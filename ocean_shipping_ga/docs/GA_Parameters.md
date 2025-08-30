# Genetic Algorithm Parameters Documentation

## Overview

This document provides a comprehensive overview of all parameters used in the Ocean Shipping GA optimization system. The parameters are organized by category and include their purpose, default values, and configuration options.

## Parameter Categories

### 1. GA Core Parameters (`GAParameters` class)

#### Population and Evolution Parameters

| Parameter | Type | Default | Description | Version Impact |
|-----------|------|---------|-------------|----------------|
| `population_size` | int | 100 | Size of the population in each generation | Varies by version |
| `max_generations` | int | 100 | Maximum number of generations to evolve | Varies by version |
| `num_elite` | int | 20 | Number of elite individuals preserved each generation | 20% of population |
| `p_crossover` | float | 0.85 | Probability of crossover between selected parents | Fixed across versions |
| `p_mutation` | float | 0.25 | Base mutation probability (adaptive during evolution) | Fixed across versions |

#### Version-Specific Configurations

| Version | Population | Generations | Elite | Patience | Description |
|---------|------------|-------------|-------|----------|-------------|
| `quick` | 50 | 20 | 10 | 10 | Fast testing (20 generations) |
| `medium` | 100 | 50 | 20 | 25 | Medium testing (50 generations) |
| `standard` | 200 | 100 | 40 | 50 | Standard execution (100 generations) |
| `full` | 1000 | 2000 | 200 | 200 | Comprehensive optimization (2000 generations) |
| `default` | 100 | 100 | 20 | 50 | Default configuration (100 generations) |

### 2. Convergence and Termination Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_fitness` | float | -3000 | Target fitness value for early termination |
| `convergence_threshold` | float | 0.0005 | Minimum improvement rate (0.05%) to avoid stagnation |
| `convergence_patience` | int | 50 | Number of generations to wait without improvement before stopping |
| `stagnation_counter` | int | 0 | Counter tracking generations without significant improvement |

### 3. Cost Parameters

#### Transportation Costs

| Parameter | Type | Default | Description | Source |
|-----------|------|---------|-------------|---------|
| `CSHIP` | float | 1000 | Base shipping cost per TEU | Fixed data files |
| `CBAF` | float | 100 | Bunker Adjustment Factor (fuel surcharge) per TEU | Fixed data files |
| `CETA` | float | 150 | ETA penalty cost per day of delay | Fixed data files |
| `CEMPTY_SHIP` | float | CSHIP + CBAF | Total cost for shipping empty containers | Calculated |

#### Physical Constants

| Parameter | Type | Value | Description |
|-----------|------|-------|-------------|
| `KG_PER_TEU` | int | 30000 | Conversion factor: kg per TEU |
| `theta` | float | 0.001 | Minimum empty container ratio threshold |

### 4. Data Structure Parameters

#### Sets and Collections

| Parameter | Type | Description | Source |
|-----------|------|-------------|---------|
| `P` | List[str] | Set of all ports | Port data Excel file |
| `R` | List[str] | Set of all routes | Schedule data Excel file |
| `V` | List[str] | Set of all vessels | Vessel data Excel file |
| `I` | List[str] | Set of all schedules (time-ordered) | Schedule data Excel file |

#### Dimensional Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `num_schedules` | int | Total number of shipping schedules |
| `num_ports` | int | Total number of ports in the network |

### 5. Temporal Parameters

#### Time Horizon

| Parameter | Type | Description |
|-----------|------|-------------|
| `time_horizon_start` | datetime | Earliest ETD in the schedule dataset |
| `time_horizon_end` | datetime | Latest ETA in the schedule dataset |
| `time_index_mapping` | Dict[str, int] | Maps schedule IDs to time-ordered indices |

#### Schedule Timing

| Parameter | Type | Description |
|-----------|------|-------------|
| `ETD_i` | Dict[str, datetime] | Estimated Time of Departure for each schedule |
| `ETA_i` | Dict[str, datetime] | Estimated Time of Arrival for each schedule |
| `RETA_i` | Dict[str, datetime] | Revised ETA (with delays) for each schedule |
| `DELAY_i` | Dict[str, int] | Delay in days for each schedule |

### 6. Route and Capacity Parameters

#### Route Mapping

| Parameter | Type | Description |
|-----------|------|-------------|
| `O_i` | Dict[str, str] | Origin port for each schedule |
| `D_i` | Dict[str, str] | Destination port for each schedule |
| `V_r` | Dict[str, str] | Vessel assigned to each route |
| `Q_r` | Dict[str, float] | Order quantity (in KG) for each route |
| `D_ab` | Dict[str, int] | Demand (in TEU) for each route |

#### Capacity Constraints

| Parameter | Type | Description |
|-----------|------|-------------|
| `CAP_v` | Dict[str, int] | Capacity (TEU) for each vessel |
| `CAP_v_r` | Dict[str, int] | Capacity for vessel on each route |

### 7. Inventory Parameters

#### Initial Inventory

| Parameter | Type | Description |
|-----------|------|-------------|
| `I0_p` | Dict[str, int] | Initial empty container inventory at each port |

#### Port-Specific Initial Inventory

| Port | Initial Inventory (TEU) |
|------|------------------------|
| BUSAN | 50,000 |
| LONG BEACH | 30,000 |
| NEW YORK | 100,000 |
| SAVANNAH | 20,000 |
| HOUSTON | 10,000 |
| MOBILE | 10,000 |
| SEATTLE | 10,000 |

### 8. Advanced Features Parameters

#### Adaptive Mutation

| Parameter | Type | Description |
|-----------|------|-------------|
| `use_adaptive_mutation` | bool | Enable adaptive mutation rate based on population diversity |

#### Performance Tracking

| Parameter | Type | Description |
|-----------|------|-------------|
| `best_ever_fitness` | float | Best fitness value achieved across all generations |
| `generation_stats` | List[Dict] | Statistics for each generation (fitness, diversity, etc.) |
| `diversity_history` | List[float] | Population diversity for each generation |

### 9. Temporal Analysis Parameters

#### Schedule Grouping

| Parameter | Type | Description |
|-----------|------|-------------|
| `daily_schedules` | Dict[date, List] | Schedules grouped by day |
| `weekly_schedules` | Dict[int, List] | Schedules grouped by ISO week |
| `monthly_schedules` | Dict[int, List] | Schedules grouped by month |

#### Vessel Timeline Analysis

| Parameter | Type | Description |
|-----------|------|-------------|
| `vessel_timeline` | Dict | Timeline analysis for each vessel including schedule gaps and reuse possibilities |

#### Port Capacity Analysis

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_timeline` | Dict | Timeline analysis for each port including departure/arrival schedules and capacity utilization |

## Decision Variables

The GA optimizes the following decision variables for each individual:

### Primary Variables

| Variable | Dimension | Type | Description |
|----------|-----------|------|-------------|
| `xF[i]` | [num_schedules] | float | Number of full containers assigned to schedule i |
| `xE[i]` | [num_schedules] | float | Number of empty containers assigned to schedule i |
| `y[i,j]` | [num_schedules, num_ports] | float | Empty container inventory at port j after schedule i |

### Fitness Components

| Component | Description | Weight |
|-----------|-------------|---------|
| Transportation Cost | CSHIP * (sum of xF + xE) | Primary objective |
| Fuel Surcharge | CBAF * (sum of xF + xE) | Cost component |
| Delay Penalty | CETA * (sum of delays) | Penalty component |
| Capacity Violation | Penalty for exceeding vessel capacity | High penalty |
| Inventory Violation | Penalty for negative inventory | High penalty |
| Demand Violation | Penalty for unmet demand | High penalty |

## Configuration Guidelines

### Choosing Execution Version

- **Quick**: For rapid prototyping and initial testing
- **Medium**: For development and parameter tuning
- **Standard**: For production optimization with moderate computation time
- **Full**: For comprehensive optimization when computation time is not a constraint

### Parameter Tuning Recommendations

1. **Population Size**: Larger populations provide better solution diversity but require more computation
2. **Crossover Rate**: 0.85 is optimal for this problem domain
3. **Mutation Rate**: Adaptive mutation (starting at 0.25) works better than fixed rates
4. **Convergence Patience**: Should be proportional to max_generations (typically 50% of max_generations)

## Data Dependencies

The parameters are initialized from the following Excel files:

1. **스해물_스케줄 data.xlsx**: Shipping schedules and routes
2. **스해물_딜레이 스케줄 data.xlsx**: Delayed schedule information  
3. **스해물_선박 data.xlsx**: Vessel capacities and specifications
4. **스해물_항구 위치 data.xlsx**: Port information and locations
5. **Fixed parameters file**: Cost parameters and constants

## Data Quality and Missing Value Handling

### NaN and Missing Data Value Strategies

The system implements robust handling for missing or invalid data values commonly found in Excel data files:

#### 1. Detection Methods

| Data Type | Detection Method | Default Handling |
|-----------|------------------|------------------|
| `NaN` values | `pandas.isna()` | Replace with defaults or interpolate |
| Empty strings | `value == ""` | Replace with appropriate defaults |
| Invalid dates | `pd.to_datetime()` errors | Skip record or use fallback dates |
| Negative capacities | `value < 0` | Use absolute value or default capacity |
| Missing port names | Korean text issues | Use port code as fallback |

#### 2. Data-Specific Handling Strategies

##### Schedule Data (`스해물_스케줄 data.xlsx`)
- **Missing ETD/ETA**: Use previous schedule + estimated transit time
- **Invalid route codes**: Skip schedule or use default route mapping  
- **Missing vessel assignment**: Assign to available vessel with matching capacity
- **NaN order quantities**: Use route-based historical averages

```python
# Example handling in data_loader.py
schedule_data['ETD'] = pd.to_datetime(schedule_data['ETD'], errors='coerce')
schedule_data['ETA'] = pd.to_datetime(schedule_data['ETA'], errors='coerce')

# Fill missing dates with forward fill + transit time
missing_etd = schedule_data['ETD'].isna()
schedule_data.loc[missing_etd, 'ETD'] = (
    schedule_data['ETD'].fillna(method='ffill') + pd.Timedelta(days=7)
)
```

##### Vessel Data (`스해물_선박 data.xlsx`)
- **Missing capacity**: Use fleet average or standard container vessel capacity (8000 TEU)
- **Invalid vessel codes**: Generate synthetic vessel ID
- **NaN speed values**: Use standard container vessel speed (20 knots)

##### Port Data (`스해물_항구 위치 data.xlsx`)
- **Missing coordinates**: Use approximate regional coordinates
- **Invalid port codes**: Standardize to UNLOCODE format
- **Missing facility data**: Assign default port capabilities

##### Delay Data (`스해물_딜레이 스케줄 data.xlsx`)
- **Missing delay values**: Assume zero delay (on-time arrival)
- **Invalid delay periods**: Cap at maximum reasonable delay (30 days)
- **Inconsistent schedule matching**: Use fuzzy matching on route + date

#### 3. Default Value Assignments

| Parameter | Missing Value Default | Rationale |
|-----------|----------------------|-----------|
| Vessel capacity | 8,000 TEU | Standard large container vessel |
| Port initial inventory | 10,000 TEU | Conservative minimum inventory |
| Transit time | 7 days | Average short-haul shipping time |
| Vessel speed | 20 knots | Standard container vessel speed |
| Delay penalty | 0 days | Assume on-time if no delay data |
| Order quantity | 0 KG | No cargo if quantity unknown |

#### 4. Data Validation Rules

##### Pre-Processing Validation
```python
def validate_schedule_data(df):
    """Validate and clean schedule data"""
    # Remove records with critical missing data
    critical_columns = ['스케줄ID', '항구명', 'ETD']
    df = df.dropna(subset=critical_columns)
    
    # Validate date formats
    df['ETD'] = pd.to_datetime(df['ETD'], errors='coerce')
    df['ETA'] = pd.to_datetime(df['ETA'], errors='coerce')
    
    # Remove invalid date ranges
    invalid_dates = df['ETD'] > df['ETA']
    df = df[~invalid_dates]
    
    return df
```

##### Runtime Validation
- **Capacity constraints**: Ensure `xF[i] + xE[i] ≤ CAP_v[vessel]`
- **Inventory bounds**: Verify `y[i,j] ≥ 0` for all ports and schedules
- **Demand satisfaction**: Check `sum(xF[routes_to_j]) ≥ D[j]` for each destination

#### 5. Error Recovery Mechanisms

##### Graceful Degradation
1. **Data file missing**: Use synthetic data generator with reasonable defaults
2. **Partial data corruption**: Continue with available schedules, log warnings
3. **Format inconsistencies**: Apply automatic format detection and conversion

##### Logging and Monitoring
```python
import logging

def log_data_quality_issues(df, data_type):
    """Log data quality statistics"""
    total_records = len(df)
    missing_counts = df.isna().sum()
    
    for column, missing_count in missing_counts.items():
        if missing_count > 0:
            percentage = (missing_count / total_records) * 100
            logging.warning(f"{data_type}: {percentage:.1f}% missing values in {column}")
```

#### 6. Best Practices for Data Quality

##### Input Data Guidelines
- Use consistent date formats (ISO 8601: YYYY-MM-DD)
- Standardize port codes to UN/LOCODE format
- Validate vessel identifiers against fleet registry
- Include data quality timestamps in Excel files

##### Monitoring Recommendations
- Track missing data percentages per data load
- Monitor fitness degradation due to synthetic data usage
- Validate solution feasibility when using default values
- Generate data quality reports before optimization runs

## Performance Considerations

### Memory Usage
- Each individual requires approximately `(2 * num_schedules + num_schedules * num_ports) * 8` bytes
- Population memory usage scales linearly with population size

### Computation Complexity
- Fitness evaluation: O(num_schedules * num_ports)
- Population evolution: O(population_size * num_schedules * num_ports)
- Overall complexity per generation: O(population_size * num_schedules * num_ports)

## Example Configuration

```python
# Example parameter setup for medium-sized problem
params = GAParameters(data_loader, version='standard')

print(f"Population Size: {params.population_size}")
print(f"Max Generations: {params.max_generations}") 
print(f"Number of Schedules: {params.num_schedules}")
print(f"Number of Ports: {params.num_ports}")
print(f"Shipping Cost: ${params.CSHIP}/TEU")
print(f"Target Fitness: {params.target_fitness}")
```

This configuration provides a balanced approach suitable for most ocean shipping optimization scenarios.