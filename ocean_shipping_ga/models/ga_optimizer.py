"""
GA 최적화 메인 클래스
"""

import numpy as np
import copy
import pandas as pd
from datetime import datetime
from typing import List, Tuple, Dict, Any

from data.data_loader import DataLoader
from .parameters import GAParameters
from .individual import Individual
from algorithms.fitness import FitnessCalculator
from algorithms.genetic_operators import GeneticOperators
from algorithms.population import PopulationManager
from visualization.plotter import ResultPlotter


class OceanShippingGA:
    """
    해상 운송 최적화를 위한 유전 알고리즘 클래스
    """
    
    def __init__(self, file_paths: Dict[str, str], version: str = 'default'):
        """
        Parameters:
        -----------
        file_paths : dict
            필요한 엑셀 파일 경로를 담은 딕셔너리
        version : str
            실행 버전
        """
        # 데이터 로드
        self.data_loader = DataLoader(file_paths)
        self.data_loader.load_all_data()
        
        # 파라미터 초기화
        self.params = GAParameters(self.data_loader, version)
        self.version = version
        
        # 알고리즘 컴포넌트 초기화
        self.fitness_calculator = FitnessCalculator(self.params)
        self.genetic_operators = GeneticOperators(self.params)
        self.population_manager = PopulationManager(self.params)
        self.plotter = ResultPlotter(self.params)
        
        # 실행 시간 추적
        self.start_time = None
        self.execution_time = 0.0
        
    def run(self) -> Tuple[Dict[str, Any], List[float]]:
        """GA 실행"""
        print("\n🧬 유전 알고리즘 시작 (성능 최적화)")
        print("=" * 60)
        print(f"🏷️ 실행 버전: {self.params.version_description}")
        print(f"📊 설정: Population={self.params.population_size}, Generations={self.params.max_generations}")
        print(f"🎯 목표: 적합도 >= {self.params.target_fitness}")
        print(f"⏰ 수렴 대기: {self.params.convergence_patience}세대")
        print("=" * 60)
        
        # 초기화
        self.start_time = datetime.now()
        population = self.population_manager.initialize_population()
        best_fitness_history = []
        best_individual = None
        stagnation_counter = 0
        
        # 진화 과정
        for generation in range(self.params.max_generations):
            # 선택
            parents, best = self.genetic_operators.selection(population)
            
            # 최고 개체 업데이트 및 수렴 체크
            improvement = False
            if best_individual is None or best['fitness'] > best_individual['fitness']:
                if best_individual is not None:
                    improvement_rate = (best['fitness'] - best_individual['fitness']) / abs(best_individual['fitness'])
                    if improvement_rate > self.params.convergence_threshold:
                        improvement = True
                        stagnation_counter = 0
                    else:
                        stagnation_counter += 1
                else:
                    improvement = True
                    stagnation_counter = 0
                best_individual = copy.deepcopy(best)
                self.params.best_ever_fitness = best['fitness']
            else:
                stagnation_counter += 1
            
            best_fitness_history.append(best['fitness'])
            
            # 다양성 계산
            diversity = self.population_manager.calculate_population_diversity(population[:50])
            self.params.diversity_history.append(diversity)
            
            # 적응적 돌연변이율 적용
            current_mutation_rate = self.genetic_operators.adaptive_mutation_rate(generation, diversity)
            self.params.p_mutation = current_mutation_rate
            
            # 세대 통계 저장
            generation_stat = {
                'generation': generation,
                'best_fitness': best['fitness'],
                'diversity': diversity,
                'mutation_rate': current_mutation_rate,
                'improvement': improvement
            }
            self.params.generation_stats.append(generation_stat)
            
            # 진행 상황 출력
            if generation % 20 == 0 or improvement:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                print(f"세대 {generation:4d}: 적합도={best['fitness']:8.2f} | "
                      f"다양성={diversity:6.2f} | 변이율={current_mutation_rate:.3f} | "
                      f"정체={stagnation_counter:3d} | {elapsed:.1f}s")
                
                # 상세 비용 정보 출력
                if generation % 100 == 0:
                    total_cost = self.fitness_calculator.calculate_total_cost(best)
                    penalty = self.fitness_calculator.calculate_penalties(best)
                    print(f"  ├─ 총 비용: ${total_cost:,.0f}")
                    print(f"  ├─ 패널티: {penalty:.0f}")
                    print(f"  └─ Full/Empty: {np.sum(best['xF']):.0f}/{np.sum(best['xE']):.0f} TEU")
            
            # 목표 달성 확인
            if best['fitness'] >= self.params.target_fitness:
                print(f"\n✅ 목표 적합도 달성! (세대 {generation})")
                break
            
            # 조기 종료 확인 (수렴 감지)
            if stagnation_counter >= self.params.convergence_patience:
                print(f"\n⏹️ 수렴 감지로 조기 종료 (세대 {generation})")
                print(f"   {self.params.convergence_patience}세대 동안 {self.params.convergence_threshold*100:.2f}% 이상 개선 없음")
                break
            
            # 재생산
            population = self.genetic_operators.reproduction(parents)
        
        # 최종 결과
        self.execution_time = (datetime.now() - self.start_time).total_seconds()
        print("\n" + "=" * 60)
        print("🎯 최적화 완료!")
        print(f"⏱️ 총 실행 시간: {self.execution_time:.2f}초")
        print(f"🏆 최종 적합도: {best_individual['fitness']:.2f}")
        print(f"📈 총 진화 세대: {generation + 1}")
        print("=" * 60)
        
        return best_individual, best_fitness_history
    
    def print_solution(self, best_individual: Dict[str, Any]):
        """최적해 출력"""
        self.plotter.print_solution_summary(best_individual)
        
    def visualize_results(self, best_individual: Dict[str, Any], fitness_history: List[float]):
        """결과 시각화"""
        return self.plotter.visualize_results(best_individual, fitness_history)
    
    def save_markdown_report(self, best_individual: Dict[str, Any], fitness_history: List[float], 
                           output_dir: str = "results") -> str:
        """마크다운 상세 보고서 저장"""
        return self.plotter.save_markdown_report(
            best_individual, fitness_history, self.version, self.execution_time, output_dir
        )