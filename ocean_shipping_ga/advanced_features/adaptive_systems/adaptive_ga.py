#!/usr/bin/env python3
"""
적응형 GA 시스템
실시간으로 환경에 적응하며 최적화 성능을 개선하는 GA
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta
import threading
import time
import copy

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.ga_optimizer import OceanShippingGA
from models.parameters import GAParameters
from .real_time_monitor import RealTimeMonitor
from .learning_system import LearningSystem
from ..rolling_optimization import RollingOptimizer, DynamicUpdater


class AdaptiveGA:
    """실시간 적응형 GA 시스템"""
    
    def __init__(self, ga_parameters: GAParameters,
                 adaptation_interval: float = 300.0,  # 5분
                 learning_enabled: bool = True):
        """
        Parameters:
        -----------
        ga_parameters : GAParameters
            GA 파라미터
        adaptation_interval : float
            적응 주기 (초)
        learning_enabled : bool
            학습 기능 활성화 여부
        """
        self.ga_params = ga_parameters
        self.adaptation_interval = adaptation_interval
        self.learning_enabled = learning_enabled
        
        # 구성 요소들
        self.monitor = RealTimeMonitor(ga_parameters, monitoring_interval=30.0)
        self.learning_system = LearningSystem() if learning_enabled else None
        self.rolling_optimizer = RollingOptimizer(ga_parameters, ga_generations=30)
        self.dynamic_updater = DynamicUpdater(self.rolling_optimizer)
        
        # 적응 상태
        self.is_adaptive = False
        self.adaptation_thread = None
        self.adaptation_history = []
        self.performance_trends = []
        
        # 적응 전략
        self.adaptation_strategies = self._initialize_adaptation_strategies()
        self.current_strategy = 'balanced'
        
        # 최적화 결과 캐시
        self.optimization_cache = {}
        self.cache_size_limit = 100
        
        # 콜백 등록
        self._register_callbacks()
        
    def _initialize_adaptation_strategies(self) -> Dict:
        """적응 전략 초기화"""
        return {
            'aggressive': {
                'description': '공격적 적응 - 빠른 변화 대응',
                'mutation_factor': 1.5,
                'population_factor': 1.3,
                'adaptation_threshold': 0.1,
                'convergence_patience': 15
            },
            'balanced': {
                'description': '균형 적응 - 안정성과 적응성 균형',
                'mutation_factor': 1.0,
                'population_factor': 1.0,
                'adaptation_threshold': 0.2,
                'convergence_patience': 25
            },
            'conservative': {
                'description': '보수적 적응 - 안정성 우선',
                'mutation_factor': 0.8,
                'population_factor': 0.9,
                'adaptation_threshold': 0.3,
                'convergence_patience': 35
            },
            'reactive': {
                'description': '반응형 적응 - 즉각적 환경 대응',
                'mutation_factor': 2.0,
                'population_factor': 1.5,
                'adaptation_threshold': 0.05,
                'convergence_patience': 10
            }
        }
    
    def _register_callbacks(self):
        """모니터링 콜백 등록"""
        # 알림 콜백
        self.monitor.register_alert_callback(self._handle_monitoring_alert)
        
        # 메트릭 콜백
        self.monitor.register_metric_callback(self._handle_monitoring_metrics)
        
    def start_adaptive_mode(self):
        """적응형 모드 시작"""
        if self.is_adaptive:
            print("⚠️ Adaptive mode is already running")
            return
        
        print("🚀 Starting adaptive GA system...")
        
        # 모니터링 시작
        self.monitor.start_monitoring()
        
        # 성능 기준선 설정
        baseline_result = self._establish_performance_baseline()
        if baseline_result:
            self.monitor.set_performance_baseline(baseline_result['fitness'])
        
        # 적응 루프 시작
        self.is_adaptive = True
        self.adaptation_thread = threading.Thread(target=self._adaptation_loop, daemon=True)
        self.adaptation_thread.start()
        
        print("✅ Adaptive GA system started")
        print(f"   - Monitoring interval: {self.monitor.monitoring_interval}s")
        print(f"   - Adaptation interval: {self.adaptation_interval}s")
        print(f"   - Learning enabled: {self.learning_enabled}")
        print(f"   - Current strategy: {self.current_strategy}")
    
    def stop_adaptive_mode(self):
        """적응형 모드 중지"""
        if not self.is_adaptive:
            print("⚠️ Adaptive mode is not running")
            return
        
        print("🛑 Stopping adaptive GA system...")
        
        # 적응 루프 중지
        self.is_adaptive = False
        
        if self.adaptation_thread and self.adaptation_thread.is_alive():
            self.adaptation_thread.join(timeout=10.0)
        
        # 모니터링 중지
        self.monitor.stop_monitoring()
        
        print("✅ Adaptive GA system stopped")
    
    def _establish_performance_baseline(self) -> Optional[Dict]:
        """성능 기준선 설정"""
        print("📊 Establishing performance baseline...")
        
        try:
            # 기본 최적화 실행
            baseline_ga = OceanShippingGA(file_paths=None, version='quick')
            baseline_ga.params = copy.deepcopy(self.ga_params)
            baseline_ga.params.max_generations = 30
            
            best_solution, fitness_history = baseline_ga.run()
            
            baseline_result = {
                'fitness': best_solution['fitness'],
                'generations': len(fitness_history),
                'timestamp': datetime.now(),
                'method': 'baseline_establishment'
            }
            
            print(f"✅ Performance baseline established: {best_solution['fitness']:.2f}")
            return baseline_result
            
        except Exception as e:
            print(f"❌ Failed to establish baseline: {e}")
            return None
    
    def _adaptation_loop(self):
        """메인 적응 루프"""
        print("🔄 Adaptation loop started")
        
        while self.is_adaptive:
            try:
                start_time = time.time()
                
                # 적응 결정 및 실행
                adaptation_decision = self._make_adaptation_decision()
                
                if adaptation_decision['should_adapt']:
                    adaptation_result = self._execute_adaptation(adaptation_decision)
                    self._record_adaptation(adaptation_result)
                
                # 학습 시스템 업데이트
                if self.learning_enabled and self.learning_system:
                    self._update_learning_system()
                
                # 대기 시간 계산 (처리 시간 고려)
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.adaptation_interval - elapsed_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"❌ Adaptation loop error: {e}")
                time.sleep(self.adaptation_interval)
        
        print("🔄 Adaptation loop ended")
    
    def _make_adaptation_decision(self) -> Dict:
        """적응 필요성 결정"""
        decision = {
            'should_adapt': False,
            'reasons': [],
            'adaptation_type': None,
            'priority': 'low',
            'confidence': 0.0
        }
        
        try:
            # 최근 모니터링 데이터 확인
            monitor_status = self.monitor.get_current_status()
            
            if monitor_status['status'] == 'no_data':
                return decision
            
            # 성능 추세 분석
            performance_trend = self._analyze_performance_trend()
            
            if performance_trend['declining']:
                decision['should_adapt'] = True
                decision['reasons'].append('performance_decline')
                decision['adaptation_type'] = 'performance_improvement'
                decision['priority'] = 'high'
                decision['confidence'] += 0.4
            
            # 시스템 건강도 확인
            system_health = monitor_status.get('system_health', 'unknown')
            
            if system_health in ['critical', 'warning']:
                decision['should_adapt'] = True
                decision['reasons'].append(f'system_health_{system_health}')
                decision['adaptation_type'] = 'system_optimization'
                decision['priority'] = 'high' if system_health == 'critical' else 'medium'
                decision['confidence'] += 0.3
            
            # 환경 변화 감지
            environment_change = self._detect_environment_change()
            
            if environment_change['significant']:
                decision['should_adapt'] = True
                decision['reasons'].append('environment_change')
                decision['adaptation_type'] = 'environment_adaptation'
                decision['priority'] = 'medium'
                decision['confidence'] += 0.2
            
            # 학습 시스템 권장사항
            if self.learning_enabled and self.learning_system:
                learning_recommendation = self.learning_system.get_adaptation_recommendation()
                if learning_recommendation['should_adapt']:
                    decision['should_adapt'] = True
                    decision['reasons'].append('learning_recommendation')
                    decision['confidence'] += 0.1
            
            # 최종 신뢰도 정규화
            decision['confidence'] = min(1.0, decision['confidence'])
            
        except Exception as e:
            print(f"⚠️ Adaptation decision error: {e}")
        
        return decision
    
    def _analyze_performance_trend(self) -> Dict:
        """성능 추세 분석"""
        if len(self.performance_trends) < 3:
            return {'declining': False, 'trend': 'insufficient_data'}
        
        recent_trends = self.performance_trends[-5:]  # 최근 5개
        fitness_values = [trend['fitness'] for trend in recent_trends]
        
        # 선형 회귀를 통한 추세 계산
        x = np.arange(len(fitness_values))
        coeffs = np.polyfit(x, fitness_values, 1)
        slope = coeffs[0]
        
        # 추세 평가
        trend_analysis = {
            'declining': slope < -50,  # 음의 기울기가 임계값보다 크면 하락
            'slope': slope,
            'recent_average': np.mean(fitness_values),
            'volatility': np.std(fitness_values),
            'trend': 'declining' if slope < -50 else ('improving' if slope > 50 else 'stable')
        }
        
        return trend_analysis
    
    def _detect_environment_change(self) -> Dict:
        """환경 변화 감지"""
        # 간단한 환경 변화 감지 (실제로는 더 복잡한 분석 필요)
        recent_alerts = [a for a in self.monitor.alerts_history if 
                        (datetime.now() - a['timestamp']).seconds < 1800]  # 최근 30분
        
        change_indicators = {
            'significant': len(recent_alerts) > 3,
            'alert_count': len(recent_alerts),
            'change_types': list(set(a['anomaly']['type'] for a in recent_alerts)),
            'severity_levels': list(set(a['anomaly']['severity'] for a in recent_alerts))
        }
        
        return change_indicators
    
    def _execute_adaptation(self, adaptation_decision: Dict) -> Dict:
        """적응 실행"""
        print(f"🔧 Executing adaptation: {adaptation_decision['adaptation_type']}")
        
        adaptation_result = {
            'timestamp': datetime.now(),
            'decision': adaptation_decision,
            'actions_taken': [],
            'success': False,
            'performance_before': None,
            'performance_after': None
        }
        
        try:
            # 현재 성능 측정
            current_performance = self._measure_current_performance()
            adaptation_result['performance_before'] = current_performance
            
            # 적응 유형별 실행
            if adaptation_decision['adaptation_type'] == 'performance_improvement':
                self._adapt_for_performance_improvement(adaptation_result)
            
            elif adaptation_decision['adaptation_type'] == 'system_optimization':
                self._adapt_for_system_optimization(adaptation_result)
            
            elif adaptation_decision['adaptation_type'] == 'environment_adaptation':
                self._adapt_for_environment_change(adaptation_result)
            
            # 적응 후 성능 측정
            time.sleep(5)  # 적응 효과가 나타날 시간 대기
            new_performance = self._measure_current_performance()
            adaptation_result['performance_after'] = new_performance
            
            # 성공 여부 판단
            if new_performance and current_performance:
                improvement = new_performance['fitness'] - current_performance['fitness']
                adaptation_result['success'] = improvement > 0
                adaptation_result['improvement'] = improvement
            
            print(f"✅ Adaptation executed: {len(adaptation_result['actions_taken'])} actions")
            
        except Exception as e:
            adaptation_result['error'] = str(e)
            print(f"❌ Adaptation execution failed: {e}")
        
        return adaptation_result
    
    def _adapt_for_performance_improvement(self, result: Dict):
        """성능 개선을 위한 적응"""
        strategy = self.adaptation_strategies[self.current_strategy]
        
        # GA 파라미터 조정
        original_mutation = self.ga_params.p_mutation
        original_population = self.ga_params.population_size
        
        self.ga_params.p_mutation *= strategy['mutation_factor']
        self.ga_params.population_size = int(self.ga_params.population_size * strategy['population_factor'])
        
        result['actions_taken'].append({
            'action': 'adjust_ga_parameters',
            'details': {
                'mutation_rate': f"{original_mutation:.3f} -> {self.ga_params.p_mutation:.3f}",
                'population_size': f"{original_population} -> {self.ga_params.population_size}"
            }
        })
        
        # 전략 변경 (성능이 계속 하락하면 더 공격적으로)
        if self.current_strategy == 'balanced':
            self.current_strategy = 'aggressive'
            result['actions_taken'].append({
                'action': 'change_strategy',
                'details': {'new_strategy': 'aggressive'}
            })
    
    def _adapt_for_system_optimization(self, result: Dict):
        """시스템 최적화를 위한 적응"""
        # 메모리 사용량 감소를 위한 조정
        if self.ga_params.population_size > 50:
            original_size = self.ga_params.population_size
            self.ga_params.population_size = max(30, int(self.ga_params.population_size * 0.8))
            
            result['actions_taken'].append({
                'action': 'reduce_population_size',
                'details': {
                    'reason': 'system_load_optimization',
                    'change': f"{original_size} -> {self.ga_params.population_size}"
                }
            })
        
        # 세대 수 조정
        if self.ga_params.max_generations > 50:
            original_gens = self.ga_params.max_generations
            self.ga_params.max_generations = max(30, int(self.ga_params.max_generations * 0.9))
            
            result['actions_taken'].append({
                'action': 'reduce_generations',
                'details': {
                    'reason': 'computational_efficiency',
                    'change': f"{original_gens} -> {self.ga_params.max_generations}"
                }
            })
    
    def _adapt_for_environment_change(self, result: Dict):
        """환경 변화에 대한 적응"""
        # 동적 업데이터를 통한 파라미터 조정
        mock_external_data = {
            'demand_data': {route: np.random.uniform(0.8, 1.2) * demand 
                           for route, demand in self.ga_params.D_ab.items()},
            'schedule_disruptions': []
        }
        
        change_metrics = self.dynamic_updater.monitor_external_changes(mock_external_data)
        adjustment_results = self.dynamic_updater.apply_dynamic_adjustments(change_metrics)
        
        result['actions_taken'].append({
            'action': 'dynamic_parameter_adjustment',
            'details': adjustment_results
        })
        
        # 적응 전략을 반응형으로 변경
        if self.current_strategy != 'reactive':
            self.current_strategy = 'reactive'
            result['actions_taken'].append({
                'action': 'change_strategy',
                'details': {'new_strategy': 'reactive', 'reason': 'environment_change'}
            })
    
    def _measure_current_performance(self) -> Optional[Dict]:
        """현재 성능 측정"""
        try:
            # 캐시된 결과가 있으면 사용
            cache_key = self._generate_cache_key()
            if cache_key in self.optimization_cache:
                cached_result = self.optimization_cache[cache_key]
                if (datetime.now() - cached_result['timestamp']).seconds < 300:  # 5분 이내
                    return cached_result
            
            # 빠른 최적화 실행
            quick_ga = OceanShippingGA(file_paths=None, version='quick')
            quick_ga.params = copy.deepcopy(self.ga_params)
            quick_ga.params.max_generations = 20  # 빠른 측정을 위해 세대 수 축소
            quick_ga.params.population_size = min(30, quick_ga.params.population_size)
            
            best_solution, fitness_history = quick_ga.run()
            
            performance = {
                'fitness': best_solution['fitness'],
                'generations': len(fitness_history),
                'convergence_speed': len(fitness_history),
                'timestamp': datetime.now()
            }
            
            # 캐시 저장
            self.optimization_cache[cache_key] = performance
            self._cleanup_cache()
            
            return performance
            
        except Exception as e:
            print(f"⚠️ Performance measurement failed: {e}")
            return None
    
    def _generate_cache_key(self) -> str:
        """캐시 키 생성"""
        # GA 파라미터의 주요 값들로 키 생성
        key_elements = [
            str(self.ga_params.population_size),
            str(self.ga_params.max_generations),
            f"{self.ga_params.p_mutation:.3f}",
            f"{self.ga_params.p_crossover:.3f}",
            str(len(self.ga_params.D_ab))
        ]
        return "_".join(key_elements)
    
    def _cleanup_cache(self):
        """캐시 정리"""
        if len(self.optimization_cache) > self.cache_size_limit:
            # 오래된 항목부터 제거
            sorted_items = sorted(
                self.optimization_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            
            # 절반 정도 제거
            items_to_remove = len(sorted_items) - self.cache_size_limit // 2
            for i in range(items_to_remove):
                del self.optimization_cache[sorted_items[i][0]]
    
    def _record_adaptation(self, adaptation_result: Dict):
        """적응 결과 기록"""
        self.adaptation_history.append(adaptation_result)
        
        # 성능 추세 업데이트
        if adaptation_result.get('performance_after'):
            self.performance_trends.append({
                'timestamp': datetime.now(),
                'fitness': adaptation_result['performance_after']['fitness'],
                'adaptation_type': adaptation_result['decision']['adaptation_type']
            })
        
        # 히스토리 크기 제한
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-100:]
        
        if len(self.performance_trends) > 50:
            self.performance_trends = self.performance_trends[-50:]
    
    def _update_learning_system(self):
        """학습 시스템 업데이트"""
        if not self.learning_system:
            return
        
        # 최근 적응 결과를 학습 데이터로 제공
        recent_adaptations = self.adaptation_history[-5:]
        
        for adaptation in recent_adaptations:
            if adaptation.get('success') and adaptation.get('performance_before') and adaptation.get('performance_after'):
                learning_data = {
                    'context': adaptation['decision'],
                    'actions': adaptation['actions_taken'],
                    'performance_improvement': adaptation.get('improvement', 0),
                    'success': adaptation['success']
                }
                
                self.learning_system.add_experience(learning_data)
    
    def _handle_monitoring_alert(self, anomalies: List[Dict], metrics: Dict):
        """모니터링 알림 처리"""
        high_severity_alerts = [a for a in anomalies if a['severity'] == 'high']
        
        if high_severity_alerts:
            print(f"🚨 High severity alerts detected: {len(high_severity_alerts)}")
            
            # 즉시 적응 트리거
            urgent_decision = {
                'should_adapt': True,
                'reasons': ['urgent_alert'],
                'adaptation_type': 'emergency_response',
                'priority': 'urgent',
                'confidence': 1.0
            }
            
            # 별도 스레드에서 즉시 실행
            threading.Thread(
                target=self._execute_adaptation,
                args=(urgent_decision,),
                daemon=True
            ).start()
    
    def _handle_monitoring_metrics(self, metrics: Dict):
        """모니터링 메트릭 처리"""
        # 메트릭 기반 상태 업데이트
        system_metrics = metrics.get('system_metrics', {})
        performance_metrics = metrics.get('performance_metrics', {})
        
        # CPU/메모리 사용량이 높으면 전략 조정
        cpu_usage = system_metrics.get('cpu_percent', 0) / 100
        memory_usage = system_metrics.get('memory_percent', 0) / 100
        
        if cpu_usage > 0.8 or memory_usage > 0.8:
            if self.current_strategy in ['aggressive', 'reactive']:
                self.current_strategy = 'conservative'
                print("🔄 Switched to conservative strategy due to high system load")
    
    def get_adaptation_status(self) -> Dict:
        """적응 상태 정보"""
        return {
            'is_adaptive': self.is_adaptive,
            'current_strategy': self.current_strategy,
            'adaptation_interval': self.adaptation_interval,
            'learning_enabled': self.learning_enabled,
            'total_adaptations': len(self.adaptation_history),
            'successful_adaptations': sum(1 for a in self.adaptation_history if a.get('success', False)),
            'monitor_status': self.monitor.get_current_status(),
            'recent_performance': self.performance_trends[-5:] if len(self.performance_trends) >= 5 else self.performance_trends,
            'cache_size': len(self.optimization_cache)
        }
    
    def change_adaptation_strategy(self, new_strategy: str):
        """적응 전략 변경"""
        if new_strategy in self.adaptation_strategies:
            old_strategy = self.current_strategy
            self.current_strategy = new_strategy
            print(f"🔄 Adaptation strategy changed: {old_strategy} -> {new_strategy}")
        else:
            available = list(self.adaptation_strategies.keys())
            print(f"❌ Invalid strategy. Available: {available}")
    
    def generate_adaptation_report(self) -> str:
        """적응 시스템 리포트 생성"""
        report = []
        report.append("🧠 Adaptive GA System Report")
        report.append("=" * 60)
        
        status = self.get_adaptation_status()
        
        # 전체 상태
        report.append("📊 System Status:")
        report.append(f"   - Adaptive mode: {'Active' if status['is_adaptive'] else 'Inactive'}")
        report.append(f"   - Current strategy: {status['current_strategy']}")
        report.append(f"   - Learning enabled: {status['learning_enabled']}")
        report.append(f"   - Adaptation interval: {status['adaptation_interval']}s")
        report.append("")
        
        # 적응 통계
        total_adaptations = status['total_adaptations']
        successful_adaptations = status['successful_adaptations']
        success_rate = (successful_adaptations / total_adaptations * 100) if total_adaptations > 0 else 0
        
        report.append("📈 Adaptation Statistics:")
        report.append(f"   - Total adaptations: {total_adaptations}")
        report.append(f"   - Successful adaptations: {successful_adaptations}")
        report.append(f"   - Success rate: {success_rate:.1f}%")
        report.append("")
        
        # 성능 추세
        if status['recent_performance']:
            recent_perf = status['recent_performance']
            fitness_values = [p['fitness'] for p in recent_perf]
            
            report.append("📊 Recent Performance Trend:")
            report.append(f"   - Average fitness: {np.mean(fitness_values):.2f}")
            report.append(f"   - Performance range: {min(fitness_values):.2f} - {max(fitness_values):.2f}")
            report.append(f"   - Trend: {'Improving' if len(fitness_values) > 1 and fitness_values[-1] > fitness_values[0] else 'Stable/Declining'}")
            report.append("")
        
        # 모니터링 상태
        monitor_status = status['monitor_status']
        report.append("🔍 Monitoring Status:")
        report.append(f"   - System health: {monitor_status.get('system_health', 'Unknown')}")
        report.append(f"   - Recent alerts: {monitor_status.get('recent_alerts_count', 0)}")
        report.append(f"   - Metrics collected: {monitor_status.get('total_metrics_collected', 0)}")
        
        return "\n".join(report)