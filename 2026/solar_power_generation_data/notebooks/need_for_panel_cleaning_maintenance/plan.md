# Project Plan: Panel Cleaning & Maintenance

## 1. Objectives
Identify cleaning events, calculate the impact of soiling on yield, and determine the optimal cleaning frequency through cost-benefit analysis.

## 2. Smart Column Reference
| Column | Description | Formula / Method |
| :--- | :--- | :--- |
| `DC_EFFICIENCY` | Normalized panel performance | `DC_POWER / IRRADIATION` |
| `EFFICIENCY_SURGE` | Relative efficiency jump | `DC_EFFICIENCY / DC_EFFICIENCY_PREV_DAY` |
| `CLEANING_PROBABILITY` | Flag for maintenance events | `1` if `SURGE > 1.2` and sunlight exists |
| `SOILING_POTENTIAL` | Risk of dust accumulation | High `MOD_TEMP` + Negative `IRRAD_TREND` |
| `TEMP_DELTA_A_M` | Plant-wide thermal baseline | `MODULE_TEMP - AMBIENT_TEMP` |
| `ROLLING_AVG_DC_3HR` | Smoothed performance signal | 12-interval rolling mean |
| `IRRAD_TEMP_INTERACTION`| Normalized power proxy | `IRRADIATION * MODULE_TEMPERATURE` |

## 3. Methodology
### Phase 1: Event Identification & Isolation
1. **Cleaning Detection**: Monitor `CLEANING_PROBABILITY` and `EFFICIENCY_SURGE` to detect sudden jumps in performance.
2. **Trend Analysis**: Correlate time with yield and power generation to identify long-term degradation trends.
3. **Signal Normalization**: 
    * Use `DC_EFFICIENCY` to isolate "dirty" vs "clean" states from weather.
    * Use `IRRAD_TEMP_INTERACTION` to normalize power data; sudden increases in normalized power while irradiation is constant indicate cleaning.
4. **Attribution**: Determine what change in yield was due to cleaning vs. other factors (weather, defects).

### Phase 2: Weather & Cleanliness Impact
1. **Categorization**: Use `DAILY_MAX_IRRADIATION` to distinguish between cloudy and sunny days.
2. **Rain Correlation**: Infer rain events (low irradiation + low temperature delta) and correlate with cleaning effects on yield.
3. **Weather Filtering**: Filter out weather-driven fluctuations to isolate the pure "dirty panel" signal.
4. **Soiling Rate**: Calculate the daily decline in `DC_EFFICIENCY` during high `SOILING_POTENTIAL` periods.

### Phase 3: Optimal Cleaning Frequency (Cost-Benefit)
1. **Regression Classification**: Define "classes" of performance regression (e.g., 5%, 10%, 15%) to trigger maintenance.
2. **Frequency Prediction**: Build a model to predict optimal cleaning intervals based on:
    * Weather data (rain, dust, etc.)
    * Season (e.g., Indian monsoon vs. dry season)
    * Acceptable regression limits
    * Estimated maintenance costs
3. **Strategic Planning**: Use `DAILY_AVG_IRRADIATION` to weigh the importance of cleaning (beneficial before high-irradiation periods).

## 4. Technical Rationale
* **Efficiency Surge**: Automates the detection of cleaning events by looking for performance "discontinuities" that cannot be explained by weather alone.
* **Soiling Potential**: High module temperatures (measured at the reference sensor) without high DC output suggest that energy is being converted to heat.
* **Normalization**: Dividing power by irradiation is the only way to compare a cloudy "clean" day with a sunny "dirty" day fairly.
* **Temperature Delta**: We use the plant's single weather sensor to establish a reference thermal state. Deviations in power generation relative to this thermal baseline help quantify the insulating effect of dust.
* **Rolling Averages**: 15-minute data can be noisy. 3-hour averages smooth out these transients to reveal the true underlying performance of the panel surfaces across the array.

## 5. Constraints & Assumptions
* **Single Point Reference**: We assume the weather sensor (one per plant) is a valid proxy for the entire array. We acknowledge that the sensor's specific location may not capture localized weather variations or "hotspots" on distant inverters.
* **Sensor Health**: The analysis depends on the reference sensor being clean. If the sensor panel itself is soiled, the baseline for the entire plant will be skewed.
