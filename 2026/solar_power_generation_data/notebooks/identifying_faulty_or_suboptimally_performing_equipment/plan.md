# Project Plan: Identifying Faulty Equipment

## 1. Objectives
Detect suboptimally performing inverters and panels by comparing performance against plant averages, historical baselines, and the plant's thermal reference.

## 2. Smart Column Reference
| Column | Description | Formula / Method |
| :--- | :--- | :--- |
| `INVERTER_EFFICIENCY` | DC to AC conversion health | `AC_POWER / DC_POWER` |
| `AC_EFFICIENCY` | Grid-level path health | `AC_POWER / IRRADIATION` |
| `RELATIVE_DC_PERF` | Peer-to-peer DC comparison | `DC_POWER / Plant_Mean_DC` |
| `RELATIVE_AC_PERF` | Peer-to-peer AC comparison | `AC_POWER / Plant_Mean_AC` |
| `MAINTENANCE_PROBABILITY`| Flag for non-panel faults | Low AC/Inv Efficiency + High DC Eff |
| `DAILY_YIELD` | Total daily energy | Sum of 15min yield intervals |
| `TEMP_DELTA_A_M` | Plant-wide thermal baseline | `MODULE_TEMP - AMBIENT_TEMP` |
| `DC_POWER_PREV_DAY` | Historical consistency check | `shift(96)` |

## 3. Methodology
### Phase 1: Core Research Questions
1. **Average Lifespan**: Use the 34-day window to check for rapid degradation or consistently low performers relative to their `DC_POWER_PREV_DAY`.
2. **Fault Identification**: Determine if a panel/inverter is faulty vs. suboptimally performing using `INVERTER_EFFICIENCY` and `RELATIVE_DC_PERF`.
3. **Trend Analysis**: Analyze the long-term trend in output by looking at `DAILY_YIELD` normalized by `DAILY_AVG_IRRADIATION`.
4. **Baseline Selection**: Identify "Peak Performance" windows (likely after cleaning) to use as a "Golden Standard" for each `SOURCE_KEY`.
5. **Panel Type Analysis**: Cluster inverters based on `DC_POWER` vs `IRRADIATION` curves to identify potential differences in panel technology or orientation.

### Phase 2: Hardware Diagnostic & Peer Comparison
1. **Inverter Health**: Flag inverters where `INVERTER_EFFICIENCY` is consistently low or where AC output lags peer averages (`RELATIVE_AC_PERF`).
2. **Spatial Normalization**: Use `RELATIVE_DC_PERF` to "cancel out" weather variability. Units staying significantly below 1.0 while others are high are likely shaded or faulty.
3. **Thermal Baseline Analysis**: Compare an individual unit's electrical output against the plant-wide `TEMP_DELTA_A_M`. If a unit's output drops disproportionately as the reference temperature rises, it suggests cooling issues or equipment-specific heat sensitivity.

### Phase 3: Action Plan
1. **Efficiency Ranking**: Rank all `SOURCE_KEY`s by their mean `INVERTER_EFFICIENCY` and `AC_EFFICIENCY`.
2. **Yield Normalization**: Calculate `DAILY_YIELD / DAILY_AVG_IRRADIATION` to normalize daily performance.
3. **Visualization**: Compare the power curves of the worst-performing inverters against the "Golden Standard" (the best inverter) to visualize the performance gap.

## 4. Technical Rationale
* **Relative Performance**: This is the most robust diagnostic tool. It uses the entire plant as a "control group" for every single timestamp, effectively canceling out weather variability without needing per-inverter sensors.
* **Efficiency Separation**: By splitting diagnostics into DC (panels) and AC (inverters), we can isolate whether a fault is on the roof or in the inverter cabinet.
* **Thermal Reference Baseline**: Since we lack per-panel sensors, we use the plant's single weather sensor as a "Golden Standard" to model the expected Power-Temperature curve. Units that deviate from this expected curve are flagged for inspection.

## 5. Constraints & Assumptions
* **Sensor Representativeness**: We acknowledge that the single weather sensor per plant is a point measurement. Physical distance between the sensor and specific panel strings could introduce localized bias in weather-power correlation.
* **Inverter Uniformity**: We assume all inverters are of the same model and specification unless clustering analysis suggests otherwise.
