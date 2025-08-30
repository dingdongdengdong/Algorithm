"""
Runner utility for GA optimization
"""

import sys
import os
from models.ga_optimizer import OceanShippingGA


def run_ocean_shipping_ga(file_paths: Dict[str, str], version: str = 'default', show_plot: bool = True) -> Tuple[Dict[str, Any], List[float]]:
    """
    해상 운송 GA 최적화 실행
    
    Parameters:
    -----------
    file_paths : dict
        데이터 파일 경로 딕셔너리
    version : str
        실행 버전 ('quick', 'medium', 'standard', 'full', 'default')
    show_plot : bool
        시각화 표시 여부
    
    Returns:
    --------
    best_solution : dict
        최적 솔루션
    fitness_history : list
        적합도 변화 이력
    """
    # GA 인스턴스 생성 (버전 포함)
    ga = OceanShippingGA(file_paths, version)
    
    # 최적화 실행
    best_solution, fitness_history = ga.run()
    
    # 결과 출력
    ga.print_solution(best_solution)
    
    # 시각화 (옵션)
    if show_plot:
        ga.visualize_results(best_solution, fitness_history)
    
    return best_solution, fitness_history