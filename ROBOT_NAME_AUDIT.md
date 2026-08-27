# New client robot registry audit

Authoritative source: `data_source/Robot list v1.xlsx`, sheet `Robot  list`. Multiline cells were flattened into individual assets; `Not set yet` is stored as `null`. Zone wording is retained exactly.

| Current ID | Current cell/model | New Excel cell | New Excel robot/IP | Zone | Result | Action |
|---|---|---|---|---|---|---|
| OH26-R001 | Experience Centre · CRX-10iA/L | — | — | — | AMBIGUOUS | No unique row; remove from active registry |
| OH26-R002 | Order Fulfilment · CRX-10iA/L | Order fulfillment | CRX-10iA · unavailable | CRX ZONE | MISMATCH | Preserve ID; correct metadata |
| OH26-R003 | Nut Tightening · CRX-10iA/L | Collaborative Nut Runner | CRX-20iA/L · unavailable | CRX ZONE | MISMATCH | Preserve by unique cell purpose; correct metadata |
| OH26-R004 | CRX Force Control · CRX-20iA/L | CRX Force Control | CRX-20iA/L · 10.31.58.74 | TECH CENTER | MATCH | Preserve ID |
| OH26-R005 | Bucket Palletizing · CRX-30iA | — | — | — | NO MATCH | Remove from active registry |
| OH26-R006 | CRX Lineup · CRX-5iA | CRX Line Up on AMR | CRX-5iA · unavailable | CRX ZONE | MATCH | Preserve ID |
| OH26-R007 | Unspecified · CRX-3iA | Two CRX-3iA rows | Mixed | Multiple | AMBIGUOUS | Assign new IDs; do not guess |
| OH26-R008 | Unspecified · CRX-10iA/L | RTVT Display | CRX-10iA/L · 10.31.58.78 | CRX ZONE | MATCH | Preserve by model/IP |
| OH26-R009 | Unspecified · CRX-20iA /L | Multiple CRX-20iA/L rows | Mixed | Multiple | AMBIGUOUS | Assign new ID to lineup asset |
| OH26-R011 | Pick and Place · SR-3iA | Solar Wafer Handling | SR-6iA · 10.31.58.80 | TECH CENTER | MISMATCH | Preserve by unique IP; correct metadata |
| OH26-R012 | Secondary Packaging · SR-20iA | High Speed Secondary Packing | SR-20iA · 10.31.58.81 | TECH CENTER | MATCH | Preserve ID |
| OH26-R013 | AI Error Proofing · LR-Mate 7-9D | AI Error Proofing | LR Mate/7-9D · 10.31.58.82 | TECH CENTER | MATCH | Preserve featured ID; correct spelling |
| OH26-R014 | Intelligent Bin Picking · M-20iD 35 | Intelligent Bin Picking | M-20iD/35 · 10.31.58.83 | TECH CENTER | MATCH | Preserve ID; correct spelling |
| OH26-R015 | CRX-Paint · CRX-10iA/L | CRX Paint Robot | CRX-10iA/L · 10.31.58.84 | TECH CENTER | MATCH | Preserve ID |
| OH26-R016 | Paint Cell · P50iB/10L | Paint Robot Display' | P-50iB/10L · unavailable | TECH CENTER | MATCH | Preserve ID; correct spelling/IP |
| OH26-R017 | Deburring · LR-Mate 200iD/7L | Robotic Deburring & Fettling | LR Mate 200iD/7L · 10.31.58.86 | TECH CENTER | MATCH | Preserve ID |
| OH26-R018 | Drilling · R-2000iC 270F | Drilling and milling cell | R-2000iC/270F · 10.31.58.87 | TECH CENTER | MATCH | Preserve ID |
| OH26-R019 | RTU · R-2000iC 210F | Flexible Spot Welding System | R-2000iC/210F · 10.31.58.88 | TECH CENTER | MATCH | Preserve featured ID by model/IP |
| OH26-R020 | Fixtureless Welding · M-900iB 360 | Fixtureless Welding Cell | M-900iB/360 · 10.31.58.1 | TECH CENTER | MATCH | Preserve ID |
| OH26-R021 | Unspecified · Arc Mate 120iD 12L | Fixtureless Welding Cell | Arc Mate 120iD/12L · 10.31.58.2 | TECH CENTER | MISMATCH | Preserve by model; replace old IP |
| OH26-R022 | Unspecified · M20iD 25 | Fixtureless Welding Cell | M-20iD/25 · 10.31.58.3 | TECH CENTER | MISMATCH | Preserve by model; replace old IP |
| OH26-R023 | AMR Setup · CRX 5iA | — | — | — | AMBIGUOUS | Remove; no unique new row |
| OH26-R024 | High Speed Palletizing · M-410iC/185 | High Speed Palletizing | M-410iC/185 · 10.31.58.92 | TECH CENTER | MATCH | Preserve ID |
| OH26-R025 | AI Palletizing · M-710iD/70 | — | — | — | NO MATCH | Remove from active registry |
| OH26-R026 | Primary Packaging · M-2iA/35L | High Speed Primary Packing | M-2iA/3SL · unavailable | TECH CENTER | MISMATCH | Preserve by unique cell; correct model/IP |
| OH26-R027 | RTVT · CRX-10iA/L | RTVT Display | CRX-10iA/L · 10.31.58.78 | CRX ZONE | DUPLICATE | R008 is the IP match; remove R027 |
| OH26-R028 | Grinding · M-10iD 12 | — | — | — | NO MATCH | Remove from active registry |
| OH26-R029 | Collaborative Arc Welding · CRX-10iA/L | Collaborative Arc Welding | CRX-10iA/L · 10.31.58.105 | FUSION HUB | MATCH | Preserve ID; update IP/zone |
| OH26-R030 | Adaptive arc welding · Arc Mate 100iD | Additive Manufacturing | Arc Mate 100iD/8L · 10.31.58.102 | FUSION HUB | MATCH | Preserve by model family; correct metadata |
| OH26-R031 | Cladding · Arc Mate 120iD | Robotic Cladding System | Arc Mate 120iD · 10.31.58.101 | FUSION HUB | MATCH | Preserve ID |
| OH26-R032 | Dispensing · R-2000iC 165F | Stud Welding System | R-2000iC/165F · 10.31.58.106 | FUSION HUB | MATCH | Preserve by exact model; correct metadata |

New IDs `OH26-R033`–`OH26-R045` cover 13 assets that could not inherit an old ID without guessing: four remaining CRX Line Up robots, CRX 40Kg capability display, CRX/10-14A controller display, Robodrill LUL, CRX Concrete Drilling, the second Flexible Spot Welding robot, two LR Mate 200iD/4S cells, Portable Welding System, and Sealant Dispensing System.

## Totals

- 36 individual robot assets; 3 zones (11 / 19 / 6)
- 20 configured IPs; 16 unavailable IPs
- 23 stable old IDs preserved; 8 old IDs lacked a defensible current match
- 0 silent ambiguous mappings
