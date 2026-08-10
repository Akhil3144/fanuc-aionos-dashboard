FANUC × AIonOS Synthetic Data V3

Multi-robot simulator dataset.

Robots
------
EXH-R01 - Assembly Robot - stable production
EXH-R02 - Handling Robot - Axis 4 anomaly + overdue predictive maintenance
EXH-R03 - Packaging Robot - cycle-performance + energy-efficiency profile

Design
------
- Current fleet state has no FAULTED robot.
- Historical fault events remain available for analytics.
- Connectivity is not an AI Insight.
- Predictive maintenance is represented inside AI Insights.
- telemetry_history.jsonl has 4,320 records per robot / 12,960 total.
- live_replay_1s.jsonl has 900 fleet snapshots.
- latest_snapshot.json remains an EXH-R01 compatibility alias.
- fleet_latest_snapshot.json is the new fleet-level source.
