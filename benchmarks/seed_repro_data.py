from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

DEFAULT_DB_URL = "postgresql://himalayaair:himalayaair@localhost:55432/himalayaair"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic benchmark seed workflow for Phase 14.")
    parser.add_argument("--database-url", default=DEFAULT_DB_URL)
    parser.add_argument("--fixture", default="fixtures/replay_sample.json")
    parser.add_argument("--compose-profiles", default="core,stream")
    parser.add_argument("--wait-seconds", type=int, default=20)
    parser.add_argument("--skip-compose-up", action="store_true")
    parser.add_argument("--skip-replay", action="store_true")
    parser.add_argument("--output", default="tmp/benchmark-results/seed-summary.json")
    return parser.parse_args()



def row_count(database_url: str, table: str) -> int:
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {table}")
            return int(cur.fetchone()[0])



def main() -> int:
    args = parse_args()
    summary: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "profiles": args.compose_profiles,
        "fixture": args.fixture,
        "wait_seconds": args.wait_seconds,
        "steps": [],
    }

    profiles = [p.strip() for p in args.compose_profiles.split(",") if p.strip()]

    if not args.skip_compose_up:
        cmd = ["docker", "compose"]
        for profile in profiles:
            cmd.extend(["--profile", profile])
        cmd.extend(["up", "-d"])
        up = run(cmd, check=False)
        summary["steps"].append({"step": "compose_up", "exit_code": up.returncode, "stdout_tail": up.stdout[-800:], "stderr_tail": up.stderr[-800:]})

    health = run(["bash", "./scripts/verify_env.sh", "--profile", "core"], check=False)
    summary["steps"].append({"step": "verify_env_core", "exit_code": health.returncode, "stdout_tail": health.stdout[-800:], "stderr_tail": health.stderr[-800:]})

    if not args.skip_replay:
        replay = run([
            "python",
            "-m",
            "services.replay_publisher.main",
            "--fixture",
            args.fixture,
            "--speed",
            "500",
        ], check=False)
        summary["steps"].append({"step": "replay_publish", "exit_code": replay.returncode, "stdout_tail": replay.stdout[-800:], "stderr_tail": replay.stderr[-800:]})

    time.sleep(max(args.wait_seconds, 0))

    tables = ["aq_readings", "weather_readings", "modeled_aq_readings", "pipeline_runs", "coverage_snapshots"]
    counts: dict[str, int | str] = {}
    for table in tables:
        try:
            counts[table] = row_count(args.database_url, table)
        except Exception as exc:
            counts[table] = f"error: {exc}"
    summary["table_counts"] = counts

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "table_counts": counts}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
