# Data Folder

This folder contains the Excel data files used by the Ocean Shipping GA optimization package.

## Data Files

- `스해물_스케줄 data.xlsx` - 운송 스케줄 정보 (출발지, 도착지, 루트, 선박 등)
- `스해물_딜레이 스케줄 data.xlsx` - 지연된 스케줄 정보 (실제 도착 시간)
- `스해물_선박 data.xlsx` - 선박 정보 (용량, 속도 등)  
- `스해물_항구 위치 data.xlsx` - 항구 정보 (위치, 시설 등)

## Usage

The DataLoader class can automatically find these files when no file paths are provided:

```python
from ocean_shipping_ga import run_ocean_shipping_ga

# Automatically uses data files from this folder
best_solution, fitness_history = run_ocean_shipping_ga(
    file_paths=None,  # Auto-detect data files
    version='quick'
)
```

## File Structure Expected

The DataLoader expects the following file names exactly:
- 스해물_스케줄 data.xlsx
- 스해물_딜레이 스케줄 data.xlsx  
- 스해물_선박 data.xlsx
- 스해물_항구 위치 data.xlsx