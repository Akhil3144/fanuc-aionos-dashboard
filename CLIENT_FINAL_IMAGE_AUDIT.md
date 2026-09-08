# Final client image audit

36 robots: 34 EXACT CLIENT IMAGE, 2 SAME-FAMILY FALLBACK, 0 MISSING, 0 WRONG-FAMILY. Existing exact mappings were checked against the original client ZIP filenames; new images were visually inspected.

New ZIP: data_source/Images for Fanuc.zip (copied from the user's Downloads); all three files extracted with safe filenames.

- R013: lr-mate-7d-client.png. Visible label is LR Mate 200iD/7L. FANUC explicitly maps this to LR Mate/7-9D. Also replaces the older exact image for R017.
- R038: crx-family.svg. New photo is explicitly labeled CRX-10iA; no verified equivalence to CRX/10-14A. New photo used only for R002 (CRX-10iA).
- R041: r-2000-family.svg. Supplied 300F-27R filename points to a 300F model (FANUC lists 300F-27E); neither establishes an exact 210F-31E match. Extracted image intentionally unused.

References: [FANUC model-name correspondence](https://fanuc-corporation.github.io/fanuc_driver_doc/v1.3.0/docs/environment/supported_models.html), [FANUC 300F-27E](https://www.fanucamerica.com/products/robot/r-2000-300f-27e).

| Robot | Registry model | Classification | Image |
|---|---|---|---|
| OH26-R033 | CRX-3iA | EXACT CLIENT IMAGE | /robot-images/client/CRX-3iA-Beauty-Shot.avif |
| OH26-R006 | CRX-5iA | EXACT CLIENT IMAGE | /robot-images/client/CRX-5iA-cobot.png |
| OH26-R034 | CRX-10iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-10ial-cobot.avif |
| OH26-R035 | CRX-20iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-20ia-l.png |
| OH26-R036 | CRX-30iA | EXACT CLIENT IMAGE | /robot-images/client/crx-30ia.avif |
| OH26-R008 | CRX-10iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-10ial-cobot.avif |
| OH26-R037 | CRX-30iA | EXACT CLIENT IMAGE | /robot-images/client/crx-30ia.avif |
| OH26-R003 | CRX-20iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-20ia-l.png |
| OH26-R002 | CRX-10iA | EXACT CLIENT IMAGE | /robot-images/client/crx-10ia-client.jpg |
| OH26-R038 | CRX/10-14A | SAME-FAMILY FALLBACK | /robot-images/crx-family.svg |
| OH26-R039 | CRX-10iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-10ial-cobot.avif |
| OH26-R013 | LR Mate/7-9D | EXACT CLIENT IMAGE | /robot-images/client/lr-mate-7d-client.png |
| OH26-R040 | CRX-30iA | EXACT CLIENT IMAGE | /robot-images/client/crx-30ia.avif |
| OH26-R004 | CRX-20iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-20ia-l.png |
| OH26-R015 | CRX-10iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-10ial-cobot.avif |
| OH26-R018 | R-2000iC/270F | EXACT CLIENT IMAGE | /robot-images/client/R2000iC_270F.avif |
| OH26-R024 | M-410iC/185 | EXACT CLIENT IMAGE | /robot-images/client/m-410ic-185.png |
| OH26-R026 | M-2iA/3SL | EXACT CLIENT IMAGE | /robot-images/client/m-2ia-3sl.avif |
| OH26-R012 | SR-20iA | EXACT CLIENT IMAGE | /robot-images/client/sr-20ia.png |
| OH26-R014 | M-20iD/35 | EXACT CLIENT IMAGE | /robot-images/client/m-20id-35.png |
| OH26-R016 | P-50iB/10L | EXACT CLIENT IMAGE | /robot-images/client/p-50ib-10l.png |
| OH26-R017 | LR Mate 200iD/7L | EXACT CLIENT IMAGE | /robot-images/client/lr-mate-7d-client.png |
| OH26-R011 | SR-6iA | EXACT CLIENT IMAGE | /robot-images/client/SR-6iA-Beauty-Shot.png |
| OH26-R019 | R-2000iC/210F | EXACT CLIENT IMAGE | /robot-images/client/r-2000ic-210f.jpg |
| OH26-R041 | R-2000/210F-31E | SAME-FAMILY FALLBACK | /robot-images/r-2000-family.svg |
| OH26-R020 | M-900iB/360 | EXACT CLIENT IMAGE | /robot-images/client/m-900ib-360.png |
| OH26-R021 | Arc Mate 120iD/12L | EXACT CLIENT IMAGE | /robot-images/client/arc-mate-120id-12l.png |
| OH26-R022 | M-20iD/25 | EXACT CLIENT IMAGE | /robot-images/client/m-20id-25.png |
| OH26-R042 | LR Mate 200iD/4S | EXACT CLIENT IMAGE | /robot-images/client/lr-mate-200id-4s.png |
| OH26-R043 | LR Mate 200iD/4S | EXACT CLIENT IMAGE | /robot-images/client/lr-mate-200id-4s.png |
| OH26-R031 | Arc Mate 120iD | EXACT CLIENT IMAGE | /robot-images/client/arc-mate-120id.png |
| OH26-R030 | Arc Mate 100iD/8L | EXACT CLIENT IMAGE | /robot-images/client/arc-mate-100id-8l.png |
| OH26-R044 | CRX-3iA | EXACT CLIENT IMAGE | /robot-images/client/CRX-3iA-Beauty-Shot.avif |
| OH26-R045 | R-2000iC/210F | EXACT CLIENT IMAGE | /robot-images/client/r-2000ic-210f.jpg |
| OH26-R029 | CRX-10iA/L | EXACT CLIENT IMAGE | /robot-images/client/crx-10ial-cobot.avif |
| OH26-R032 | R-2000iC/165F | EXACT CLIENT IMAGE | /robot-images/client/r-2000ic-165f.avif |

Featured IDs: OH26-R013 and OH26-R019 only. R041 remains in the fleet with its registers and full existing simulator history. Home and Fleet counts, filtering, badges, and detail selection derive from registry flags; no hard-coded featured count of 3 found. R013/R019 detail links and enhanced pages remain intact.

Validation: production build, targeted ESLint, Python compilation, diff whitespace check, all three scripts/test suites, synthetic-data validation, 7 register-grounding cases, 112/112 handover cases, and 11/11 client chatbot cases passed. The older client test expected removed R028 in maintenance rankings; the original HEAD implementation and registry produced the same R002/R022/R019 answer, so only the stale test expectation was corrected. Chatbot routing and analytics are unchanged; the featured answer handler now includes the derived count and resolves explicitly named robots in fleet-scope featured questions. Browser visual interaction was not performed.
