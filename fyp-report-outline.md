# HimalayaAir - FYP Report Outline

Reference pattern: `docs_reference/ProctiNetra Project Report.docx` (senior report).
Source of truth for content: `docs/himalayaair-system-overview.md`.
This file is a planning outline only; it holds no report prose. Cover page is handled separately and is out of scope here.

## Style conventions (match the senior report)

- Heading 1 = front-matter sections and `CHAPTER N: TITLE`.
- Heading 2 = `x.1` numbered section.
- Heading 3 = `x.x.x` subsection.
- Heading 4 = `x.x.x.x` sub-subsection.
- Body text = `Normal`.
- Figure captions = manual `Figure N: <title>` lines (Word Caption style), placed directly under each inline figure.
- Table captions = manual `Table N. <title>`.
- `LIST OF FIGURES`, `LIST OF TABLES`, and `TABLE OF CONTENTS` are typed manually in the senior report. For HimalayaAir they may be regenerated from Heading and Caption styles before final export.
- Conceptual, architecture, DFD, ERD, and Gantt figures live inline in Chapters 2-5.
- All live-product UI screenshots are collected in `APPENDIX I - SCREENSHOTS`, not scattered through the body.

## Front matter order

1. ACKNOWLEDGMENT
2. ABSTRACT - provenance-aware data-fusion thesis framing per `docs/himalayaair-system-overview.md` Section 1; ends with a `Keywords:` line (AQI, provenance, Kafka, Spark Structured Streaming, TimescaleDB, PostGIS, IDW, SARIMAX, Airflow, OpenAQ).
3. LIST OF ABBREVIATIONS - two-column alpha-sorted table: AQI, PM2.5, PM10, IDW, DFD, ERD, DAG, API, WebSocket, SARIMAX, CAMS, FIRMS, UTC, JSON, UCI.
4. LIST OF FIGURES
5. LIST OF TABLES
6. TABLE OF CONTENTS

## CHAPTER 1: INTRODUCTION

- 1.1 Introduction
- 1.2 Problem Statement
- 1.3 Objectives
- 1.4 Scope and Limitations
  - 1.4.1 Scope
  - 1.4.2 Limitation
- 1.5 Development Methodology
- 1.6 Report Organization

No figures in this chapter.

## CHAPTER 2: BACKGROUND STUDY AND LITERATURE REVIEW

2.1 Background Study (one subsection per core technology; each carries one block diagram):

- 2.1.1 Kafka Message Bus - Figure 1: Kafka topic and producer/consumer block diagram
- 2.1.2 Spark Structured Streaming - Figure 2: Spark streaming pipeline block diagram
- 2.1.3 TimescaleDB Hypertables and PostGIS - Figure 3: Hypertable and continuous aggregate model
- 2.1.4 Airflow Orchestration - Figure 4: DAG dependency block diagram
- 2.1.5 FastAPI and WebSocket Live Feed - Figure 5: API and WebSocket block diagram
- 2.1.6 Spatial Interpolation (IDW) and AQI Calculation

2.2 Literature Review (grouped thematically):

- 2.2.1 Air-Quality Data Platforms
- 2.2.2 Real-Time Streaming Pipelines
- 2.2.3 Forecasting Approaches
  - 2.2.3.1 SARIMAX with Weather Covariates
  - 2.2.3.2 Persistence and Bias-Adjusted Modeled Fallback

Figures used: 1, 2, 3, 4, 5.

## CHAPTER 3: SYSTEM ANALYSIS

3.1 System Analysis

- 3.1.1.1 Functional Requirements - Table 1: Functional Requirements
- 3.1.1.2 Non-Functional Requirements
- 3.1.2 Feasibility Analysis
  - Technical Feasibility
  - Economic Feasibility
  - Operational Feasibility
  - Schedule Feasibility - Figure 7: Project Timeline (Gantt)
- 3.1.3 System Analysis
  - 3.1.3.1 Process Modeling
    - Figure 6: Use case diagram
    - Figure 8: Context Diagram
    - Figure 9: Level 0 DFD
    - Figure 10: Level 1 DFD for Ingestion and Stream Processing
    - Figure 11: Level 1 DFD for Forecast and API
  - 3.1.3.2 Database Modeling
    - Figure 12: Database Design (ERD of station, sensor, reading, forecast, fire event tables)

Tables used: 1. Figures used: 6, 7, 8, 9, 10, 11, 12.

## CHAPTER 4: SYSTEM DESIGN

4.1 Design

- 4.1.1 System Flowchart - Figure 13: End-to-end system flowchart (source adapter through Kafka, Spark, TimescaleDB, FastAPI, frontend)
- 4.1.2 Interface Design (wireframe mockups, not live screenshots)
  - Figure 14: Map-first Dashboard Wireframe
  - Figure 15: Forecast Panel Wireframe
  - Figure 16: Pipeline Health Dashboard Wireframe

4.2 Algorithm Details

- 4.2.1 AQI Calculation Algorithm
- 4.2.2 IDW Spatial Interpolation Algorithm
- 4.2.3 Provenance and Source-Mode Resolution Algorithm
- 4.2.4 Forecast Arbitration Algorithm (SARIMAX to bias-adjusted modeled to persistence fallback)

Figures used: 13, 14, 15, 16.

## CHAPTER 5: IMPLEMENTATION AND TESTING

5.1.2 Implementation Details of Modules

- 5.1.2.1 OpenAQ Ingestion (sensor-based adapter)
- 5.1.2.2 Open-Meteo Weather and Modeled AQ Pollers
- 5.1.2.3 Kafka and Spark Stream Processing
- 5.1.2.4 Airflow DAGs (historical backfill, weather backfill, modeled AQ refresh, forecast recompute, data quality check, FIRMS daily)
- 5.1.2.5 FastAPI and WebSocket API
- 5.1.2.6 Forecasting Service (model arbitration)
- 5.1.2.7 React Frontend (map-first view, provenance panel, demo mode)

5.2 Testing

- 5.2.1 Test Cases for Unit Testing - Table 2: Unit Testing Test Cases
- 5.2.2 Test Cases for Integration Testing - Table 3: Integration Testing Test Cases

5.3 Result Analysis

- 5.3.1 Findings
- 5.3.2 Forecast Accuracy vs Observed - Figure 17: Forecast Evaluation Curve
- 5.3.3 Provenance Mode Distribution - Figure 18: Provenance Mode Distribution
- Result validation summary - Table 4: Forecast Validation Results

Tables used: 2, 3, 4. Figures used: 17, 18.

## CHAPTER 6: CONCLUSION AND FUTURE ENHANCEMENTS

- 6.1 Conclusion
- 6.2 Future Enhancements

No figures.

## REFERENCES

IEEE-style entries. No figures or tables.

## APPENDIX I - SCREENSHOTS

Live-product UI gallery, one tile per screenshot, placed after References. Captures reuse `docs/screenshots/`:

1. Dashboard / Map-first Overview - `docs/screenshots/dashboard-overview.png`
2. Provenance Panel - `docs/screenshots/provenance-panel.png`
3. Replay/Demo Mode - `docs/screenshots/replay-demo-mode.png`
4. Forecast Panel - `docs/screenshots/forecast-panel.png`
5. Pipeline Health - `docs/screenshots/pipeline-health.png`
6. (Optional) Mobile Layout Capture - 390x844, one tile

Capture rules per `docs/screenshots/README.md`:
- Resolution 1920x1080 (desktop) and one 390x844 mobile capture.
- Browser Chromium/Chrome at 100% zoom.
- Timestamp and current provenance/coverage mode visible in each shot.
- No secrets or local tokens in devtools.

## Figure and table index summary

Figures (inline, numbered 1 through 18):

1. Kafka topic and producer/consumer block diagram (Ch2.1.1)
2. Spark streaming pipeline block diagram (Ch2.1.2)
3. Hypertable and continuous aggregate model (Ch2.1.3)
4. DAG dependency block diagram (Ch2.1.4)
5. API and WebSocket block diagram (Ch2.1.5)
6. Use case diagram (Ch3.1.3.1)
7. Project Timeline / Gantt (Ch3.1.2 Schedule)
8. Context Diagram (Ch3.1.3.1)
9. Level 0 DFD (Ch3.1.3.1)
10. Level 1 DFD for Ingestion and Stream Processing (Ch3.1.3.1)
11. Level 1 DFD for Forecast and API (Ch3.1.3.1)
12. Database Design / ERD (Ch3.1.3.2)
13. End-to-end System Flowchart (Ch4.1.1)
14. Map-first Dashboard Wireframe (Ch4.1.2)
15. Forecast Panel Wireframe (Ch4.1.2)
16. Pipeline Health Dashboard Wireframe (Ch4.1.2)
17. Forecast Evaluation Curve (Ch5.3.2)
18. Provenance Mode Distribution (Ch5.3.3)

Appendix I screenshots (uncaptioned gallery tiles):

1. Dashboard / Map-first Overview
2. Provenance Panel
3. Replay/Demo Mode
4. Forecast Panel
5. Pipeline Health
6. Mobile Layout (optional)

Tables (numbered 1 through 4):

1. Functional Requirements (Ch3)
2. Unit Testing Test Cases (Ch5.2.1)
3. Integration Testing Test Cases (Ch5.2.2)
4. Forecast Validation Results (Ch5.3)

## Open items before draft writing

- Confirm final figure numbering once figures are actually produced; the indices above assume the listed insertion order.
- Decide whether wireframe mockups (Figs 14-16) will be hand-drawn, Figma, or Excalidraw; they are intentionally separate from the live screenshots in Appendix I.
- Capture the 5 PNG screenshots already declared in `docs/screenshots/README.md` plus the optional mobile capture before final export.
- Generate `LIST OF FIGURES`, `LIST OF TABLES`, and `TABLE OF CONTENTS` from Heading and Caption styles at the end, replacing any manually typed drafts.