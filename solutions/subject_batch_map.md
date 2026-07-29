# Subject → batch mapping (snapshot 240)

Source tables in `taasika2-foss-26jan26.sql/taasika2-foss-26jan26.sql`:

- `subject` (CREATE ~line 494)
- `subjectClassTeacher` → lecture subject ↔ class
- `subjectBatchTeacher` → lab/tut/elective subject ↔ batch
- `batchClass` → batch ↔ parent class (year)

Rules used:

1. If a subject has `subjectBatchTeacher` rows → those batches.
2. Else if it only has `subjectClassTeacher` → all batches under those classes via `batchClass`.
3. Year from parent class short name / semester; else from batch name prefix (FY/SY/TY/BT).

## FY (First Year B.Tech)

### `AIMA` — AI for Multidisciplinary Applications(FY)

- subjectId: `32749`
- classes: FY-AIMA1 (FY ES AI For Interdisci. Appl Div1), FY-AIMA2 (FY ES AI For Interdisci. Appl Div2), FY-AIMA3 (FY ES AI for Interrdisci. Appl Div3)
- batches (via class→batchClass (no direct SBT)): *(no batches)*

### `DS(FY)` — Discrete Structures(FY)

- subjectId: `32747`
- classes: FY-CSE1 (FY CSE Div1), FY-CSE2 (FY CSE Div2), FY-CSE3 (FY CSE Div3), FY-CSE4 (FY CSE Div4), FY-AIML (FY AIML Div1)
- batches (via class→batchClass (no direct SBT)): FY-CSE1-A, FY-CSE1-B, FY-CSE1-C, FY-CSE1-D, FY-CSE2-A, FY-CSE2-B, FY-CSE2-C, FY-CSE2-D, FY-CSE3-A, FY-CSE3-B, FY-CSE3-C, FY-CSE3-D, FY-AIML-A, FY-AIML-B, FY-AIML-C, FY-AIML-D, FY-CSE4-A, FY-CSE4-B, FY-CSE4-C, FY-CSE4-D
- batch detail:
  - `FY-CSE1-A` (id 30724, year=FY, parent class: FY-CSE1)
  - `FY-CSE1-B` (id 30725, year=FY, parent class: FY-CSE1)
  - `FY-CSE1-C` (id 30726, year=FY, parent class: FY-CSE1)
  - `FY-CSE1-D` (id 30727, year=FY, parent class: FY-CSE1)
  - `FY-CSE2-A` (id 30728, year=FY, parent class: FY-CSE2)
  - `FY-CSE2-B` (id 30729, year=FY, parent class: FY-CSE2)
  - `FY-CSE2-C` (id 30730, year=FY, parent class: FY-CSE2)
  - `FY-CSE2-D` (id 30731, year=FY, parent class: FY-CSE2)
  - `FY-CSE3-A` (id 30732, year=FY, parent class: FY-CSE3)
  - `FY-CSE3-B` (id 30733, year=FY, parent class: FY-CSE3)
  - `FY-CSE3-C` (id 30734, year=FY, parent class: FY-CSE3)
  - `FY-CSE3-D` (id 30735, year=FY, parent class: FY-CSE3)
  - `FY-AIML-A` (id 30780, year=FY, parent class: FY-AIML)
  - `FY-AIML-B` (id 30781, year=FY, parent class: FY-AIML)
  - `FY-AIML-C` (id 30782, year=FY, parent class: FY-AIML)
  - `FY-AIML-D` (id 30783, year=FY, parent class: FY-AIML)
  - `FY-CSE4-A` (id 30784, year=FY, parent class: FY-CSE4)
  - `FY-CSE4-B` (id 30785, year=FY, parent class: FY-CSE4)
  - `FY-CSE4-C` (id 30786, year=FY, parent class: FY-CSE4)
  - `FY-CSE4-D` (id 30787, year=FY, parent class: FY-CSE4)

### `DS(FY)-Tut` — Discrete Structures Tutorial(FY)

- subjectId: `32748`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): FY-CSE1-A, FY-CSE1-B, FY-CSE1-C, FY-CSE1-D, FY-CSE2-A, FY-CSE2-B, FY-CSE2-C, FY-CSE2-D, FY-CSE3-A, FY-CSE3-B, FY-CSE3-C, FY-CSE3-D, FY-AIML-A, FY-AIML-B, FY-AIML-C, FY-AIML-D, FY-CSE4-A, FY-CSE4-B, FY-CSE4-C, FY-CSE4-D
- batch detail:
  - `FY-CSE1-A` (id 30724, year=FY, parent class: FY-CSE1)
  - `FY-CSE1-B` (id 30725, year=FY, parent class: FY-CSE1)
  - `FY-CSE1-C` (id 30726, year=FY, parent class: FY-CSE1)
  - `FY-CSE1-D` (id 30727, year=FY, parent class: FY-CSE1)
  - `FY-CSE2-A` (id 30728, year=FY, parent class: FY-CSE2)
  - `FY-CSE2-B` (id 30729, year=FY, parent class: FY-CSE2)
  - `FY-CSE2-C` (id 30730, year=FY, parent class: FY-CSE2)
  - `FY-CSE2-D` (id 30731, year=FY, parent class: FY-CSE2)
  - `FY-CSE3-A` (id 30732, year=FY, parent class: FY-CSE3)
  - `FY-CSE3-B` (id 30733, year=FY, parent class: FY-CSE3)
  - `FY-CSE3-C` (id 30734, year=FY, parent class: FY-CSE3)
  - `FY-CSE3-D` (id 30735, year=FY, parent class: FY-CSE3)
  - `FY-AIML-A` (id 30780, year=FY, parent class: FY-AIML)
  - `FY-AIML-B` (id 30781, year=FY, parent class: FY-AIML)
  - `FY-AIML-C` (id 30782, year=FY, parent class: FY-AIML)
  - `FY-AIML-D` (id 30783, year=FY, parent class: FY-AIML)
  - `FY-CSE4-A` (id 30784, year=FY, parent class: FY-CSE4)
  - `FY-CSE4-B` (id 30785, year=FY, parent class: FY-CSE4)
  - `FY-CSE4-C` (id 30786, year=FY, parent class: FY-CSE4)
  - `FY-CSE4-D` (id 30787, year=FY, parent class: FY-CSE4)

### `FY-Reserved` — FY Reserved Subject

- subjectId: `32745`
- classes: FY-Reserved1 (FY Reserved classes1), FY-Reserved2 (FY Reserved classes2), FY-Reserved3 (FY Reserved classes3)
- batches (via class→batchClass (no direct SBT)): *(no batches)*

### `PP(FY)` — Python Programming (FY)

- subjectId: `32750`
- classes: FY-PP1 (FY VSEC Python Programming Div1), FY-PP2 (FY VSEC Python Programming Div2), FY-PP3 (FY VSEC Python Programming Div3), FY-PP4n5 (FY VSEC Python Programming Div4,5 Combined)
- batches (via class→batchClass (no direct SBT)): FY-PP1-A, FY-PP1-B, FY-PP1-C, FY-PP1-D, FY-PP2-A, FY-PP2-B, FY-PP2-C, FY-PP2-D, FY-PP3-A, FY-PP3-B, FY-PP3-C, FY-PP3-D, FY-PP3-A_
- batch detail:
  - `FY-PP1-A` (id 30736, year=FY, parent class: FY-PP1)
  - `FY-PP1-B` (id 30737, year=FY, parent class: FY-PP1)
  - `FY-PP1-C` (id 30738, year=FY, parent class: FY-PP1)
  - `FY-PP1-D` (id 30739, year=FY, parent class: FY-PP1)
  - `FY-PP2-A` (id 30740, year=FY, parent class: FY-PP2)
  - `FY-PP2-B` (id 30741, year=FY, parent class: FY-PP2)
  - `FY-PP2-C` (id 30742, year=FY, parent class: FY-PP2)
  - `FY-PP2-D` (id 30743, year=FY, parent class: FY-PP2)
  - `FY-PP3-A` (id 30744, year=FY, parent class: FY-PP3)
  - `FY-PP3-B` (id 30745, year=FY, parent class: FY-PP3)
  - `FY-PP3-C` (id 30746, year=FY, parent class: FY-PP3)
  - `FY-PP3-D` (id 30747, year=FY, parent class: FY-PP3)
  - `FY-PP3-A_` (id 30793, year=FY, parent class: FY-PP3)

### `PP(FY)-Lab` — Python Programming Laboratory (FY)

- subjectId: `32751`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): FY-PP1-A, FY-PP1-B, FY-PP1-C, FY-PP1-D, FY-PP2-A, FY-PP2-B, FY-PP2-C, FY-PP2-D, FY-PP3-A, FY-PP3-B, FY-PP3-C, FY-PP3-D, FY-PP4-A, FY-PP4-B, FY-PP4-C, FY-PP5-A, FY-PP5-B, FY-PP5-C, FY-PP5-D, FY-PP5-E, FY-PP5-F, FY-PP5-A_, FY-PP4-A_, FY-PP3-A_
- batch detail:
  - `FY-PP1-A` (id 30736, year=FY, parent class: FY-PP1)
  - `FY-PP1-B` (id 30737, year=FY, parent class: FY-PP1)
  - `FY-PP1-C` (id 30738, year=FY, parent class: FY-PP1)
  - `FY-PP1-D` (id 30739, year=FY, parent class: FY-PP1)
  - `FY-PP2-A` (id 30740, year=FY, parent class: FY-PP2)
  - `FY-PP2-B` (id 30741, year=FY, parent class: FY-PP2)
  - `FY-PP2-C` (id 30742, year=FY, parent class: FY-PP2)
  - `FY-PP2-D` (id 30743, year=FY, parent class: FY-PP2)
  - `FY-PP3-A` (id 30744, year=FY, parent class: FY-PP3)
  - `FY-PP3-B` (id 30745, year=FY, parent class: FY-PP3)
  - `FY-PP3-C` (id 30746, year=FY, parent class: FY-PP3)
  - `FY-PP3-D` (id 30747, year=FY, parent class: FY-PP3)
  - `FY-PP4-A` (id 30748, year=FY, parent class: FY-PP4)
  - `FY-PP4-B` (id 30749, year=FY, parent class: FY-PP4)
  - `FY-PP4-C` (id 30750, year=FY, parent class: FY-PP4)
  - `FY-PP5-A` (id 30752, year=FY, parent class: FY-PP5)
  - `FY-PP5-B` (id 30753, year=FY, parent class: FY-PP5)
  - `FY-PP5-C` (id 30754, year=FY, parent class: FY-PP5)
  - `FY-PP5-D` (id 30755, year=FY, parent class: FY-PP5)
  - `FY-PP5-E` (id 30788, year=FY, parent class: FY-PP5)
  - `FY-PP5-F` (id 30789, year=FY, parent class: FY-PP5)
  - `FY-PP5-A_` (id 30791, year=FY, parent class: FY-PP5)
  - `FY-PP4-A_` (id 30792, year=FY, parent class: FY-PP4)
  - `FY-PP3-A_` (id 30793, year=FY, parent class: FY-PP3)

### `PPS(FY)` — Programming for Problem Solving (FY)

- subjectId: `32754`
- classes: FY-PPS1n2 (FY VSEC Programming for Prob.Solving Div1,2 Combined)
- batches (via class→batchClass (no direct SBT)): *(no batches)*

### `PPS(FY)-Lab` — Programming for Problem Solving Laboratory(FY)

- subjectId: `32755`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): FY-PPS1-A, FY-PPS1-B, FY-PPS1-C, FY-PPS1-D, FY-PPS2-A, FY-PPS2-C, FY-PPS2-D, FY-PPS2-B
- batch detail:
  - `FY-PPS1-A` (id 30764, year=FY, parent class: FY-PPS1)
  - `FY-PPS1-B` (id 30765, year=FY, parent class: FY-PPS1)
  - `FY-PPS1-C` (id 30766, year=FY, parent class: FY-PPS1)
  - `FY-PPS1-D` (id 30767, year=FY, parent class: FY-PPS1)
  - `FY-PPS2-A` (id 30768, year=FY, parent class: FY-PPS2)
  - `FY-PPS2-C` (id 30769, year=FY, parent class: FY-PPS2)
  - `FY-PPS2-D` (id 30770, year=FY, parent class: FY-PPS2)
  - `FY-PPS2-B` (id 30790, year=FY, parent class: FY-PPS2)

### `WD(FY)` — Web Design(FY)

- subjectId: `32752`
- classes: FY-WD1 (FY VSEC Web Design Div1), FY-WD2 (FY VSEC Web Design Div2)
- batches (via class→batchClass (no direct SBT)): FY-WD1-A, FY-WD1-B, FY-WD1-C, FY-WD1-D, FY-WD2-A, FY-WD2-B, FY-WD2-C, FY-WD2-D
- batch detail:
  - `FY-WD1-A` (id 30756, year=FY, parent class: FY-WD1)
  - `FY-WD1-B` (id 30757, year=FY, parent class: FY-WD1)
  - `FY-WD1-C` (id 30758, year=FY, parent class: FY-WD1)
  - `FY-WD1-D` (id 30759, year=FY, parent class: FY-WD1)
  - `FY-WD2-A` (id 30760, year=FY, parent class: FY-WD2)
  - `FY-WD2-B` (id 30761, year=FY, parent class: FY-WD2)
  - `FY-WD2-C` (id 30762, year=FY, parent class: FY-WD2)
  - `FY-WD2-D` (id 30763, year=FY, parent class: FY-WD2)

### `WD(FY)-Lab` — Web Design Laboratory(FY)

- subjectId: `32753`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): FY-WD1-A, FY-WD1-B, FY-WD1-C, FY-WD1-D, FY-WD2-A, FY-WD2-B, FY-WD2-C
- batch detail:
  - `FY-WD1-A` (id 30756, year=FY, parent class: FY-WD1)
  - `FY-WD1-B` (id 30757, year=FY, parent class: FY-WD1)
  - `FY-WD1-C` (id 30758, year=FY, parent class: FY-WD1)
  - `FY-WD1-D` (id 30759, year=FY, parent class: FY-WD1)
  - `FY-WD2-A` (id 30760, year=FY, parent class: FY-WD2)
  - `FY-WD2-B` (id 30761, year=FY, parent class: FY-WD2)
  - `FY-WD2-C` (id 30762, year=FY, parent class: FY-WD2)

## SY (Second Year B.Tech)

### `CO` — Computer Organization

- subjectId: `32534`
- classes: SY-Div1 (SY Computer Engineering Div 1), SY-Div2 (SY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

### `CoI` — Constitution of India

- subjectId: `32529`
- classes: SY-Div1 (SY Computer Engineering Div 1), SY-Div2 (SY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

### `DTL-Lab` — Development Tools Laboratory

- subjectId: `32584`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

### `Eco` — Economics (SY)

- subjectId: `32758`
- classes: SY-Div1 (SY Computer Engineering Div 1), SY-Div2 (SY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

### `MDM-DSFA` — MDM-Data Structures, Files and Algorithms

- subjectId: `32572`
- classes: SY-MDM1 (SY CSE-MDM Div1), SY-MDM2 (SY CSE-MDM Div2)
- batches (via class→batchClass (no direct SBT)): *(no batches)*

### `OE-FOS` — OE Fundamentals of Operating Systems

- subjectId: `32701`
- classes: SY-OE1 (SY CSE Open Elective Div1), SY-OE2 (SY CSE Open Elective Div2)
- batches (via class→batchClass (no direct SBT)): *(no batches)*

### `OOPD` — Object Oriented Programming and Design

- subjectId: `32699`
- classes: SY-Div1 (SY Computer Engineering Div 1), SY-Div2 (SY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

### `OOPD-Lab` — Object Oriented Programming and Design Lab

- subjectId: `32700`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

### `TOC` — Theory of Computation

- subjectId: `32661`
- classes: SY-Div1 (SY Computer Engineering Div 1), SY-Div2 (SY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

### `TOC-Tut` — Theory of Computation Tutorial

- subjectId: `32666`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): SY1-S1, SY1-S2, SY1-S3, SY1-S4, SY1-S5, SY2-S1, SY2-S2, SY2-S3, SY2-S4, SY2-S5, SY2-S6(DSY)
- batch detail:
  - `SY1-S1` (id 30629, year=SY, parent class: SY-Div1)
  - `SY1-S2` (id 30630, year=SY, parent class: SY-Div1)
  - `SY1-S3` (id 30631, year=SY, parent class: SY-Div1)
  - `SY1-S4` (id 30632, year=SY, parent class: SY-Div1)
  - `SY1-S5` (id 30633, year=SY, parent class: SY-Div1)
  - `SY2-S1` (id 30634, year=SY, parent class: SY-Div2)
  - `SY2-S2` (id 30635, year=SY, parent class: SY-Div2)
  - `SY2-S3` (id 30636, year=SY, parent class: SY-Div2)
  - `SY2-S4` (id 30637, year=SY, parent class: SY-Div2)
  - `SY2-S5` (id 30662, year=SY, parent class: SY-Div2)
  - `SY2-S6(DSY)` (id 30680, year=SY, parent class: SY-Div2)

## TY (Third Year B.Tech)

### `AI` — Artificial Intelligence

- subjectId: `32537`
- classes: TY-Div1 (TY Computer Engineering Div 1), TY-Div2 (TY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): TY1-T1, TY1-T2, TY1-T3, TY1-T4, TY1-T5, TY2-T1, TY2-T2, TY2-T3, TY2-T4, TY2-T5, TY1_EH(Hon), TY2_EH(Hon), TY1_BDA(Hon), TY2_BDA(Hon), TY_OOPD(Min), OOPD(Min), TY2-T6, TY1-ASP, TY2-ASP, TY1-BCT, TY2-BCT, TY1-DSci, TY2-DSci, TY1-PP, TY2-PP, TY1-FSD, TY2-FSD
- batch detail:
  - `TY1-T1` (id 30638, year=TY, parent class: TY-Div1)
  - `TY1-T2` (id 30639, year=TY, parent class: TY-Div1)
  - `TY1-T3` (id 30640, year=TY, parent class: TY-Div1)
  - `TY1-T4` (id 30641, year=TY, parent class: TY-Div1)
  - `TY1-T5` (id 30642, year=TY, parent class: TY-Div1)
  - `TY2-T1` (id 30643, year=TY, parent class: TY-Div2)
  - `TY2-T2` (id 30644, year=TY, parent class: TY-Div2)
  - `TY2-T3` (id 30645, year=TY, parent class: TY-Div2)
  - `TY2-T4` (id 30646, year=TY, parent class: TY-Div2)
  - `TY2-T5` (id 30647, year=TY, parent class: TY-Div2)
  - `TY1_EH(Hon)` (id 30663, year=TY, parent class: TY-Div1)
  - `TY2_EH(Hon)` (id 30664, year=TY, parent class: TY-Div2)
  - `TY1_BDA(Hon)` (id 30665, year=TY, parent class: TY-Div1)
  - `TY2_BDA(Hon)` (id 30666, year=TY, parent class: TY-Div2)
  - `TY_OOPD(Min)` (id 30673, year=TY, parent class: TY-Div1)
  - `OOPD(Min)` (id 30674, year=TY, parent class: TY-Div2)
  - `TY2-T6` (id 30679, year=TY, parent class: TY-Div2)
  - `TY1-ASP` (id 30687, year=TY, parent class: TY-Div1)
  - `TY2-ASP` (id 30688, year=TY, parent class: TY-Div2)
  - `TY1-BCT` (id 30689, year=TY, parent class: TY-Div1)
  - `TY2-BCT` (id 30690, year=TY, parent class: TY-Div2)
  - `TY1-DSci` (id 30691, year=TY, parent class: TY-Div1)
  - `TY2-DSci` (id 30692, year=TY, parent class: TY-Div2)
  - `TY1-PP` (id 30693, year=TY, parent class: TY-Div1)
  - `TY2-PP` (id 30694, year=TY, parent class: TY-Div2)
  - `TY1-FSD` (id 30695, year=TY, parent class: TY-Div1)
  - `TY2-FSD` (id 30696, year=TY, parent class: TY-Div2)

### `CN` — Computer Networks

- subjectId: `32539`
- classes: TY-Div1 (TY Computer Engineering Div 1), TY-Div2 (TY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): TY1-T1, TY1-T2, TY1-T3, TY1-T4, TY1-T5, TY2-T1, TY2-T2, TY2-T3, TY2-T4, TY2-T5, TY1_EH(Hon), TY2_EH(Hon), TY1_BDA(Hon), TY2_BDA(Hon), TY_OOPD(Min), OOPD(Min), TY2-T6, TY1-ASP, TY2-ASP, TY1-BCT, TY2-BCT, TY1-DSci, TY2-DSci, TY1-PP, TY2-PP, TY1-FSD, TY2-FSD
- batch detail:
  - `TY1-T1` (id 30638, year=TY, parent class: TY-Div1)
  - `TY1-T2` (id 30639, year=TY, parent class: TY-Div1)
  - `TY1-T3` (id 30640, year=TY, parent class: TY-Div1)
  - `TY1-T4` (id 30641, year=TY, parent class: TY-Div1)
  - `TY1-T5` (id 30642, year=TY, parent class: TY-Div1)
  - `TY2-T1` (id 30643, year=TY, parent class: TY-Div2)
  - `TY2-T2` (id 30644, year=TY, parent class: TY-Div2)
  - `TY2-T3` (id 30645, year=TY, parent class: TY-Div2)
  - `TY2-T4` (id 30646, year=TY, parent class: TY-Div2)
  - `TY2-T5` (id 30647, year=TY, parent class: TY-Div2)
  - `TY1_EH(Hon)` (id 30663, year=TY, parent class: TY-Div1)
  - `TY2_EH(Hon)` (id 30664, year=TY, parent class: TY-Div2)
  - `TY1_BDA(Hon)` (id 30665, year=TY, parent class: TY-Div1)
  - `TY2_BDA(Hon)` (id 30666, year=TY, parent class: TY-Div2)
  - `TY_OOPD(Min)` (id 30673, year=TY, parent class: TY-Div1)
  - `OOPD(Min)` (id 30674, year=TY, parent class: TY-Div2)
  - `TY2-T6` (id 30679, year=TY, parent class: TY-Div2)
  - `TY1-ASP` (id 30687, year=TY, parent class: TY-Div1)
  - `TY2-ASP` (id 30688, year=TY, parent class: TY-Div2)
  - `TY1-BCT` (id 30689, year=TY, parent class: TY-Div1)
  - `TY2-BCT` (id 30690, year=TY, parent class: TY-Div2)
  - `TY1-DSci` (id 30691, year=TY, parent class: TY-Div1)
  - `TY2-DSci` (id 30692, year=TY, parent class: TY-Div2)
  - `TY1-PP` (id 30693, year=TY, parent class: TY-Div1)
  - `TY2-PP` (id 30694, year=TY, parent class: TY-Div2)
  - `TY1-FSD` (id 30695, year=TY, parent class: TY-Div1)
  - `TY2-FSD` (id 30696, year=TY, parent class: TY-Div2)

### `CN-Lab` — Computer Networks Laboratory

- subjectId: `32540`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-T1, TY1-T2, TY1-T3, TY1-T4, TY1-T5, TY2-T1, TY2-T2, TY2-T3, TY2-T4, TY2-T5, TY2-T6
- batch detail:
  - `TY1-T1` (id 30638, year=TY, parent class: TY-Div1)
  - `TY1-T2` (id 30639, year=TY, parent class: TY-Div1)
  - `TY1-T3` (id 30640, year=TY, parent class: TY-Div1)
  - `TY1-T4` (id 30641, year=TY, parent class: TY-Div1)
  - `TY1-T5` (id 30642, year=TY, parent class: TY-Div1)
  - `TY2-T1` (id 30643, year=TY, parent class: TY-Div2)
  - `TY2-T2` (id 30644, year=TY, parent class: TY-Div2)
  - `TY2-T3` (id 30645, year=TY, parent class: TY-Div2)
  - `TY2-T4` (id 30646, year=TY, parent class: TY-Div2)
  - `TY2-T5` (id 30647, year=TY, parent class: TY-Div2)
  - `TY2-T6` (id 30679, year=TY, parent class: TY-Div2)

### `DAA` — Design and Analysis of Algorithm

- subjectId: `32640`
- classes: TY-Div1 (TY Computer Engineering Div 1), TY-Div2 (TY Computer Engineering Div 2)
- batches (via class→batchClass (no direct SBT)): TY1-T1, TY1-T2, TY1-T3, TY1-T4, TY1-T5, TY2-T1, TY2-T2, TY2-T3, TY2-T4, TY2-T5, TY1_EH(Hon), TY2_EH(Hon), TY1_BDA(Hon), TY2_BDA(Hon), TY_OOPD(Min), OOPD(Min), TY2-T6, TY1-ASP, TY2-ASP, TY1-BCT, TY2-BCT, TY1-DSci, TY2-DSci, TY1-PP, TY2-PP, TY1-FSD, TY2-FSD
- batch detail:
  - `TY1-T1` (id 30638, year=TY, parent class: TY-Div1)
  - `TY1-T2` (id 30639, year=TY, parent class: TY-Div1)
  - `TY1-T3` (id 30640, year=TY, parent class: TY-Div1)
  - `TY1-T4` (id 30641, year=TY, parent class: TY-Div1)
  - `TY1-T5` (id 30642, year=TY, parent class: TY-Div1)
  - `TY2-T1` (id 30643, year=TY, parent class: TY-Div2)
  - `TY2-T2` (id 30644, year=TY, parent class: TY-Div2)
  - `TY2-T3` (id 30645, year=TY, parent class: TY-Div2)
  - `TY2-T4` (id 30646, year=TY, parent class: TY-Div2)
  - `TY2-T5` (id 30647, year=TY, parent class: TY-Div2)
  - `TY1_EH(Hon)` (id 30663, year=TY, parent class: TY-Div1)
  - `TY2_EH(Hon)` (id 30664, year=TY, parent class: TY-Div2)
  - `TY1_BDA(Hon)` (id 30665, year=TY, parent class: TY-Div1)
  - `TY2_BDA(Hon)` (id 30666, year=TY, parent class: TY-Div2)
  - `TY_OOPD(Min)` (id 30673, year=TY, parent class: TY-Div1)
  - `OOPD(Min)` (id 30674, year=TY, parent class: TY-Div2)
  - `TY2-T6` (id 30679, year=TY, parent class: TY-Div2)
  - `TY1-ASP` (id 30687, year=TY, parent class: TY-Div1)
  - `TY2-ASP` (id 30688, year=TY, parent class: TY-Div2)
  - `TY1-BCT` (id 30689, year=TY, parent class: TY-Div1)
  - `TY2-BCT` (id 30690, year=TY, parent class: TY-Div2)
  - `TY1-DSci` (id 30691, year=TY, parent class: TY-Div1)
  - `TY2-DSci` (id 30692, year=TY, parent class: TY-Div2)
  - `TY1-PP` (id 30693, year=TY, parent class: TY-Div1)
  - `TY2-PP` (id 30694, year=TY, parent class: TY-Div2)
  - `TY1-FSD` (id 30695, year=TY, parent class: TY-Div1)
  - `TY2-FSD` (id 30696, year=TY, parent class: TY-Div2)

### `DAA-Lab` — Design and Analysis of Algorithm Lab

- subjectId: `32702`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-T1, TY1-T2, TY1-T3, TY1-T4, TY1-T5, TY2-T1, TY2-T2, TY2-T3, TY2-T4, TY2-T5, TY2-T6
- batch detail:
  - `TY1-T1` (id 30638, year=TY, parent class: TY-Div1)
  - `TY1-T2` (id 30639, year=TY, parent class: TY-Div1)
  - `TY1-T3` (id 30640, year=TY, parent class: TY-Div1)
  - `TY1-T4` (id 30641, year=TY, parent class: TY-Div1)
  - `TY1-T5` (id 30642, year=TY, parent class: TY-Div1)
  - `TY2-T1` (id 30643, year=TY, parent class: TY-Div2)
  - `TY2-T2` (id 30644, year=TY, parent class: TY-Div2)
  - `TY2-T3` (id 30645, year=TY, parent class: TY-Div2)
  - `TY2-T4` (id 30646, year=TY, parent class: TY-Div2)
  - `TY2-T5` (id 30647, year=TY, parent class: TY-Div2)
  - `TY2-T6` (id 30679, year=TY, parent class: TY-Div2)

### `DE2-ASP` — DE II - Advanced System Programming

- subjectId: `32712`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-ASP, TY2-ASP
- batch detail:
  - `TY1-ASP` (id 30687, year=TY, parent class: TY-Div1)
  - `TY2-ASP` (id 30688, year=TY, parent class: TY-Div2)

### `DE2-ASP-Lab` — DE II -  Advanced System Programming Lab

- subjectId: `32703`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-T5, TY2-T5, TY2-T6
- batch detail:
  - `TY1-T5` (id 30642, year=TY, parent class: TY-Div1)
  - `TY2-T5` (id 30647, year=TY, parent class: TY-Div2)
  - `TY2-T6` (id 30679, year=TY, parent class: TY-Div2)

### `DE2-BCT` — DE II - BlockChain Technologies

- subjectId: `32704`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-BCT, TY2-BCT
- batch detail:
  - `TY1-BCT` (id 30689, year=TY, parent class: TY-Div1)
  - `TY2-BCT` (id 30690, year=TY, parent class: TY-Div2)

### `DE2-BCT-Lab` — DE II- BlockChain Technologies Lab

- subjectId: `32705`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-T1, TY1-T2, TY2-T1, TY2-T2
- batch detail:
  - `TY1-T1` (id 30638, year=TY, parent class: TY-Div1)
  - `TY1-T2` (id 30639, year=TY, parent class: TY-Div1)
  - `TY2-T1` (id 30643, year=TY, parent class: TY-Div2)
  - `TY2-T2` (id 30644, year=TY, parent class: TY-Div2)

### `DE2-DSci` — DE II - Data Science

- subjectId: `32706`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-DSci, TY2-DSci
- batch detail:
  - `TY1-DSci` (id 30691, year=TY, parent class: TY-Div1)
  - `TY2-DSci` (id 30692, year=TY, parent class: TY-Div2)

### `DE2-DSci-Lab` — DE II - Data Science Lab

- subjectId: `32707`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY1-T3, TY1-T4, TY2-T3, TY2-T4
- batch detail:
  - `TY1-T3` (id 30640, year=TY, parent class: TY-Div1)
  - `TY1-T4` (id 30641, year=TY, parent class: TY-Div1)
  - `TY2-T3` (id 30645, year=TY, parent class: TY-Div2)
  - `TY2-T4` (id 30646, year=TY, parent class: TY-Div2)

### `MDM-FDMS` — MDM - CS - Fundamentals of Database Management Systems

- subjectId: `32713`
- classes: TY-MDM1 (TY CSE MDM Div1), TY-MDM2 (TY CSE MDM Div2)
- batches (via class→batchClass (no direct SBT)): TY-MDM1-B1, TY-MDM1-B2, TY-MDM1-B3, TY-MDM1-B4, TY-MDM2-B1, TY-MDM2-B2, TY-MDM2-B3, TY-MDM2-B4
- batch detail:
  - `TY-MDM1-B1` (id 30772, year=TY, parent class: TY-MDM1)
  - `TY-MDM1-B2` (id 30773, year=TY, parent class: TY-MDM1)
  - `TY-MDM1-B3` (id 30774, year=TY, parent class: TY-MDM1)
  - `TY-MDM1-B4` (id 30775, year=TY, parent class: TY-MDM1)
  - `TY-MDM2-B1` (id 30776, year=TY, parent class: TY-MDM2)
  - `TY-MDM2-B2` (id 30777, year=TY, parent class: TY-MDM2)
  - `TY-MDM2-B3` (id 30778, year=TY, parent class: TY-MDM2)
  - `TY-MDM2-B4` (id 30779, year=TY, parent class: TY-MDM2)

### `MDM-FDMSLab` — MDM - CS - Fundamentals of Database Management Systems Lab

- subjectId: `32756`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): TY-MDM1-B1, TY-MDM1-B2, TY-MDM1-B3, TY-MDM2-B1, TY-MDM2-B2, TY-MDM2-B3
- batch detail:
  - `TY-MDM1-B1` (id 30772, year=TY, parent class: TY-MDM1)
  - `TY-MDM1-B2` (id 30773, year=TY, parent class: TY-MDM1)
  - `TY-MDM1-B3` (id 30774, year=TY, parent class: TY-MDM1)
  - `TY-MDM2-B1` (id 30776, year=TY, parent class: TY-MDM2)
  - `TY-MDM2-B2` (id 30777, year=TY, parent class: TY-MDM2)
  - `TY-MDM2-B3` (id 30778, year=TY, parent class: TY-MDM2)

## BT / B.Tech final year

### `DE4-GIS` — DE4-GIS: Geographical Information Systems

- subjectId: `32716`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-GIS, BT2-GIS
- batch detail:
  - `BT1-GIS` (id 30677, year=BT, parent class: BT-Div1)
  - `BT2-GIS` (id 30678, year=BT, parent class: BT-Div2)

### `DE4-GIS-Lab` — DE4-GIS: Geographical Information Systems Lab

- subjectId: `32717`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-B2, BT1-B3, BT2-B3, BT2-B4
- batch detail:
  - `BT1-B2` (id 30698, year=BT, parent class: BT-Div1)
  - `BT1-B3` (id 30699, year=BT, parent class: BT-Div1)
  - `BT2-B3` (id 30704, year=BT, parent class: BT-Div2)
  - `BT2-B4` (id 30705, year=BT, parent class: BT-Div2)

### `DE4-GPU` — DE4: GPU Computing

- subjectId: `32718`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-GPU, BT2-GPU
- batch detail:
  - `BT1-GPU` (id 30675, year=BT, parent class: BT-Div1)
  - `BT2-GPU` (id 30676, year=BT, parent class: BT-Div2)

### `DE4-GPU-Lab` — DE4: GPU Computing Lab

- subjectId: `32646`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-B4, BT1-B5, BT2-B5, BT2-B6
- batch detail:
  - `BT1-B4` (id 30700, year=BT, parent class: BT-Div1)
  - `BT1-B5` (id 30701, year=BT, parent class: BT-Div1)
  - `BT2-B5` (id 30706, year=BT, parent class: BT-Div2)
  - `BT2-B6` (id 30707, year=BT, parent class: BT-Div2)

### `DE4-IBC-Lab` — DE4: Introduction of Blockchains CSC Lab

- subjectId: `32715`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-B1, BT2-B1, BT2-B2
- batch detail:
  - `BT1-B1` (id 30697, year=BT, parent class: BT-Div1)
  - `BT2-B1` (id 30702, year=BT, parent class: BT-Div2)
  - `BT2-B2` (id 30703, year=BT, parent class: BT-Div2)

### `DE4-IBCS` — Introduction of Blockchains Cryptocurrencies and Smart Contracts

- subjectId: `32714`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-IBCSC, BT2-IBCSC
- batch detail:
  - `BT1-IBCSC` (id 30708, year=BT, parent class: BT-Div1)
  - `BT2-IBCSC` (id 30709, year=BT, parent class: BT-Div2)

### `Honor4-IOT` — Honor4-IOT Security

- subjectId: `32719`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-HONORS-IOT, BT2-HONORS-IOT
- batch detail:
  - `BT1-HONORS-IOT` (id 30669, year=BT, parent class: BT-Div1)
  - `BT2-HONORS-IOT` (id 30670, year=BT, parent class: BT-Div2)

### `Honor4-RL` — Honor4-Reinforcement Learning

- subjectId: `32720`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): BT1-HONORS-RL, BT2-HONORS-RL
- batch detail:
  - `BT1-HONORS-RL` (id 30667, year=BT, parent class: BT-Div1)
  - `BT2-HONORS-RL` (id 30668, year=BT, parent class: BT-Div2)

### `Minor4-DS` — Minor4-Data Science

- subjectId: `32648`
- classes: BT-Minor (BT Minor of CSE)
- batches (via class→batchClass (no direct SBT)): *(no batches)*

## MT (M.Tech) — included for completeness

### `DMML` — Data Mining and Machine Learning

- subjectId: `32675`
- classes: MT-CE (FY M Tech Computer Engineering)
- batches (via class→batchClass (no direct SBT)): MTCE-A, MTCE-B, MTCE-DE3A, MTCE-DE3B
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)
  - `MTCE-DE3A` (id 30718, year=MT, parent class: MT-CE)
  - `MTCE-DE3B` (id 30719, year=MT, parent class: MT-CE)

### `DMML-Lab` — Data Mining and Machine Learning - Laboratory

- subjectId: `32687`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCE-A, MTCE-B
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)

### `ES` — Embedded Systems

- subjectId: `32677`
- classes: MT-CE (FY M Tech Computer Engineering)
- batches (via class→batchClass (no direct SBT)): MTCE-A, MTCE-B, MTCE-DE3A, MTCE-DE3B
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)
  - `MTCE-DE3A` (id 30718, year=MT, parent class: MT-CE)
  - `MTCE-DE3B` (id 30719, year=MT, parent class: MT-CE)

### `ES-Lab` — Embedded Systems - Laboratory

- subjectId: `32689`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCE-A, MTCE-B
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)

### `MT-AMLD` — Advanced Machine Learning and Deep

- subjectId: `32736`
- classes: MT-DS (FY M Tech Data Sciecne)
- batches (via class→batchClass (no direct SBT)): MTDS-A, MTDS-B, MTDS-C, MTDS-D, MTDS-C,D, MTDS-A,B, MTDS-DE3A, MTDS-DE3B
- batch detail:
  - `MTDS-A` (id 30683, year=MT, parent class: MT-DS)
  - `MTDS-B` (id 30684, year=MT, parent class: MT-DS)
  - `MTDS-C` (id 30685, year=MT, parent class: MT-DS)
  - `MTDS-D` (id 30686, year=MT, parent class: MT-DS)
  - `MTDS-C,D` (id 30720, year=MT, parent class: MT-DS)
  - `MTDS-A,B` (id 30721, year=MT, parent class: MT-DS)
  - `MTDS-DE3A` (id 30722, year=MT, parent class: MT-DS)
  - `MTDS-DE3B` (id 30723, year=MT, parent class: MT-DS)

### `MT-AMLD-Lab` — Advanced Machine Learning and Deep Lab

- subjectId: `32737`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTDS-A, MTDS-B, MTDS-C, MTDS-D
- batch detail:
  - `MTDS-A` (id 30683, year=MT, parent class: MT-DS)
  - `MTDS-B` (id 30684, year=MT, parent class: MT-DS)
  - `MTDS-C` (id 30685, year=MT, parent class: MT-DS)
  - `MTDS-D` (id 30686, year=MT, parent class: MT-DS)

### `MT-BDAAS` — Big Data Analytics with Apache Spark

- subjectId: `32734`
- classes: MT-DS (FY M Tech Data Sciecne)
- batches (via class→batchClass (no direct SBT)): MTDS-A, MTDS-B, MTDS-C, MTDS-D, MTDS-C,D, MTDS-A,B, MTDS-DE3A, MTDS-DE3B
- batch detail:
  - `MTDS-A` (id 30683, year=MT, parent class: MT-DS)
  - `MTDS-B` (id 30684, year=MT, parent class: MT-DS)
  - `MTDS-C` (id 30685, year=MT, parent class: MT-DS)
  - `MTDS-D` (id 30686, year=MT, parent class: MT-DS)
  - `MTDS-C,D` (id 30720, year=MT, parent class: MT-DS)
  - `MTDS-A,B` (id 30721, year=MT, parent class: MT-DS)
  - `MTDS-DE3A` (id 30722, year=MT, parent class: MT-DS)
  - `MTDS-DE3B` (id 30723, year=MT, parent class: MT-DS)

### `MT-BDAAS-Lab` — Big Data Analytics with Apache Spark Lab

- subjectId: `32735`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTDS-A, MTDS-B, MTDS-C, MTDS-D
- batch detail:
  - `MTDS-A` (id 30683, year=MT, parent class: MT-DS)
  - `MTDS-B` (id 30684, year=MT, parent class: MT-DS)
  - `MTDS-C` (id 30685, year=MT, parent class: MT-DS)
  - `MTDS-D` (id 30686, year=MT, parent class: MT-DS)

### `MT-DFDR` — MTech Digital Forensics and Data Recovery

- subjectId: `32683`
- classes: MT-CSIS (FY M Tech Computer Science and Information Security)
- batches (via class→batchClass (no direct SBT)): MTCSIS-A, MTCSIS-B, MTCSIS-DE3A, MTCSIS-DE3B
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)
  - `MTCSIS-DE3A` (id 30710, year=MT, parent class: MT-CSIS)
  - `MTCSIS-DE3B` (id 30711, year=MT, parent class: MT-CSIS)

### `MT-DFDR-Lab` — MTech Digital Forensics and Data Recovery  - Laboratory

- subjectId: `32692`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCSIS-A, MTCSIS-B
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)

### `MT-DL` — Deep Learning

- subjectId: `32724`
- classes: MT-AI (FY M TechArtificial Intelligence)
- batches (via class→batchClass (no direct SBT)): MTAI-DE2A, MTAI-DE2B, MTAI-DE3A, MTAI-DE3B
- batch detail:
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)

### `MT-ETCSA` — MTech Effective Technical Communication Skills

- subjectId: `32743`
- classes: MT-CE (FY M Tech Computer Engineering)
- batches (via class→batchClass (no direct SBT)): MTCE-A, MTCE-B, MTCE-DE3A, MTCE-DE3B
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)
  - `MTCE-DE3A` (id 30718, year=MT, parent class: MT-CE)
  - `MTCE-DE3B` (id 30719, year=MT, parent class: MT-CE)

### `MT-ETCSALab` — MTech Effective Technical Communication Skills Lab

- subjectId: `32757`
- classes: MT-CE (FY M Tech Computer Engineering), MT-CSIS (FY M Tech Computer Science and Information Security), MT-AI (FY M TechArtificial Intelligence), MT-DS (FY M Tech Data Sciecne)
- batches (via class→batchClass (no direct SBT)): MTCSIS-A, MTCSIS-B, MTDS-A, MTDS-B, MTDS-C, MTDS-D, MTCSIS-DE3A, MTCSIS-DE3B, MTAI-DE2A, MTAI-DE2B, MTAI-DE3A, MTAI-DE3B, MTCE-A, MTCE-B, MTCE-DE3A, MTCE-DE3B, MTDS-C,D, MTDS-A,B, MTDS-DE3A, MTDS-DE3B
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)
  - `MTDS-A` (id 30683, year=MT, parent class: MT-DS)
  - `MTDS-B` (id 30684, year=MT, parent class: MT-DS)
  - `MTDS-C` (id 30685, year=MT, parent class: MT-DS)
  - `MTDS-D` (id 30686, year=MT, parent class: MT-DS)
  - `MTCSIS-DE3A` (id 30710, year=MT, parent class: MT-CSIS)
  - `MTCSIS-DE3B` (id 30711, year=MT, parent class: MT-CSIS)
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)
  - `MTCE-DE3A` (id 30718, year=MT, parent class: MT-CE)
  - `MTCE-DE3B` (id 30719, year=MT, parent class: MT-CE)
  - `MTDS-C,D` (id 30720, year=MT, parent class: MT-DS)
  - `MTDS-A,B` (id 30721, year=MT, parent class: MT-DS)
  - `MTDS-DE3A` (id 30722, year=MT, parent class: MT-DS)
  - `MTDS-DE3B` (id 30723, year=MT, parent class: MT-DS)

### `MT-GAN` — Generative Adversarial Network

- subjectId: `32726`
- classes: MT-AI (FY M TechArtificial Intelligence)
- batches (via class→batchClass (no direct SBT)): MTAI-DE2A, MTAI-DE2B, MTAI-DE3A, MTAI-DE3B
- batch detail:
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)

### `MT-GAN-Lab` — Generative Adversarial Network Lab

- subjectId: `32727`
- classes: MT-AI (FY M TechArtificial Intelligence)
- batches (via class→batchClass (no direct SBT)): MTAI-DE2A, MTAI-DE2B, MTAI-DE3A, MTAI-DE3B
- batch detail:
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)

### `MT-MLOS` — ML Ops and Systems

- subjectId: `32738`
- classes: MT-DS (FY M Tech Data Sciecne)
- batches (via class→batchClass (no direct SBT)): MTDS-A, MTDS-B, MTDS-C, MTDS-D, MTDS-C,D, MTDS-A,B, MTDS-DE3A, MTDS-DE3B
- batch detail:
  - `MTDS-A` (id 30683, year=MT, parent class: MT-DS)
  - `MTDS-B` (id 30684, year=MT, parent class: MT-DS)
  - `MTDS-C` (id 30685, year=MT, parent class: MT-DS)
  - `MTDS-D` (id 30686, year=MT, parent class: MT-DS)
  - `MTDS-C,D` (id 30720, year=MT, parent class: MT-DS)
  - `MTDS-A,B` (id 30721, year=MT, parent class: MT-DS)
  - `MTDS-DE3A` (id 30722, year=MT, parent class: MT-DS)
  - `MTDS-DE3B` (id 30723, year=MT, parent class: MT-DS)

### `MT-MLOS-Lab` — ML Ops and Systems Lab

- subjectId: `32739`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTDS-A, MTDS-B, MTDS-C, MTDS-D
- batch detail:
  - `MTDS-A` (id 30683, year=MT, parent class: MT-DS)
  - `MTDS-B` (id 30684, year=MT, parent class: MT-DS)
  - `MTDS-C` (id 30685, year=MT, parent class: MT-DS)
  - `MTDS-D` (id 30686, year=MT, parent class: MT-DS)

### `MT-NLP` — PSEC3- Natural Language Processing

- subjectId: `32733`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTAI-DE3A, MTDS-DE3B
- batch detail:
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTDS-DE3B` (id 30723, year=MT, parent class: MT-DS)

### `MT-NS` — MTech Network Security

- subjectId: `32681`
- classes: MT-CSIS (FY M Tech Computer Science and Information Security)
- batches (via class→batchClass (no direct SBT)): MTCSIS-A, MTCSIS-B, MTCSIS-DE3A, MTCSIS-DE3B
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)
  - `MTCSIS-DE3A` (id 30710, year=MT, parent class: MT-CSIS)
  - `MTCSIS-DE3B` (id 30711, year=MT, parent class: MT-CSIS)

### `MT-NS-Lab` — MTech Network Security - Laboratory

- subjectId: `32690`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCSIS-A, MTCSIS-B
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)

### `MT-OT` — Optimization Techniques

- subjectId: `32728`
- classes: MT-AI (FY M TechArtificial Intelligence)
- batches (via class→batchClass (no direct SBT)): MTAI-DE2A, MTAI-DE2B, MTAI-DE3A, MTAI-DE3B
- batch detail:
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)

### `MT-OT-Lab` — Optimization Techniques Lab

- subjectId: `32729`
- classes: MT-AI (FY M TechArtificial Intelligence)
- batches (via class→batchClass (no direct SBT)): MTAI-DE2A, MTAI-DE2B, MTAI-DE3A, MTAI-DE3B
- batch detail:
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)

### `MT-WNS` — MTech Wireless Networks

- subjectId: `32682`
- classes: MT-CSIS (FY M Tech Computer Science and Information Security)
- batches (via class→batchClass (no direct SBT)): MTCSIS-A, MTCSIS-B, MTCSIS-DE3A, MTCSIS-DE3B
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)
  - `MTCSIS-DE3A` (id 30710, year=MT, parent class: MT-CSIS)
  - `MTCSIS-DE3B` (id 30711, year=MT, parent class: MT-CSIS)

### `MT-WNS-Lab` — MTech Wireless Networks and Security - Laboratory

- subjectId: `32691`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCSIS-A, MTCSIS-B
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)

### `MTDL-Lab` — Deep Learning Lab

- subjectId: `32725`
- classes: MT-AI (FY M TechArtificial Intelligence)
- batches (via class→batchClass (no direct SBT)): MTAI-DE2A, MTAI-DE2B, MTAI-DE3A, MTAI-DE3B
- batch detail:
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)
  - `MTAI-DE3A` (id 30714, year=MT, parent class: MT-AI)
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)

### `OE-DS` — OE:Data Structures

- subjectId: `32721`
- classes: MT-OE (FY M Tech Open Elective class)
- batches (via class→batchClass (no direct SBT)): *(no batches)*

### `PSEC2-BT` — PSEC2- Blockchain Technology

- subjectId: `32722`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCSIS-A
- batch detail:
  - `MTCSIS-A` (id 30681, year=MT, parent class: MT-CSIS)

### `PSEC2-CCS` — PSEC2- Cloud Computing and Security

- subjectId: `32684`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCSIS-B
- batch detail:
  - `MTCSIS-B` (id 30682, year=MT, parent class: MT-CSIS)

### `PSEC2-CCV` — PSEC2-Cloud Computing and Virtualization

- subjectId: `32678`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCE-A
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)

### `PSEC2-CV` — PSEC2- Computer Vision

- subjectId: `32740`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTDS-A,B
- batch detail:
  - `MTDS-A,B` (id 30721, year=MT, parent class: MT-DS)

### `PSEC2-EAI` — PSEC2- Explainable Artificial Intelligence

- subjectId: `32730`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTAI-DE2A
- batch detail:
  - `MTAI-DE2A` (id 30712, year=MT, parent class: MT-AI)

### `PSEC2-MLPS` — PSEC2- ML-OPS

- subjectId: `32731`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTAI-DE2B
- batch detail:
  - `MTAI-DE2B` (id 30713, year=MT, parent class: MT-AI)

### `PSEC2-MTRP` — PSEC2- R Programming

- subjectId: `32741`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTDS-C,D
- batch detail:
  - `MTDS-C,D` (id 30720, year=MT, parent class: MT-DS)

### `PSEC2-NLP` — PSEC2-Natural Language Processing

- subjectId: `32679`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCE-B
- batch detail:
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)

### `PSEC3-DL` — PSEC3-Deep Learning

- subjectId: `32673`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCE-DE3A
- batch detail:
  - `MTCE-DE3A` (id 30718, year=MT, parent class: MT-CE)

### `PSEC3-GAN` — PSEC3- Generative Adversarial Network

- subjectId: `32742`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTDS-DE3A
- batch detail:
  - `MTDS-DE3A` (id 30722, year=MT, parent class: MT-DS)

### `PSEC3-GNN` — PSEC3- Graph Neural Network

- subjectId: `32732`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTAI-DE3B
- batch detail:
  - `MTAI-DE3B` (id 30715, year=MT, parent class: MT-AI)

### `PSEC3-ITS` — PSEC3- Internet of Things and Security

- subjectId: `32723`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCSIS-DE3B
- batch detail:
  - `MTCSIS-DE3B` (id 30711, year=MT, parent class: MT-CSIS)

### `PSEC3-MT` — PSEC3-Multicore Technology

- subjectId: `32680`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCE-DE3B
- batch detail:
  - `MTCE-DE3B` (id 30719, year=MT, parent class: MT-CE)

### `PSEC3-WS` — PSEC3- Web Security

- subjectId: `32685`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCSIS-DE3A
- batch detail:
  - `MTCSIS-DE3A` (id 30710, year=MT, parent class: MT-CSIS)

### `SIC` — Security in Computing

- subjectId: `32676`
- classes: MT-CE (FY M Tech Computer Engineering)
- batches (via class→batchClass (no direct SBT)): MTCE-A, MTCE-B, MTCE-DE3A, MTCE-DE3B
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)
  - `MTCE-DE3A` (id 30718, year=MT, parent class: MT-CE)
  - `MTCE-DE3B` (id 30719, year=MT, parent class: MT-CE)

### `SIC-Lab` — Security in Computing - Laboratory

- subjectId: `32688`
- classes: *(no class — batch-only)*
- batches (subjectBatchTeacher): MTCE-A, MTCE-B
- batch detail:
  - `MTCE-A` (id 30716, year=MT, parent class: MT-CE)
  - `MTCE-B` (id 30717, year=MT, parent class: MT-CE)

## Questions / confusing cases

### Mapping rule (please confirm)

1. **Lectures vs batches:** In Taasika, lectures are assigned to *classes* (`subjectClassTeacher`); only labs/tuts/electives are assigned to *batches* (`subjectBatchTeacher`). For lecture-only subjects below, should the map say “no batches” (strict), or list every batch under the parent class via `batchClass` (current inferred behaviour for e.g. `DS(FY)`, `CO`, `AI`)?
2. **Include M.Tech?** You asked for FY/SY/TY/BTech. Snapshot 240 also has **42 MT subjects** (including all `PSEC`*). Keep them in a separate section, or drop them from this map?

### Lecture-only (class yes, batch no)

These have teachers on a class but no `subjectBatchTeacher` and no batches under that class:

- **MDM-DSFA** → SY-MDM1, SY-MDM2
- **OE-FOS** → SY-OE1, SY-OE2
- **Minor4-DS** → BT-Minor only (no batches under BT-Minor; meanwhile `BT1-MINOR-DS` / `BT2-MINOR-DS` batches exist unused by this subject)
- **FY-Reserved** → FY-Reserved1/2/3
- **AIMA** → FY-AIMA1/2/3
- **OE-DS** → MT-OE (M.Tech open elective)
- **PPS(FY)** → only combined class **FY-PPS1n2** (no `batchClass` under that combined class)

### Div / combined-class mismatches

1. **PP(FY) vs PP(FY)-Lab:** Lecture is on FY-PP1, FY-PP2, FY-PP3, and combined **FY-PP4n5**. Lab batches include FY-PP4-* and FY-PP5-* (and duplicate-looking `FY-PP3-A_`, `FY-PP4-A_`, `FY-PP5-A_`). Should Div4/5 lecture be treated as the combined class only, or also FY-PP4 / FY-PP5 individually?
2. **PPS(FY) vs PPS(FY)-Lab:** Lecture only on **FY-PPS1n2**; lab on FY-PPS1-A..D and FY-PPS2-A..D. Is the combined lecture meant to cover both lab divisions?

### Data quirks

1. **TY-Minor** class has `semester=8` (same as BT) while short name is TY — treat as TY or BT?
2. **SIC / DMML / ES** (and labs) sit under **MT-CE**, not B.Tech TY/BT, despite undergrad-looking names. Confirm these are M.Tech CE courses in this snapshot.
3. **Honor4-IOT / Honor4-RL** map to BT via batches `BT1-HONORS-IOT` etc., but there are also unused-looking `IOT Div 1/2` batches — ignore those?

