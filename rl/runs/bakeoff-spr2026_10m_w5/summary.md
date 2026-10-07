## Per instance and arm (median over seeds, IQR for C)

|                          |   C_median |   C_iqr |   C_checker_median |   assigned_median |   hard_max |   soft_median |   wall_median |   committed_median |   n |
|:-------------------------|-----------:|--------:|-------------------:|------------------:|-----------:|--------------:|--------------:|-------------------:|----:|
| ('spr2026_10m_w5', 'B0') |          0 |       0 |                  0 |                 1 |          0 |            25 |       900.324 |     2483.5         |  10 |
| ('spr2026_10m_w5', 'B1') |          0 |       0 |                  0 |                 1 |          0 |            25 |       900.205 |     2555           |  10 |
| ('spr2026_10m_w5', 'B2') |          0 |       0 |                  0 |                 1 |          0 |            15 |       900.016 |        3.08862e+06 |  10 |

## Relative reduction of R versus B1: (C_B1 - C_R) / C_B1

(arms B1 and/or R missing)

## Co-primary bounds (held-out term)


## Secondary metrics (median over seeds)

|                          |   zero_conflict |   pair_rate |   reach_040 |   reach_030 |   reach_025 |   last_c_improvement_sec |   disagreement |
|:-------------------------|----------------:|------------:|------------:|------------:|------------:|-------------------------:|---------------:|
| ('spr2026_10m_w5', 'B0') |               1 |           0 |           0 |           0 |           0 |                        0 |            nan |
| ('spr2026_10m_w5', 'B1') |               1 |           0 |           0 |           0 |           0 |                        0 |            nan |
| ('spr2026_10m_w5', 'B2') |               1 |           0 |           0 |           0 |           0 |                        0 |            nan |

## Overhead ratio (B0 iterations/sec divided by arm iterations/sec)

| instance       | arm   |   overhead_ratio |
|:---------------|:------|-----------------:|
| spr2026_10m_w5 | B0    |            1     |
| spr2026_10m_w5 | B1    |            0.972 |
| spr2026_10m_w5 | B2    |            0.001 |

## Soft constraints (median over seeds)

|                          |   time_pref |   room_pref |   dist_pref |   soft_penalty |   student_conflict_criterion |   hard_student_conflict_criterion |   too_big_rooms |   useless_half_hours |   back_to_back_instructor |   broken_time_patterns |   total_value |
|:-------------------------|------------:|------------:|------------:|---------------:|-----------------------------:|----------------------------------:|----------------:|---------------------:|--------------------------:|-----------------------:|--------------:|
| ('spr2026_10m_w5', 'B0') |           0 |          25 |           0 |             25 |                            0 |                                 0 |             333 |                    0 |                         0 |                     26 |       69.3964 |
| ('spr2026_10m_w5', 'B1') |           0 |          25 |           0 |             25 |                            0 |                                 0 |             333 |                    0 |                         0 |                     26 |       69.3964 |
| ('spr2026_10m_w5', 'B2') |           0 |          15 |           0 |             15 |                            0 |                                 0 |             362 |                    0 |                         0 |                     28 |       63.7197 |

B0/B1/B2 use TimetableComparator; L/R use LexicographicComparator (unassigned, then C, then unweighted time+room+distribution); the step reward is unchanged.