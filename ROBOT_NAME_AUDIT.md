# Open House 2026 robot-name audit

Authoritative comparison: `data_source/Openhouse 2026 Robotlist.xlsx`, **Main Floor**, rows 3–33. Blank, `NA`, and `UNASSIGNED` IP cells are represented as unavailable. Trailing spaces are normalized for display.

| Robot ID | Current display name | Excel name | Result | Action |
|---|---|---|---|---|
| OH26-R001 | CRX-10iA/L | CRX-10iA/L | MATCH | None |
| OH26-R002 | CRX-10iA/L | CRX-10iA/L | MATCH | None |
| OH26-R003 | CRX-10iA/L | CRX-10iA/L | MATCH | None |
| OH26-R004 | CRX-20iA/L | CRX-20iA/L | MATCH | None |
| OH26-R005 | CRX-30iA | CRX-30iA | MATCH | None |
| OH26-R006 | CRX-5iA | CRX-5iA | MATCH | None |
| OH26-R007 | CRX-3iA | CRX-3iA | MATCH | None |
| OH26-R008 | CRX-10iA/L | CRX-10iA/L | MATCH | None |
| OH26-R009 | CRX-20iA /L | CRX-20iA /L | MATCH | None |
| OH26-R011 | SR-3iA | SR-3iA | MATCH | None |
| OH26-R012 | SR-20iA | SR-20iA | MATCH | None |
| OH26-R013 | LR-Mate 7-9D | LR-Mate 7-9D | MATCH | None |
| OH26-R014 | M-20iD 35 | M-20iD 35 | MATCH | None |
| OH26-R015 | CRX-10iA/L | CRX-10iA/L | MATCH | None |
| OH26-R016 | P50iB/10L | P50iB/10L | MATCH | None |
| OH26-R017 | LR-Mate 200iD/7L | LR-Mate 200iD/7L | MATCH | None |
| OH26-R018 | R-2000iC 270F | R-2000iC 270F | MATCH | None |
| OH26-R019 | R-2000iC 210F | R-2000iC 210F | MATCH | None |
| OH26-R020 | M-900iB 360 | M-900iB 360 | MATCH | None |
| OH26-R021 | Arc Mate 120iD 12L | Arc Mate 120iD 12L | MATCH | Trimmed trailing space |
| OH26-R022 | M20iD 25 | M20iD 25 | MATCH | None |
| OH26-R023 | CRX 5iA | CRX 5iA | MATCH | None |
| OH26-R024 | M-410iC/185 | M-410iC/185 | MATCH | None |
| OH26-R025 | M-710iD/70 | M-710iD/70 | MATCH | None |
| OH26-R026 | M-2iA/35L | M-2iA/35L | MATCH | None |
| OH26-R027 | CRX-10iA/L | CRX-10iA/L | MATCH | None |
| OH26-R028 | M-10iD 12 | M-10iD 12 | MATCH | None |
| OH26-R029 | CRX-10iA/L | CRX-10iA/L | MATCH | Trimmed application space |
| OH26-R030 | Arc Mate 100iD | Arc Mate 100iD | MATCH | Trimmed trailing space |
| OH26-R031 | Arc Mate 120iD | Arc Mate 120iD | MATCH | None |
| OH26-R032 | R-2000iC 165F | R-2000iC 165F | MATCH | `UNASSIGNED` IP treated as unavailable |

## Ambiguities

The secondary **Fusion Hub** sheet uses a different local serial sequence and conflicting model/application pairings for rows numbered 27–30. Because the main registry sheet is complete, includes IP addresses, and matches the existing 31-entry OH26 mapping, no secondary-sheet values were substituted.
