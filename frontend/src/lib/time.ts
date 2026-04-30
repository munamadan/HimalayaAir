export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return 'not reported';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function formatTimeOnly(value: string | null | undefined): string {
  if (!value) {
    return 'n/a';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function formatFreshness(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) {
    return 'freshness unknown';
  }
  if (minutes < 60) {
    return `${minutes} min old`;
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder === 0 ? `${hours} hr old` : `${hours} hr ${remainder} min old`;
}
