#!/usr/bin/env python3
"""
Ocean Shipping GA Optimization Runner
Usage: python run.py [version] [show_plot]
"""

import sys
import os
from typing import Dict

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.ga_optimizer import OceanShippingGA


def run_ocean_shipping_ga(file_paths: Dict[str, str], version: str = 'quick', show_plot: bool = True):
    """
    Run the Ocean Shipping GA optimization
    
    Args:
        file_paths: Dictionary of data file paths
        version: Execution version ('quick', 'medium', 'standard', 'full')
        show_plot: Whether to show visualization
    
    Returns:
        Tuple of (best_solution, fitness_history)
    """
    # Create GA instance
    ga = OceanShippingGA(file_paths, version)
    
    # Run optimization
    best_solution, fitness_history = ga.run()
    
    # Print results
    ga.print_solution(best_solution)
    
    # Show visualization if requested
    if show_plot:
        ga.visualize_results(best_solution, fitness_history)
    
    return best_solution, fitness_history


def main():
    # Parse command line arguments
    version = sys.argv[1] if len(sys.argv) > 1 else 'quick'
    show_plot = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True
    
    print(f"Running Ocean Shipping GA with version: {version}, show_plot: {show_plot}")
    
    # Auto-detect data files
    file_paths = {
        'schedule': 'data/스해물_스케줄data.xlsx',
        'delayed': 'data/스해물_딜레이스케줄data.xlsx', 
        'vessel': 'data/스해물_선박data.xlsx',
        'port': 'data/스해물_항구위치data.xlsx',
        'fixed': 'data/스해물_고정값data.xlsx'
    }
    
    # Run optimization
    best_solution, fitness_history = run_ocean_shipping_ga(
        file_paths=file_paths,
        version=version,
        show_plot=show_plot
    )
    
    print(f"\nOptimization complete!")
    print(f"Best fitness: {best_solution['fitness']}")


if __name__ == "__main__":
    main()