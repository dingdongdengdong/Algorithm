#!/usr/bin/env python3
"""
Ocean Shipping GA Optimization Runner
Usage: python run.py [version] [show_plot] [save_report]

Arguments:
    version: 'quick' (default), 'medium', 'standard', 'full'
    show_plot: 'true' (default), 'false' - whether to show visualization
    save_report: 'true' (default), 'false' - whether to save markdown report
"""

import sys
import os
from typing import Dict

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.ga_optimizer import OceanShippingGA


def run_ocean_shipping_ga(file_paths: Dict[str, str], version: str = 'quick', show_plot: bool = True, save_report: bool = True):
    """
    Run the Ocean Shipping GA optimization
    
    Args:
        file_paths: Dictionary of data file paths
        version: Execution version ('quick', 'medium', 'standard', 'full')
        show_plot: Whether to show visualization
        save_report: Whether to save detailed markdown report
    
    Returns:
        Tuple of (best_solution, fitness_history)
    """
    # Create GA instance
    ga = OceanShippingGA(file_paths, version)
    
    # Run optimization
    best_solution, fitness_history = ga.run()
    
    # Print results
    ga.print_solution(best_solution)
    
    # Save detailed markdown report
    if save_report:
        report_path = ga.save_markdown_report(best_solution, fitness_history)
        print(f"\n📄 상세 분석 보고서 저장됨: {report_path}")
    
    # Show visualization if requested
    if show_plot:
        ga.visualize_results(best_solution, fitness_history)
    
    return best_solution, fitness_history


def main():
    # Parse command line arguments
    version = sys.argv[1] if len(sys.argv) > 1 else 'quick'
    show_plot = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True
    save_report = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
    
    print(f"Running Ocean Shipping GA with version: {version}, show_plot: {show_plot}, save_report: {save_report}")
    
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
        show_plot=show_plot,
        save_report=save_report
    )
    
    print(f"\n✅ 최적화 완료!")
    print(f"🏆 최종 적합도: {best_solution['fitness']}")
    if save_report:
        print(f"📊 상세 분석 보고서가 results/ 폴더에 저장되었습니다.")


if __name__ == "__main__":
    main()