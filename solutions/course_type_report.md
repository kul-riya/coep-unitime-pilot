# Course type report (snapshot 240) — revised

## Student body (planned)

| Cohort | Count |
|--------|------:|
| FY CSE | 400 |
| FY AIML | 100 |
| SY CSE | 400 |
| SY AIML | 100 |
| TY CSE | 400 |
| TY AIML | 100 |
| BT CSE | 400 |
| BT AIML | 100 |
| **B.Tech subtotal** | **2000** |
| MT (programs in dump) | *existing MT class sizes / TBD* |

**CSE vs AIML:** same course basket (same curriculum; cohort name differs).

## Enrollment rules (planned)

1. Every student takes all **DEFAULT** + **RESERVED** courses for their year.
2. For each elective group present that year, every student **picks exactly one** option; options split as evenly as possible.
3. Elective groups can stack (e.g. TY: one DE + one MDM + one OE).
4. **HONOR** / **MINOR** (BT): every student picks one from that group.
5. **OE** and **MDM** are college-wide: assume **~5 options across departments** (CSE dump shows 1; remaining are placeholders). Equal split across all 5.
6. **MDM** and **OE** apply to **SY, TY, and BT** (not FY).

## Hard-coded shared time slots (college-wide)

| TYPE | Days | Time | Notes |
|------|------|------|-------|
| **MDM** | Mon & Tue | **16:30–18:30** | Same slot for all MDM options / all depts; SY+TY+BT |
| **OE** | Wed & Thu | **16:30–17:30** | Same slot for all OE options / all depts; SY+TY+BT |
| **DE** | *(solver chooses one fixed pattern)* | Same meeting time for **all DE options** in a year (mutually exclusive pick) |

## Course table

| YEAR | COURSE | LAB COURSE | TYPE |
|------|--------|------------|------|
| FY | `AIMA` — AI for Multidisciplinary Applications(FY) | — | **DEFAULT** |
| FY | `DS(FY)` — Discrete Structures(FY) | `DS(FY)-Tut` — Discrete Structures Tutorial(FY) | **DEFAULT** |
| FY | `PP(FY)` — Python Programming (FY) | `PP(FY)-Lab` — Python Programming Laboratory (FY) | **DEFAULT** |
| FY | `PPS(FY)` — Programming for Problem Solving (FY) | `PPS(FY)-Lab` — Programming for Problem Solving Laboratory(FY) | **DEFAULT** |
| FY | `WD(FY)` — Web Design(FY) | `WD(FY)-Lab` — Web Design Laboratory(FY) | **DEFAULT** |
| FY | `FY-Reserved` — FY Reserved Subject | — | **RESERVED** |
| SY | `CO` — Computer Organization | — | **DEFAULT** |
| SY | `CoI` — Constitution of India | — | **DEFAULT** |
| SY | — | `DTL-Lab` — Development Tools Laboratory | **DEFAULT** |
| SY | `Eco` — Economics (SY) | — | **DEFAULT** |
| SY | `OOPD` — Object Oriented Programming and Design | `OOPD-Lab` — Object Oriented Programming and Design Lab | **DEFAULT** |
| SY | `TOC` — Theory of Computation | `TOC-Tut` — Theory of Computation Tutorial | **DEFAULT** |
| SY | `OE-FOS` — OE Fundamentals of Operating Systems | — | **OE** |
| SY | `OE-OTHER-2` — *(other-dept OE option 2; not in CSE dump)* | — | **OE** |
| SY | `OE-OTHER-3` — *(other-dept OE option 3; not in CSE dump)* | — | **OE** |
| SY | `OE-OTHER-4` — *(other-dept OE option 4; not in CSE dump)* | — | **OE** |
| SY | `OE-OTHER-5` — *(other-dept OE option 5; not in CSE dump)* | — | **OE** |
| SY | `MDM-DSFA` — MDM-Data Structures, Files and Algorithms | — | **MDM** |
| SY | `MDM-OTHER-2` — *(other-dept MDM option 2; not in CSE dump)* | — | **MDM** |
| SY | `MDM-OTHER-3` — *(other-dept MDM option 3; not in CSE dump)* | — | **MDM** |
| SY | `MDM-OTHER-4` — *(other-dept MDM option 4; not in CSE dump)* | — | **MDM** |
| SY | `MDM-OTHER-5` — *(other-dept MDM option 5; not in CSE dump)* | — | **MDM** |
| TY | `AI` — Artificial Intelligence | `AI-Lab` — Artificial Intelligence Laboratory *(forced: in catalog, no SCT/SBT in snap 240)* | **DEFAULT** |
| TY | `CN` — Computer Networks | `CN-Lab` — Computer Networks Laboratory | **DEFAULT** |
| TY | `DAA` — Design and Analysis of Algorithm | `DAA-Lab` — Design and Analysis of Algorithm Lab | **DEFAULT** |
| TY | `DE2-ASP` — DE II - Advanced System Programming | `DE2-ASP-Lab` — DE II -  Advanced System Programming Lab | **DE** |
| TY | `DE2-BCT` — DE II - BlockChain Technologies | `DE2-BCT-Lab` — DE II- BlockChain Technologies Lab | **DE** |
| TY | `DE2-DSci` — DE II - Data Science | `DE2-DSci-Lab` — DE II - Data Science Lab | **DE** |
| TY | `OE-OTHER-1` — *(other-dept OE option 1; not in CSE dump)* | — | **OE** |
| TY | `OE-OTHER-2` — *(other-dept OE option 2; not in CSE dump)* | — | **OE** |
| TY | `OE-OTHER-3` — *(other-dept OE option 3; not in CSE dump)* | — | **OE** |
| TY | `OE-OTHER-4` — *(other-dept OE option 4; not in CSE dump)* | — | **OE** |
| TY | `OE-OTHER-5` — *(other-dept OE option 5; not in CSE dump)* | — | **OE** |
| TY | `MDM-FDMS` — MDM - CS - Fundamentals of Database Management Systems | `MDM-FDMSLab` — MDM - CS - Fundamentals of Database Management Systems Lab | **MDM** |
| TY | `MDM-OTHER-2` — *(other-dept MDM option 2; not in CSE dump)* | — | **MDM** |
| TY | `MDM-OTHER-3` — *(other-dept MDM option 3; not in CSE dump)* | — | **MDM** |
| TY | `MDM-OTHER-4` — *(other-dept MDM option 4; not in CSE dump)* | — | **MDM** |
| TY | `MDM-OTHER-5` — *(other-dept MDM option 5; not in CSE dump)* | — | **MDM** |
| BT | `DE4-GIS` — DE4-GIS: Geographical Information Systems | `DE4-GIS-Lab` — DE4-GIS: Geographical Information Systems Lab | **DE** |
| BT | `DE4-GPU` — DE4: GPU Computing | `DE4-GPU-Lab` — DE4: GPU Computing Lab | **DE** |
| BT | `DE4-IBCS` — Introduction of Blockchains Cryptocurrencies and Smart Contracts | `DE4-IBC-Lab` — DE4: Introduction of Blockchains CSC Lab | **DE** |
| BT | `OE-OTHER-1` — *(other-dept OE option 1; not in CSE dump)* | — | **OE** |
| BT | `OE-OTHER-2` — *(other-dept OE option 2; not in CSE dump)* | — | **OE** |
| BT | `OE-OTHER-3` — *(other-dept OE option 3; not in CSE dump)* | — | **OE** |
| BT | `OE-OTHER-4` — *(other-dept OE option 4; not in CSE dump)* | — | **OE** |
| BT | `OE-OTHER-5` — *(other-dept OE option 5; not in CSE dump)* | — | **OE** |
| BT | `MDM-OTHER-1` — *(other-dept MDM option 1; not in CSE dump)* | — | **MDM** |
| BT | `MDM-OTHER-2` — *(other-dept MDM option 2; not in CSE dump)* | — | **MDM** |
| BT | `MDM-OTHER-3` — *(other-dept MDM option 3; not in CSE dump)* | — | **MDM** |
| BT | `MDM-OTHER-4` — *(other-dept MDM option 4; not in CSE dump)* | — | **MDM** |
| BT | `MDM-OTHER-5` — *(other-dept MDM option 5; not in CSE dump)* | — | **MDM** |
| BT | `Honor4-IOT` — Honor4-IOT Security | — | **HONOR** |
| BT | `Honor4-RL` — Honor4-Reinforcement Learning | — | **HONOR** |
| BT | `Minor4-DS` — Minor4-Data Science | — | **MINOR** |
| MT | `DMML` — Data Mining and Machine Learning | `DMML-Lab` — Data Mining and Machine Learning - Laboratory | **DEFAULT** |
| MT | `ES` — Embedded Systems | `ES-Lab` — Embedded Systems - Laboratory | **DEFAULT** |
| MT | `SIC` — Security in Computing | `SIC-Lab` — Security in Computing - Laboratory | **DEFAULT** |
| MT | `OE-DS` — OE:Data Structures | — | **OE** |
| MT | `MT-NLP` — PSEC3- Natural Language Processing | — | **PSEC** |
| MT | `PSEC2-BT` — PSEC2- Blockchain Technology | — | **PSEC** |
| MT | `PSEC2-CCS` — PSEC2- Cloud Computing and Security | — | **PSEC** |
| MT | `PSEC2-CCV` — PSEC2-Cloud Computing and Virtualization | — | **PSEC** |
| MT | `PSEC2-CV` — PSEC2- Computer Vision | — | **PSEC** |
| MT | `PSEC2-EAI` — PSEC2- Explainable Artificial Intelligence | — | **PSEC** |
| MT | `PSEC2-MLPS` — PSEC2- ML-OPS | — | **PSEC** |
| MT | `PSEC2-MTRP` — PSEC2- R Programming | — | **PSEC** |
| MT | `PSEC2-NLP` — PSEC2-Natural Language Processing | — | **PSEC** |
| MT | `PSEC3-DL` — PSEC3-Deep Learning | — | **PSEC** |
| MT | `PSEC3-GAN` — PSEC3- Generative Adversarial Network | — | **PSEC** |
| MT | `PSEC3-GNN` — PSEC3- Graph Neural Network | — | **PSEC** |
| MT | `PSEC3-ITS` — PSEC3- Internet of Things and Security | — | **PSEC** |
| MT | `PSEC3-MT` — PSEC3-Multicore Technology | — | **PSEC** |
| MT | `PSEC3-WS` — PSEC3- Web Security | — | **PSEC** |
| MT | `MT-AMLD` — Advanced Machine Learning and Deep | `MT-AMLD-Lab` — Advanced Machine Learning and Deep Lab | **MT-DEFAULT** |
| MT | `MT-BDAAS` — Big Data Analytics with Apache Spark | `MT-BDAAS-Lab` — Big Data Analytics with Apache Spark Lab | **MT-DEFAULT** |
| MT | `MT-DFDR` — MTech Digital Forensics and Data Recovery | `MT-DFDR-Lab` — MTech Digital Forensics and Data Recovery  - Laboratory | **MT-DEFAULT** |
| MT | `MT-DL` — Deep Learning | `MTDL-Lab` — Deep Learning Lab | **MT-DEFAULT** |
| MT | `MT-ETCSA` — MTech Effective Technical Communication Skills | `MT-ETCSALab` — MTech Effective Technical Communication Skills Lab | **MT-DEFAULT** |
| MT | `MT-GAN` — Generative Adversarial Network | `MT-GAN-Lab` — Generative Adversarial Network Lab | **MT-DEFAULT** |
| MT | `MT-MLOS` — ML Ops and Systems | `MT-MLOS-Lab` — ML Ops and Systems Lab | **MT-DEFAULT** |
| MT | `MT-NS` — MTech Network Security | `MT-NS-Lab` — MTech Network Security - Laboratory | **MT-DEFAULT** |
| MT | `MT-OT` — Optimization Techniques | `MT-OT-Lab` — Optimization Techniques Lab | **MT-DEFAULT** |
| MT | `MT-WNS` — MTech Wireless Networks | `MT-WNS-Lab` — MTech Wireless Networks and Security - Laboratory | **MT-DEFAULT** |

## Counts by year × type

| YEAR | TYPE | N |
|------|------|---|
| FY | DEFAULT | 5 |
| FY | RESERVED | 1 |
| SY | DEFAULT | 6 |
| SY | OE | 5 |
| SY | MDM | 5 |
| TY | DEFAULT | 3 |
| TY | DE | 3 |
| TY | OE | 5 |
| TY | MDM | 5 |
| BT | DE | 3 |
| BT | OE | 5 |
| BT | MDM | 5 |
| BT | HONOR | 2 |
| BT | MINOR | 1 |
| MT | DEFAULT | 3 |
| MT | OE | 1 |
| MT | PSEC | 15 |
| MT | MT-DEFAULT | 10 |

## Equal-split preview (500 students / B.Tech year)

| YEAR | Group | # options | Students / option (approx) |
|------|-------|----------:|---------------------------:|
| SY | OE | 5 | 100 (rem 0) |
| SY | MDM | 5 | 100 (rem 0) |
| TY | DE | 3 | 166 (rem 2) |
| TY | OE | 5 | 100 (rem 0) |
| TY | MDM | 5 | 100 (rem 0) |
| BT | DE | 3 | 166 (rem 2) |
| BT | OE | 5 | 100 (rem 0) |
| BT | MDM | 5 | 100 (rem 0) |
| BT | HONOR | 2 | 250 (rem 0) |
| BT | MINOR | 1 | 500 (rem 0) |

## Notes

- `AI-Lab` is attached to `AI` per your instruction. In snapshot 240 it exists in `subject` but has **no** `subjectClassTeacher` / `subjectBatchTeacher` / `timeTable` row — flagged in the LAB column.
- `DTL-Lab`: COURSE blank; name only under LAB COURSE.
- `OE-OTHER-*` / `MDM-OTHER-*` are placeholders for other-department electives (avg 5 college-wide).
- M.Tech rows included; PSEC treated as MT elective picks (one per PSEC level if you confirm later).

**Waiting for your OK before rewriting `studentenrollments.xml` / preferences.**
