# FANUC × AIonOS Synthetic Dashboard Dataset v2.0

This is the simulator contract for dashboard development before FANUC live access is available.

## Primary application format
- JSON: current snapshots, alarms, maintenance, summaries, contracts.
- JSONL: historical and replay streams.
- CSV: included only for human inspection of shift summaries.

## Data volume
- Historical telemetry: 4,320 records, 3 days at 1-minute resolution.
- Live replay: 900 records, 15 minutes at 1-second resolution.
- Optional motion sample: 600 records, 60 seconds at 100-ms resolution.
- Alarms: 4 (includes cleared and active cases).
- Maintenance: 3 (includes OVERDUE, DUE_SOON and OK cases).

## Dashboard coverage
1. Live Cell
2. Production & Cycle
3. Robot Health
4. Alarms
5. Predictive Maintenance
6. Axis & Servo
7. Energy
8. AI Insights

## Important implementation rule
Treat this as a NORMALIZED AIonOS contract. Do not couple frontend components to synthetic OPC UA NodeIds or pretend the synthetic structures are exact native ZDT responses.
When FANUC provides real data, OPC UA and ZDT adapters should map native payloads into this normalized contract.

## Recommended frontend use
- Initial page load: latest_snapshot.json
- Historical charts: telemetry_history.jsonl
- Animated demo: live_replay_1s.jsonl
- Alarm panel: alarms.json
- Maintenance panel: maintenance.json
- Shift/OEE cards: production_shift_summary.json
- AI analytics test: ai_validation_questions.json + derived_insights.json
- Optional 3D proof-of-concept: optional_motion_stream_100ms.jsonl

## QA safeguards
- Connection/stale-data scenarios are separate from robot faults.
- Active, cleared, due, overdue and normal states are all represented.
- OEE is labeled AIonOS-derived, not native FANUC.
- Position Register sample is separated from high-speed current-position simulation.
