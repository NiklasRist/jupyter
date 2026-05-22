# Project Plan: Predicting Power Generation

## 1. Objectives
The primary goal is to leverage historical generation and weather data to build a predictive model for DC and AC power output for the next few days. This includes identifying patterns in both generation and weather data to understand their interaction.

## 2. Smart Column Reference
| Column | Description | Formula / Method |
| :--- | :--- | :--- |
| `hour_sin`, `hour_cos` | Cyclical time representation | `sin/cos(2 * pi * hour / 24)` |
| `IRRADIATION_LAG1` | Previous window irradiation | `shift(1)` |
| `IRRADIATION_TREND` | Current change in sunlight | `IRRADIATION - IRRADIATION_LAG1` |
| `DC_POWER_LAG1` | Previous window power | `shift(1)` |
| `DC_POWER_PREV_DAY` | Power exactly 24h ago | `shift(96)` (for 15min intervals) |
| `AC_EFFICIENCY` | Total system efficiency | `AC_POWER / IRRADIATION` |
| `MAINTENANCE_PROBABILITY`| Flag for conversion path faults | Low AC/Inv Efficiency + High DC Eff |
| `IRRAD_TEMP_INTERACTION` | Combined heat/light effect | `IRRADIATION * MODULE_TEMPERATURE` |
| `ROLLING_AVG_DC_3HR` | Smoothed power signal | 12-interval rolling mean |

## 3. Methodology
### Phase 1: Pattern Identification (Generation)
1. **Inverter Analysis**: Split data by `SOURCE_KEY` to analyze how different inverters respond to similar irradiation levels.
2. **Yield Baselines**: Calculate average hourly and daily yield to establish seasonal and daily performance curves.
3. **Fluctuation Analysis**: Analyze daily and hourly yield fluctuations.
4. **Temporal Correlation**: Correlate `DATE_TIME` with hourly yield to find seasonal/daily trends using `hour` and `month`.
5. **Autocorrelation**: Use `DC_POWER_LAG1` and `DC_POWER_PREV_DAY` to quantify how much of today's output is explained by recent history.

### Phase 2: Weather Pattern Analysis
1. **Condition Optimization**: Determine optimal weather conditions for panels (Irradiation vs. Temperature).
2. **Clustering/Categorization**: Use `DAILY_AVG_IRRADIATION` and `DAILY_AVG_TEMP_AMBIENT` to categorize days (e.g., Clear, Overcast, Hot, Mild).
3. **Forecasting Prep**: Leverage `IRRADIATION_LAG1` and `IRRADIATION_TREND` to model cloud movement and predict irradiation for the next window.
4. **Fluctuation Correlation**: Correlate weather patterns with hourly and/or daily generation fluctuations.

### Phase 3: Predictive Modeling & Evaluation
1. **Feature Selection**: Combine `IRRADIATION`, `MODULE_TEMPERATURE`, `hour_sin/cos`, `IRRADIATION_TREND`, `DC_POWER_LAG1`, and `IRRAD_TEMP_INTERACTION`.
2. **Model Selection**: Train Regression models (Random Forest, XGBoost, LightGBM) or Time-Series models (Prophet).
3. **Performance Metrics**: Evaluate using MAE (Mean Absolute Error), RMSE (Root Mean Squared Error), and R-squared.
4. **Diagnostic Evaluation**:
    * **Feature Importance**: Analyze which smart columns (e.g., `IRRAD_TEMP_INTERACTION`) contribute most to the model.
    * **Error Analysis**: Identify if the model fails specifically on cloudy days (using `DAILY_MAX_IRRADIATION` as a proxy).

## 4. Technical Rationale
* **Cyclical Time**: Ensures the model understands that 23:59 is adjacent to 00:00, preventing "jumps" in predictions at midnight.
* **Weather Lags**: These act as a "localized radar," allowing the model to react to incoming weather changes.
* **Interaction Terms**: Photovoltaic efficiency drops as temperature rises. The interaction term allows the model to "penalize" output during the hottest parts of the day.
* **Autoregression**: Solar output is highly stable day-to-day; yesterday's data is often the strongest predictor for today.
* **Plant-Wide Reference**: Since we have one weather sensor per plant, we treat it as a *Reference Baseline* for the entire array to normalize expectations for all inverters in that plant.

## 5. Constraints & Assumptions
* **Sensor Representativeness**: We assume the single weather sensor per plant (Irradiation/Module Temp) is a proxy for the whole array. However, the physical distance between the sensor and specific panel strings could introduce localized bias in weather-power correlation.
* **Sensor Health**: We assume the reference sensor is clean and calibrated. If the sensor panel itself is soiled, the entire plant baseline will be skewed.
