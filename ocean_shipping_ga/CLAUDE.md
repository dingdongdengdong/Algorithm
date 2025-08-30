# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ocean Shipping GA Optimization Package

This is a genetic algorithm optimization package for ocean shipping logistics. The system optimizes container allocation (Full and Empty containers) across shipping schedules while minimizing costs and respecting operational constraints.

## Running the System

### Basic Usage
```python
from ocean_shipping_ga import run_ocean_shipping_ga

# Run with auto-detected data files
best_solution, fitness_history = run_ocean_shipping_ga(
    file_paths=None,  # Auto-detect from data/ folder
    version='quick',  # or 'medium', 'standard', 'full'
    show_plot=True
)
```

### Execution Versions
- `quick`: 20 generations, population 50 - for testing
- `medium`: 50 generations, population 100 - for development  
- `standard`: 100 generations, population 200 - for production
- `full`: 200 generations, population 300 - for comprehensive optimization

## Architecture

### Core Components
- **`models/ga_optimizer.py`**: Main GA orchestrator class
- **`algorithms/`**: Core GA operations (fitness, selection, crossover, mutation)
- **`data/data_loader.py`**: Excel data loading and preprocessing
- **`visualization/plotter.py`**: Results visualization and reporting

### Data Structure
The GA operates on individuals representing complete shipping plans:
- `xF[i]`: Full container allocation for schedule i
- `xE[i]`: Empty container allocation for schedule i  
- `y[i,j]`: Inventory at port j after schedule i
- `fitness`: Combined cost and penalty score

### Required Data Files (in `data/` folder)
- `스해물_스케줄 data.xlsx`: Shipping schedules (routes, ships, ports)
- `스해물_딜레이 스케줄 data.xlsx`: Delayed schedule information
- `스해물_선박 data.xlsx`: Ship information (capacity, speed)
- `스해물_항구 위치 data.xlsx`: Port information (location, facilities)

## Fitness Calculation
The system minimizes total cost while penalizing constraint violations:
- **Total Cost**: Transportation + delay penalties + inventory holding costs
- **Penalties**: Capacity violations, demand mismatches, inventory constraints
- **Final Fitness**: -(Total Cost + Penalties) (higher is better)

## Key Features
- **Adaptive Mutation**: Mutation rate adjusts based on population diversity
- **Uniform Crossover**: Probabilistic gene exchange for complex solution spaces
- **Multi-strategy Mutation**: Fine-tuning + occasional reinitialization (5% chance)
- **Early Convergence Detection**: Stops when no significant improvement for 50 generations
- **Performance Optimization**: Uses vectorized operations for efficiency

## Dependencies
Based on imports found in the codebase:
- `numpy`: Numerical computations
- `pandas`: Data manipulation  
- `matplotlib`: Visualization
- Standard library: `copy`, `datetime`, `typing`

## Testing

### Advanced Features Test Suite
Run the comprehensive test suite for all advanced features:
```bash
./scripts/run_all_advanced_features.sh
```

This executes:
1. **Demand Forecasting** (LSTM-based): 30-day demand prediction
2. **Rolling Optimization**: Time-windowed GA with 30-day windows, 7-day overlap
3. **Adaptive GA**: Real-time parameter adaptation over 30 minutes

**Note**: Requires Korean Excel data files in `data/` folder. Without data, scripts will complete but show `'항구명'` KeyError (expected behavior).

### Manual Testing
For basic functionality without advanced features:
1. Running quick version to verify basic functionality
2. Checking fitness improvement over generations
3. Validating solution feasibility (no constraint violations)

## Development Notes
- Solutions must satisfy shipping capacity and inventory constraints
- The system handles Korean Excel file names in the data folder
- Progress is logged with generation statistics and timing information
- Results include detailed cost breakdowns and route utilization