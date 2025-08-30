#!/usr/bin/env python3
"""
Ocean Shipping GA Optimization Runner
Usage: python run.py [version] [show_plot] [save_report] [advanced_features]

Arguments:
    version: 'quick' (default), 'medium', 'standard', 'full'
    show_plot: 'true' (default), 'false' - whether to show visualization
    save_report: 'true' (default), 'false' - whether to save markdown report
    advanced_features: 'true' (default), 'false' - whether to run advanced features
"""

import sys
import os
from typing import Dict
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.ga_optimizer import OceanShippingGA
from models.dynamic_imbalance_detector import DynamicImbalanceDetector
from models.auto_redistribution_trigger import AutoRedistributionTrigger
from models.monitoring_dashboard import RealTimeMonitoringDashboard
from models.redistribution_optimizer import ContainerRedistributionOptimizer
from visualization.graph_visualizer import GraphVisualizer


def run_ocean_shipping_ga(file_paths: Dict[str, str], version: str = 'quick', 
                          show_plot: bool = True, save_report: bool = True, 
                          advanced_features: bool = True):
    """
    Run the Ocean Shipping GA optimization with advanced features
    
    Args:
        file_paths: Dictionary of data file paths
        version: Execution version ('quick', 'medium', 'standard', 'full')
        show_plot: Whether to show visualization
        save_report: Whether to save detailed markdown report
        advanced_features: Whether to run advanced imbalance detection and redistribution
    
    Returns:
        Tuple of (best_solution, fitness_history)
    """
    print("Ocean Shipping GA 최적화 시작")
    print("=" * 50)
    
    # Create GA instance
    ga = OceanShippingGA(file_paths, version)
    
    # Run optimization
    best_solution, fitness_history = ga.run()
    
    # Print results
    ga.print_solution(best_solution)
    
    # Advanced features
    if advanced_features:
        print("\n고급 기능 실행 중...")
        run_advanced_analysis(ga.params, best_solution, show_plot)
    
    # Save detailed markdown report
    if save_report:
        report_path = ga.save_markdown_report(best_solution, fitness_history)
        print(f"\n상세 분석 보고서 저장됨: {report_path}")
    
    # Show visualization if requested
    if show_plot and not advanced_features:  # advanced_features에서 이미 시각화
        ga.visualize_results(best_solution, fitness_history)
    
    return best_solution, fitness_history


def run_advanced_analysis(params, best_solution: Dict, show_plot: bool = True):
    """고급 분석 기능 실행"""
    print("=== 고급 분석 시작 ===")
    
    # 1. 동적 불균형 감지
    print("\n1. 불균형 감지 분석")
    imbalance_detector = DynamicImbalanceDetector(params)
    imbalance_report = imbalance_detector.detect_real_time_imbalance(best_solution)
    
    # 분석 결과 출력
    analysis = imbalance_report['imbalance_analysis']
    print(f"   불균형 지수: {analysis['imbalance_index']:.3f}")
    print(f"   과잉 항구: {len(analysis['excess_ports'])}개 - {analysis['excess_ports']}")
    print(f"   부족 항구: {len(analysis['shortage_ports'])}개 - {analysis['shortage_ports']}")
    print(f"   심각 부족: {len(analysis['critical_shortage_ports'])}개 - {analysis['critical_shortage_ports']}")
    print(f"   생성된 알림: {len(imbalance_report['alerts'])}건")
    
    # 2. 재배치 최적화
    print("\n2. 재배치 최적화")
    redistributor = ContainerRedistributionOptimizer(params)
    redistribution_plan = redistributor.generate_redistribution_plan(best_solution)
    
    paths = redistribution_plan.get('redistribution_paths', [])
    print(f"   재배치 경로: {len(paths)}개")
    if paths:
        total_containers = sum(getattr(path, 'container_count', 0) for path in paths)
        total_cost = sum(getattr(path, 'cost', 0) for path in paths)
        print(f"   총 재배치량: {total_containers:,} TEU")
        print(f"   총 비용: ${total_cost:,.0f}")
    
    # 3. 자동 트리거 시스템
    print("\n3. 자동 트리거 분석")
    auto_trigger = AutoRedistributionTrigger(params, imbalance_detector, redistributor)
    trigger_result = auto_trigger.check_and_execute_triggers(best_solution)
    
    print(f"   트리거된 조건: {len(trigger_result['triggered_conditions'])}개")
    print(f"   실행 가능한 트리거: {len(trigger_result['executable_triggers'])}개")
    
    # 4. 모니터링 대시보드
    print("\n4. 모니터링 대시보드")
    dashboard = RealTimeMonitoringDashboard(params, imbalance_detector, auto_trigger)
    snapshot = dashboard.update_dashboard_data(best_solution)
    
    metrics = snapshot['metrics']
    print(f"   효율성 점수: {metrics.efficiency_score:.1f}/100")
    print(f"   총 컨테이너: {metrics.total_containers:,} TEU")
    
    # 5. 시각화 생성
    if show_plot:
        print("\n5. 시각화 생성")
        visualizer = GraphVisualizer(params)
        
        # 출력 디렉토리 생성
        output_dir = Path("output/visualizations")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            saved_files = visualizer.save_all_visualizations(
                str(output_dir), imbalance_report, paths
            )
            print(f"   생성된 시각화 파일: {len(saved_files)}개")
            for file_path in saved_files:
                print(f"     - {Path(file_path).name}")
        except Exception as e:
            print(f"   시각화 생성 중 오류: {e}")
    
    print("\n고급 분석 완료")


def main():
    # Parse command line arguments
    version = sys.argv[1] if len(sys.argv) > 1 else 'quick'
    show_plot = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True
    save_report = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
    advanced_features = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
    
    print(f"Ocean Shipping GA 실행 설정:")
    print(f"  버전: {version}")
    print(f"  시각화: {show_plot}")
    print(f"  보고서 저장: {save_report}")
    print(f"  고급 기능: {advanced_features}")
    
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
        save_report=save_report,
        advanced_features=advanced_features
    )
    
    print(f"\n최적화 완료")
    print(f"최종 적합도: {best_solution['fitness']}")
    if save_report:
        print(f"상세 분석 보고서가 results/ 폴더에 저장되었습니다.")
    if advanced_features:
        print(f"고급 분석 결과 및 시각화 파일이 output/ 폴더에 저장되었습니다.")


if __name__ == "__main__":
    main()