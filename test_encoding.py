import pandas as pd
import os

# Test Korean file reading
base_path = '/Users/dong/Downloads/ocean'
file_paths = {
    'schedule': f'{base_path}/스해물_스케줄 data.xlsx',
    'delayed': f'{base_path}/스해물_딜레이 스케줄 data.xlsx',
    'vessel': f'{base_path}/스해물_선박 data.xlsx',
    'port': f'{base_path}/스해물_항구 위치 data.xlsx'
}

print("Testing file encoding...")

for name, path in file_paths.items():
    print(f"\n=== {name.upper()} FILE ===")
    try:
        df = pd.read_excel(path, engine='openpyxl')
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"First few rows:")
        print(df.head(2))
        
        # Check for encoding issues in data
        for col in df.columns:
            if df[col].dtype == 'object':
                sample_values = df[col].dropna().head(3).tolist()
                print(f"  {col}: {sample_values}")
                
    except Exception as e:
        print(f"Error reading {name}: {e}")