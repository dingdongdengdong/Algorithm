#!/usr/bin/env python3
"""
롤링 최적화 시스템
시간 윈도우를 이동하며 지속적으로 GA 최적화 수행
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import copy

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.ga_optimizer import OceanShippingGA
from models.parameters import GAParameters
from .time_window_manager import TimeWindowManager


class RollingOptimizer:
    """롤링 최적화 시스템"""
    
    def __init__(self, ga_parameters: GAParameters, 
                 window_size_days: int = 30,
                 overlap_days: int = 7,
                 ga_generations: int = 50):
        """
        Parameters:
        -----------
        ga_parameters : GAParameters
            원본 GA 파라미터
        window_size_days : int
            윈도우 크기 (일)
        overlap_days : int
            윈도우 겹침 (일)
        ga_generations : int
            각 윈도우별 GA 실행 세대 수
        """
        self.original_params = ga_parameters
        self.ga_generations = ga_generations
        
        # 시간 윈도우 관리자 생성
        self.window_manager = TimeWindowManager(
            ga_parameters, window_size_days, overlap_days
        )
        
        # 최적화 결과 저장
        self.window_results = {}
        self.global_solution = None
        self.optimization_history = []
        
        # 연속성 관리
        self.solution_continuity = {}
        self.performance_tracking = []
        
    def optimize_single_window(self, window_id: int, 
                             warm_start_solution: Optional[Dict] = None) -> Dict:
        """단일 윈도우 최적화"""
        print(f"🎯 Optimizing window {window_id}...")
        
        # 윈도우 파라미터 생성
        window_params = self.window_manager.get_window_parameters(window_id)
        
        if window_params is None:
            print(f"⚠️ Window {window_id} has no schedules")
            return {"status": "skipped", "reason": "no_schedules"}
        
        try:
            # GA 최적화기 생성
            ga = OceanShippingGA(
                file_paths=None,  # 데이터 로더에서 직접 사용
                version='quick'
            )
            
            # 윈도우별 파라미터 적용
            ga.params = window_params
            ga.params.max_generations = self.ga_generations
            ga.params.population_size = min(50, ga.params.population_size)  # 윈도우는 작은 인구 사용
            
            # 웜 스타트 적용
            initial_population = None
            if warm_start_solution:
                initial_population = self._create_warm_start_population(
                    warm_start_solution, window_params
                )
            
            # 최적화 실행
            start_time = datetime.now()
            best_solution, fitness_history = ga.run(initial_population=initial_population)
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            # 결과 저장
            window_result = {
                'window_id': window_id,
                'best_solution': best_solution,
                'fitness_history': fitness_history,
                'optimization_time': optimization_time,
                'schedules_count': len(window_params.I),
                'final_fitness': best_solution['fitness'],
                'generations_run': len(fitness_history),
                'status': 'success'
            }
            
            self.window_results[window_id] = window_result
            
            print(f"✅ Window {window_id} optimization completed:")
            print(f"   - Final fitness: {best_solution['fitness']:.2f}")
            print(f"   - Generations: {len(fitness_history)}")
            print(f"   - Time: {optimization_time:.1f}s")
            
            return window_result
            
        except Exception as e:
            print(f"❌ Window {window_id} optimization failed: {e}")
            return {
                'window_id': window_id,
                'status': 'failed',
                'error': str(e),
                'schedules_count': len(window_params.I) if window_params else 0
            }
    
    def _create_warm_start_population(self, previous_solution: Dict, 
                                    window_params: GAParameters) -> List[Dict]:
        """이전 해를 이용한 웜 스타트 인구 생성"""
        population = []
        population_size = min(20, window_params.population_size)
        
        # 이전 윈도우의 해에서 현재 윈도우 스케줄에 해당하는 부분 추출
        base_individual = {
            'xF': np.zeros(len(window_params.I)),
            'xE': np.zeros(len(window_params.I)),
            'y': np.zeros((len(window_params.I), len(window_params.P)))
        }
        
        # 겹치는 스케줄의 해를 복사
        for i, schedule_id in enumerate(window_params.I):
            # 이전 해에서 해당 스케줄의 인덱스 찾기
            if schedule_id in self.original_params.time_index_mapping:
                orig_idx = self.original_params.time_index_mapping[schedule_id]
                if orig_idx < len(previous_solution['xF']):
                    base_individual['xF'][i] = previous_solution['xF'][orig_idx]
                    base_individual['xE'][i] = previous_solution['xE'][orig_idx]
        
        # 기본 개체를 포함하여 인구 생성
        population.append(copy.deepcopy(base_individual))
        
        # 나머지는 변형된 개체들
        for _ in range(population_size - 1):
            variant = copy.deepcopy(base_individual)
            
            # 약간의 변형 추가
            noise_factor = 0.1
            variant['xF'] += np.random.normal(0, noise_factor * variant['xF'])
            variant['xE'] += np.random.normal(0, noise_factor * variant['xE'])
            
            # 음수 방지
            variant['xF'] = np.maximum(0, variant['xF'])
            variant['xE'] = np.maximum(0, variant['xE'])
            
            population.append(variant)
        
        print(f"🔥 Created warm-start population with {len(population)} individuals")
        return population
    
    def run_rolling_optimization(self, enable_warm_start: bool = True) -> Dict:
        """전체 롤링 최적화 실행"""
        print(f"🔄 Starting rolling optimization with {self.window_manager.get_window_stats()['total_windows']} windows")
        
        total_start_time = datetime.now()
        successful_windows = 0
        failed_windows = 0
        
        previous_solution = None
        
        # 각 윈도우 순차 최적화
        for window_id in range(len(self.window_manager.time_windows)):
            warm_start = previous_solution if enable_warm_start else None
            
            window_result = self.optimize_single_window(window_id, warm_start)
            
            if window_result['status'] == 'success':
                successful_windows += 1
                previous_solution = window_result['best_solution']
                
                # 성능 추적
                self.performance_tracking.append({
                    'window_id': window_id,
                    'fitness': window_result['final_fitness'],
                    'optimization_time': window_result['optimization_time'],
                    'schedules_count': window_result['schedules_count']
                })
                
            else:
                failed_windows += 1
                print(f"⚠️ Window {window_id} failed, continuing with next window")
        
        total_optimization_time = (datetime.now() - total_start_time).total_seconds()
        
        # 전역 해 구성
        self._construct_global_solution()
        
        # 결과 요약
        rolling_summary = {
            'status': 'completed',
            'total_windows': len(self.window_manager.time_windows),
            'successful_windows': successful_windows,
            'failed_windows': failed_windows,
            'total_optimization_time': total_optimization_time,
            'global_solution': self.global_solution,
            'performance_tracking': self.performance_tracking,
            'average_fitness': np.mean([p['fitness'] for p in self.performance_tracking]) if self.performance_tracking else 0,
            'total_schedules_optimized': sum(p['schedules_count'] for p in self.performance_tracking)
        }
        
        print(f"\\n✅ Rolling optimization completed:")
        print(f"   - Successful windows: {successful_windows}/{len(self.window_manager.time_windows)}")
        print(f"   - Total time: {total_optimization_time:.1f}s")
        print(f"   - Average fitness: {rolling_summary['average_fitness']:.2f}")
        
        return rolling_summary
    
    def _construct_global_solution(self):
        """윈도우별 결과를 통합하여 전역 해 구성"""
        print("🔗 Constructing global solution from window results...")
        
        if not self.window_results:
            print("❌ No window results to construct global solution")
            return
        
        # 전역 해 초기화
        global_solution = {
            'xF': np.zeros(len(self.original_params.I)),
            'xE': np.zeros(len(self.original_params.I)),
            'y': np.zeros((len(self.original_params.I), len(self.original_params.P))),
            'fitness': 0,
            'construction_method': 'rolling_integration'
        }
        
        # 각 스케줄에 대해 최적의 윈도우 결과 사용
        schedule_assignments = {}
        
        for window_id, result in self.window_results.items():
            if result['status'] != 'success':
                continue
                
            window_schedules = self.window_manager.window_schedules[window_id]
            window_params = self.window_manager.get_window_parameters(window_id)
            
            if window_params is None:
                continue
            
            # 윈도우 내 각 스케줄의 해를 전역 해에 매핑
            for local_idx, schedule_id in enumerate(window_schedules):
                global_idx = self.original_params.time_index_mapping.get(schedule_id)
                
                if global_idx is not None:
                    # 여러 윈도우에서 겹치는 경우 가장 좋은 fitness를 가진 윈도우 우선
                    if schedule_id not in schedule_assignments or result['final_fitness'] > schedule_assignments[schedule_id]['fitness']:
                        schedule_assignments[schedule_id] = {
                            'window_id': window_id,
                            'fitness': result['final_fitness'],
                            'local_idx': local_idx,
                            'global_idx': global_idx
                        }
                        
                        # 해 복사
                        global_solution['xF'][global_idx] = result['best_solution']['xF'][local_idx]
                        global_solution['xE'][global_idx] = result['best_solution']['xE'][local_idx]
        
        # 전역 재고 계산
        global_solution['y'] = self.original_params.calculate_empty_container_levels(global_solution)
        
        # 전역 fitness 재계산 (필요시)
        # 여기서는 윈도우별 fitness의 가중 평균 사용
        total_schedules = sum(len(self.window_manager.window_schedules[wid]) for wid in self.window_results if self.window_results[wid]['status'] == 'success')
        weighted_fitness = 0
        
        for window_id, result in self.window_results.items():
            if result['status'] == 'success':
                weight = len(self.window_manager.window_schedules[window_id]) / total_schedules
                weighted_fitness += result['final_fitness'] * weight
        
        global_solution['fitness'] = weighted_fitness
        
        self.global_solution = global_solution
        
        assigned_schedules = len(schedule_assignments)
        total_schedules = len(self.original_params.I)
        
        print(f"✅ Global solution constructed:")
        print(f"   - Assigned schedules: {assigned_schedules}/{total_schedules}")
        print(f"   - Global fitness: {global_solution['fitness']:.2f}")
    
    def analyze_window_performance(self) -> Dict:
        """윈도우별 성능 분석"""
        if not self.performance_tracking:
            return {"status": "no_data"}
        
        performance_df = pd.DataFrame(self.performance_tracking)
        
        analysis = {
            'total_windows_analyzed': len(performance_df),
            'fitness_stats': {
                'mean': performance_df['fitness'].mean(),
                'std': performance_df['fitness'].std(),
                'min': performance_df['fitness'].min(),
                'max': performance_df['fitness'].max()
            },
            'time_stats': {
                'mean_seconds': performance_df['optimization_time'].mean(),
                'total_seconds': performance_df['optimization_time'].sum(),
                'max_seconds': performance_df['optimization_time'].max()
            },
            'schedule_stats': {
                'mean_schedules': performance_df['schedules_count'].mean(),
                'total_schedules': performance_df['schedules_count'].sum(),
                'max_schedules': performance_df['schedules_count'].max()
            },
            'efficiency_metrics': {
                'fitness_per_second': performance_df['fitness'].sum() / performance_df['optimization_time'].sum(),
                'schedules_per_second': performance_df['schedules_count'].sum() / performance_df['optimization_time'].sum()
            }
        }
        
        # 윈도우별 상대 성능
        if len(performance_df) > 1:
            analysis['relative_performance'] = []
            for _, row in performance_df.iterrows():
                relative_fitness = row['fitness'] / analysis['fitness_stats']['mean']
                relative_time = row['optimization_time'] / analysis['time_stats']['mean_seconds']
                
                analysis['relative_performance'].append({
                    'window_id': row['window_id'],
                    'relative_fitness': relative_fitness,
                    'relative_time': relative_time,
                    'efficiency_score': relative_fitness / relative_time
                })
        
        return analysis
    
    def generate_rolling_report(self, rolling_summary: Dict, 
                              performance_analysis: Dict) -> str:
        """롤링 최적화 결과 리포트 생성"""
        report = []
        report.append("🔄 Rolling Optimization Report")
        report.append("=" * 60)
        
        # 전체 요약
        report.append("📊 Overall Summary:")
        report.append(f"   - Total windows: {rolling_summary['total_windows']}")
        report.append(f"   - Successful: {rolling_summary['successful_windows']}")
        report.append(f"   - Failed: {rolling_summary['failed_windows']}")
        report.append(f"   - Success rate: {rolling_summary['successful_windows']/rolling_summary['total_windows']*100:.1f}%")
        report.append(f"   - Total optimization time: {rolling_summary['total_optimization_time']:.1f}s")
        report.append("")
        
        # 성능 통계
        if performance_analysis.get('fitness_stats'):
            fs = performance_analysis['fitness_stats']
            ts = performance_analysis['time_stats']
            
            report.append("📈 Performance Statistics:")
            report.append(f"   - Average fitness: {fs['mean']:.2f} (±{fs['std']:.2f})")
            report.append(f"   - Fitness range: {fs['min']:.2f} - {fs['max']:.2f}")
            report.append(f"   - Average time per window: {ts['mean_seconds']:.1f}s")
            report.append(f"   - Total schedules optimized: {rolling_summary['total_schedules_optimized']}")
            report.append("")
        
        # 효율성 지표
        if performance_analysis.get('efficiency_metrics'):
            em = performance_analysis['efficiency_metrics']
            report.append("⚡ Efficiency Metrics:")
            report.append(f"   - Fitness per second: {em['fitness_per_second']:.3f}")
            report.append(f"   - Schedules per second: {em['schedules_per_second']:.1f}")
            report.append("")
        
        # 윈도우 설정
        window_stats = self.window_manager.get_window_stats()
        report.append("🪟 Window Configuration:")
        report.append(f"   - Window size: {window_stats['window_size_days']} days")
        report.append(f"   - Overlap: {window_stats['overlap_days']} days")
        report.append(f"   - Avg schedules per window: {window_stats['avg_schedules_per_window']:.1f}")
        
        return "\\n".join(report)