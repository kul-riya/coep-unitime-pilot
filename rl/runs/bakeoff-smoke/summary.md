## Per instance and arm (median over seeds, IQR for C)

|                          |   C_median |   C_iqr |   C_checker_median |   assigned_median |   hard_max |   soft_median |   wall_median |   committed_median |   n |
|:-------------------------|-----------:|--------:|-------------------:|------------------:|-----------:|--------------:|--------------:|-------------------:|----:|
| ('synthetic-hard', 'B0') |     0.1667 |  0.0333 |             0.1667 |                 1 |          0 |          82.5 |       15.1584 |              135.5 |   2 |
| ('synthetic-hard', 'B1') |     0.1333 |  0      |             0.1333 |                 1 |          0 |          83.5 |       15.4685 |              158.5 |   2 |
| ('synthetic-hard', 'B2') |     0.1333 |  0      |             0.1333 |                 1 |          0 |          85   |       15.03   |            68659.5 |   2 |
| ('synthetic-hard', 'L')  |     0.1333 |  0      |             0.1333 |                 1 |          0 |         125.5 |       15.0231 |            59978.5 |   2 |
| ('synthetic-hard', 'R')  |     0.2667 |  0      |             0.2667 |                 1 |          0 |          92   |       15.2589 |            96379   |   2 |

## Relative reduction of R versus B1: (C_B1 - C_R) / C_B1

| instance       |   C_B1 |    C_R |   relative_reduction |
|:---------------|-------:|-------:|---------------------:|
| synthetic-hard | 0.1333 | 0.2667 |                   -1 |

Median relative reduction across instances: **-1.000** (threshold 0.25) -> FAIL
Wilcoxon with the instance as unit needs >= 2 instances; exploratory per-seed pairing below.
Exploratory per-seed Wilcoxon: W=0.0, p=1.0000, n=2

## Co-primary bounds (held-out term)

| instance       | assigned_within_1pt   | hard_zero   | soft_within_10pct   | wall_within_2x_B0   |
|:---------------|:----------------------|:------------|:--------------------|:--------------------|
| synthetic-hard | True                  | True        | False               | True                |

## Secondary metrics (median over seeds)

|                          |   zero_conflict |   pair_rate |   reach_040 |   reach_030 |   reach_025 |   disagreement |
|:-------------------------|----------------:|------------:|------------:|------------:|------------:|---------------:|
| ('synthetic-hard', 'B0') |          0.8333 |      0.0093 |           0 |           0 |         0   |            nan |
| ('synthetic-hard', 'B1') |          0.8667 |      0.0074 |           0 |           0 |         0   |            nan |
| ('synthetic-hard', 'B2') |          0.8667 |      0.0037 |           0 |           0 |         0   |            nan |
| ('synthetic-hard', 'L')  |          0.8667 |      0.0074 |           0 |           0 |         2.5 |            nan |
| ('synthetic-hard', 'R')  |          0.7333 |      0.0148 |           0 |           0 |       nan   |            nan |

## Overhead ratio (B0 iterations/sec divided by arm iterations/sec)

| instance       | arm   |   overhead_ratio |
|:---------------|:------|-----------------:|
| synthetic-hard | B0    |            1     |
| synthetic-hard | B1    |            0.872 |
| synthetic-hard | B2    |            0.002 |
| synthetic-hard | L     |            0.002 |
| synthetic-hard | R     |            0.001 |