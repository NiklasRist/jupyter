import pandas as pd
import numpy as np
import os

# Define paths to original data files, relative to the script's location
script_dir = os.path.dirname(__file__)
base_data_path = os.path.abspath(os.path.join(script_dir, '../data/'))

p1_gen_path = os.path.join(base_data_path, 'Plant_1_Generation_Data (2).csv')
p1_weather_path = os.path.join(base_data_path, 'Plant_1_Weather_Sensor_Data (2).csv')
p2_gen_path = os.path.join(base_data_path, 'Plant_2_Generation_Data (2).csv')
p2_weather_path = os.path.join(base_data_path, 'Plant_2_Weather_Sensor_Data (1).csv')

print(f"Loading data from: {base_data_path}")

# --- Function to Load, Augment, and Merge Data for Generation Files ---
def load_augment_merge_generation_data(gen_file, weather_file, plant_id_val, dayfirst_gen=False):
    gen_df = pd.read_csv(gen_file)
    weather_df = pd.read_csv(weather_file)

    # Convert DATE_TIME to datetime objects
    gen_df['DATE_TIME'] = pd.to_datetime(gen_df['DATE_TIME'], dayfirst=dayfirst_gen)
    weather_df['DATE_TIME'] = pd.to_datetime(weather_df['DATE_TIME'])

    gen_df['PLANT_ID'] = plant_id_val

    # Aggregate weather data for merge
    weather_agg = weather_df.groupby('DATE_TIME').agg({
        'AMBIENT_TEMPERATURE': 'mean',
        'MODULE_TEMPERATURE': 'mean',
        'IRRADIATION': 'mean'
    }).reset_index()
    weather_agg['PLANT_ID'] = plant_id_val

    # Merge
    merged_df = pd.merge(gen_df, weather_agg, on=['DATE_TIME', 'PLANT_ID'], how='left')
    merged_df.ffill(inplace=True)
    merged_df.bfill(inplace=True)
    merged_df.fillna(0, inplace=True)

    # --- Smart Columns: Time-based features ---
    merged_df['hour'] = merged_df['DATE_TIME'].dt.hour
    merged_df['day_of_week'] = merged_df['DATE_TIME'].dt.dayofweek
    merged_df['day_of_year'] = merged_df['DATE_TIME'].dt.dayofyear
    merged_df['month'] = merged_df['DATE_TIME'].dt.month
    merged_df['hour_sin'] = np.sin(2 * np.pi * merged_df['hour'] / 24)
    merged_df['hour_cos'] = np.cos(2 * np.pi * merged_df['hour'] / 24)

    # --- Smart Columns: Lagged & Rolling Features ---
    merged_df = merged_df.sort_values(by=['PLANT_ID', 'SOURCE_KEY', 'DATE_TIME'])
    merged_df['DC_POWER_LAG1'] = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['DC_POWER'].shift(1)
    merged_df['AC_POWER_LAG1'] = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['AC_POWER'].shift(1)
    merged_df['DC_POWER_PREV_DAY'] = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['DC_POWER'].shift(96)
    
    merged_df['ROLLING_AVG_DC_POWER_3HR'] = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['DC_POWER'].transform(lambda x: x.rolling(window=12, min_periods=1).mean())

    # --- Smart Columns: Weather Lags (Predicting the Weather) ---
    merged_df['IRRADIATION_LAG1'] = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['IRRADIATION'].shift(1)
    merged_df['AMBIENT_TEMP_LAG1'] = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['AMBIENT_TEMPERATURE'].shift(1)
    merged_df['IRRADIATION_TREND'] = merged_df['IRRADIATION'] - merged_df['IRRADIATION_LAG1']

    # --- Smart Columns: Efficiency & Interaction ---
    # Note: IRRADIATION and MODULE_TEMPERATURE are plant-wide reference values from a single sensor.
    merged_df['IRRADIATION_TEMP_INTERACTION'] = merged_df['IRRADIATION'] * merged_df['MODULE_TEMPERATURE']
    merged_df['TEMP_DELTA_AMBIENT_MODULE'] = merged_df['MODULE_TEMPERATURE'] - merged_df['AMBIENT_TEMPERATURE']
    
    # Efficiency is calculated relative to the plant's reference weather sensor
    merged_df['DC_EFFICIENCY'] = (merged_df['DC_POWER'] / merged_df['IRRADIATION']).replace([np.inf, -np.inf], 0).fillna(0)
    merged_df['AC_EFFICIENCY'] = (merged_df['AC_POWER'] / merged_df['IRRADIATION']).replace([np.inf, -np.inf], 0).fillna(0)
    merged_df['INVERTER_EFFICIENCY'] = (merged_df['AC_POWER'] / merged_df['DC_POWER']).replace([np.inf, -np.inf], 0).fillna(0)

    # --- Smart Columns: Relative Performance ---
    avg_dc_at_timestamp = merged_df.groupby('DATE_TIME')['DC_POWER'].transform('mean')
    avg_ac_at_timestamp = merged_df.groupby('DATE_TIME')['AC_POWER'].transform('mean')
    merged_df['RELATIVE_DC_PERFORMANCE'] = (merged_df['DC_POWER'] / avg_dc_at_timestamp).replace([np.inf, -np.inf], 1).fillna(1)
    merged_df['RELATIVE_AC_PERFORMANCE'] = (merged_df['AC_POWER'] / avg_ac_at_timestamp).replace([np.inf, -np.inf], 1).fillna(1)

    # --- Smart Columns: Cleaning, Soiling & Maintenance Signals ---
    # Detect sudden performance jumps relative to yesterday's efficiency at same time
    eff_prev_day = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['DC_EFFICIENCY'].shift(96)
    merged_df['EFFICIENCY_SURGE'] = (merged_df['DC_EFFICIENCY'] / eff_prev_day).replace([np.inf, -np.inf], 1).fillna(1)
    
    # Cleaning Probability: Sudden efficiency jump in high sun
    merged_df['CLEANING_PROBABILITY'] = np.where((merged_df['EFFICIENCY_SURGE'] > 1.2) & (merged_df['IRRADIATION'] > 0.1), 1, 0)
    
    # Maintenance Probability: Low AC Efficiency + Low Inverter Efficiency but normal DC Efficiency
    # Indicates something is wrong with the conversion/grid path, not the panels
    merged_df['MAINTENANCE_PROBABILITY'] = np.where((merged_df['INVERTER_EFFICIENCY'] < 0.8) & (merged_df['DC_EFFICIENCY'] > 0.5) & (merged_df['IRRADIATION'] > 0.1), 1, 0)
    
    # Soiling Rate Proxy: Cumulative potential for dust based on high temp and lack of irradiation trends
    # (Simplified as a localized potential score)
    merged_df['SOILING_POTENTIAL'] = np.where((merged_df['MODULE_TEMPERATURE'] > 50) & (merged_df['IRRADIATION_TREND'] < 0), 1, 0)
    merged_df['CUMULATIVE_SOILING_RISK'] = merged_df.groupby(['PLANT_ID', 'SOURCE_KEY'])['SOILING_POTENTIAL'].transform(lambda x: x.rolling(window=96, min_periods=1).sum())

    # --- Daily Aggregates ---
    merged_df['DATE'] = merged_df['DATE_TIME'].dt.date
    daily_summary = merged_df.groupby(['DATE', 'PLANT_ID']).agg(
        DAILY_MAX_IRRADIATION=('IRRADIATION', 'max'),
        DAILY_AVG_IRRADIATION=('IRRADIATION', 'mean'),
        DAILY_MAX_TEMP_AMBIENT=('AMBIENT_TEMPERATURE', 'max'),
        DAILY_AVG_TEMP_AMBIENT=('AMBIENT_TEMPERATURE', 'mean')
    ).reset_index()
    merged_df = pd.merge(merged_df, daily_summary, on=['DATE', 'PLANT_ID'], how='left')
    merged_df.drop(columns=['DATE'], inplace=True)
    merged_df.fillna(0, inplace=True)

    return merged_df

# Process Plants
p1_gen_augmented_df = load_augment_merge_generation_data(p1_gen_path, p1_weather_path, 4135001, dayfirst_gen=True)
p1_gen_augmented_df.to_csv(os.path.join(base_data_path, 'Plant_1_Generation_Data_augmented.csv'), index=False)

p2_gen_augmented_df = load_augment_merge_generation_data(p2_gen_path, p2_weather_path, 4136001, dayfirst_gen=False)
p2_gen_augmented_df.to_csv(os.path.join(base_data_path, 'Plant_2_Generation_Data_augmented.csv'), index=False)

# --- Function to Augment Weather Files ---
def augment_weather_data_only(weather_file, plant_id_val):
    weather_df = pd.read_csv(weather_file)
    weather_df['DATE_TIME'] = pd.to_datetime(weather_df['DATE_TIME'])
    weather_df['PLANT_ID'] = plant_id_val

    # Time features
    weather_df['hour'] = weather_df['DATE_TIME'].dt.hour
    weather_df['hour_sin'] = np.sin(2 * np.pi * weather_df['hour'] / 24)
    weather_df['hour_cos'] = np.cos(2 * np.pi * weather_df['hour'] / 24)

    # Weather prediction features (lags)
    weather_df['IRRADIATION_LAG1'] = weather_df['IRRADIATION'].shift(1)
    weather_df['AMBIENT_TEMP_LAG1'] = weather_df['AMBIENT_TEMPERATURE'].shift(1)
    weather_df['IRRADIATION_TREND'] = weather_df['IRRADIATION'] - weather_df['IRRADIATION_LAG1']

    weather_df['TEMP_DELTA_AMBIENT_MODULE'] = weather_df['MODULE_TEMPERATURE'] - weather_df['AMBIENT_TEMPERATURE']

    # Daily summary
    weather_df['DATE'] = weather_df['DATE_TIME'].dt.date
    daily_summary = weather_df.groupby(['DATE', 'PLANT_ID']).agg(
        DAILY_MAX_IRRADIATION=('IRRADIATION', 'max'),
        DAILY_AVG_IRRADIATION=('IRRADIATION', 'mean'),
        DAILY_MAX_TEMP_AMBIENT=('AMBIENT_TEMPERATURE', 'max'),
        DAILY_AVG_TEMP_AMBIENT=('AMBIENT_TEMPERATURE', 'mean')
    ).reset_index()
    weather_df = pd.merge(weather_df, daily_summary, on=['DATE', 'PLANT_ID'], how='left')
    weather_df.drop(columns=['DATE'], inplace=True)
    weather_df.fillna(0, inplace=True)

    return weather_df

p1_weather_augmented_df = augment_weather_data_only(p1_weather_path, 4135001)
p1_weather_augmented_df.to_csv(os.path.join(base_data_path, 'Plant_1_Weather_Sensor_Data_augmented.csv'), index=False)

p2_weather_augmented_df = augment_weather_data_only(p2_weather_path, 4136001)
p2_weather_augmented_df.to_csv(os.path.join(base_data_path, 'Plant_2_Weather_Sensor_Data_augmented.csv'), index=False)

print("\nAll augmented files (with weather prediction and cleaning signals) have been updated.")