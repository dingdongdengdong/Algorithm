#!/usr/bin/env python3
"""
동적 업데이터
실시간 데이터 변화에 따른 파라미터 동적 조정
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.parameters import GAParameters
from .rolling_optimizer import RollingOptimizer


class DynamicUpdater:
    """실시간 파라미터 동적 업데이트"""
    
    def __init__(self, rolling_optimizer: RollingOptimizer, 
                 update_threshold: float = 0.1,
                 monitoring_interval: int = 3600):  # 1시간
        """
        Parameters:
        -----------
        rolling_optimizer : RollingOptimizer
            롤링 최적화기 인스턴스
        update_threshold : float
            업데이트 트리거 임계값
        monitoring_interval : int
            모니터링 간격 (초)
        """
        self.rolling_optimizer = rolling_optimizer
        self.update_threshold = update_threshold
        self.monitoring_interval = monitoring_interval
        
        # 상태 추적
        self.baseline_parameters = self._capture_baseline()
        self.update_history = []
        self.last_update_time = datetime.now()
        self.performance_baseline = None
        
        # 동적 조정 규칙
        self.adjustment_rules = self._initialize_adjustment_rules()
        
    def _capture_baseline(self) -> Dict:
        """현재 파라미터 상태를 기준선으로 저장"""
        params = self.rolling_optimizer.original_params
        
        baseline = {
            'timestamp': datetime.now(),
            'demand_values': params.D_ab.copy(),
            'capacity_values': params.CAP_v_r.copy(),
            'cost_parameters': {
                'CSHIP': params.CSHIP,
                'CBAF': params.CBAF,
                'CETA': params.CETA
            },
            'ga_parameters': {
                'population_size': params.population_size,
                'max_generations': params.max_generations,
                'p_mutation': params.p_mutation,
                'p_crossover': params.p_crossover
            }
        }
        
        print("📊 Baseline parameters captured")
        return baseline
    
    def _initialize_adjustment_rules(self) -> Dict:
        """동적 조정 규칙 초기화"""
        return {
            'demand_spike': {
                'condition': lambda data: data['demand_change'] > 0.3,
                'action': 'increase_capacity_buffer',
                'parameters': {'buffer_factor': 1.2}
            },
            'demand_drop': {
                'condition': lambda data: data['demand_change'] < -0.3,
                'action': 'reduce_capacity_allocation',
                'parameters': {'reduction_factor': 0.9}
            },
            'performance_degradation': {
                'condition': lambda data: data['fitness_change'] < -0.2,
                'action': 'increase_ga_exploration',
                'parameters': {'mutation_increase': 0.1, 'population_increase': 1.5}
            },
            'schedule_disruption': {
                'condition': lambda data: data['schedule_disruption'] > 0.1,
                'action': 'enable_reactive_mode',
                'parameters': {'reactive_weight': 0.8}
            }
        }
    
    def monitor_external_changes(self, external_data: Dict) -> Dict:
        """외부 데이터 변화 모니터링"""
        print("🔍 Monitoring external data changes...")
        
        change_metrics = {
            'timestamp': datetime.now(),
            'demand_change': 0,
            'capacity_change': 0,
            'schedule_disruption': 0,
            'fitness_change': 0,
            'significant_changes': []
        }
        
        # 수요 변화 감지
        if 'demand_data' in external_data:
            current_demand = external_data['demand_data']
            baseline_demand = self.baseline_parameters['demand_values']
            
            demand_changes = []
            for route in baseline_demand:
                if route in current_demand:
                    baseline_val = baseline_demand[route]
                    current_val = current_demand[route]
                    if baseline_val > 0:
                        change_ratio = (current_val - baseline_val) / baseline_val
                        demand_changes.append(change_ratio)
            
            if demand_changes:
                change_metrics['demand_change'] = np.mean(demand_changes)
                if abs(change_metrics['demand_change']) > self.update_threshold:
                    change_metrics['significant_changes'].append('demand_change')
        
        # 스케줄 중단 감지
        if 'schedule_disruptions' in external_data:
            disruptions = external_data['schedule_disruptions']
            total_schedules = len(self.rolling_optimizer.original_params.I)
            change_metrics['schedule_disruption'] = len(disruptions) / total_schedules
            
            if change_metrics['schedule_disruption'] > self.update_threshold:
                change_metrics['significant_changes'].append('schedule_disruption')
        
        # 성능 변화 감지 (최근 윈도우 결과와 비교)
        if self.performance_baseline and self.rolling_optimizer.performance_tracking:
            recent_performance = self.rolling_optimizer.performance_tracking[-1]['fitness']
            baseline_performance = self.performance_baseline
            
            change_metrics['fitness_change'] = (recent_performance - baseline_performance) / baseline_performance
            if abs(change_metrics['fitness_change']) > self.update_threshold:
                change_metrics['significant_changes'].append('performance_change')
        
        print(f"✅ Change monitoring completed: {len(change_metrics['significant_changes'])} significant changes detected")
        return change_metrics
    
    def apply_dynamic_adjustments(self, change_metrics: Dict) -> Dict:
        """변화 감지에 따른 동적 조정 적용"""
        print("⚙️ Applying dynamic adjustments...")
        
        applied_adjustments = {
            'timestamp': datetime.now(),
            'adjustments_applied': [],
            'parameters_changed': {},
            'status': 'success'
        }
        
        try:
            # 각 규칙에 대해 조건 검사 및 적용
            for rule_name, rule in self.adjustment_rules.items():
                if rule['condition'](change_metrics):
                    print(f"🔧 Applying adjustment rule: {rule_name}")
                    
                    adjustment_result = self._apply_adjustment_action(
                        rule['action'], 
                        rule['parameters'], 
                        change_metrics
                    )
                    
                    applied_adjustments['adjustments_applied'].append({
                        'rule_name': rule_name,
                        'action': rule['action'],
                        'result': adjustment_result
                    })
                    
                    applied_adjustments['parameters_changed'].update(adjustment_result.get('changed_params', {}))
            
            # 조정 이력 저장
            self.update_history.append(applied_adjustments)
            self.last_update_time = datetime.now()
            
            print(f"✅ Dynamic adjustments completed: {len(applied_adjustments['adjustments_applied'])} rules applied")
            
        except Exception as e:
            applied_adjustments['status'] = 'failed'
            applied_adjustments['error'] = str(e)
            print(f"❌ Dynamic adjustment failed: {e}")
        
        return applied_adjustments
    
    def _apply_adjustment_action(self, action: str, parameters: Dict, change_metrics: Dict) -> Dict:
        """특정 조정 액션 실행"""
        params = self.rolling_optimizer.original_params
        result = {'changed_params': {}, 'status': 'success'}
        
        try:
            if action == 'increase_capacity_buffer':
                buffer_factor = parameters.get('buffer_factor', 1.2)
                for route in params.CAP_v_r:
                    old_capacity = params.CAP_v_r[route]
                    new_capacity = int(old_capacity * buffer_factor)
                    params.CAP_v_r[route] = new_capacity
                    result['changed_params'][f'capacity_{route}'] = {
                        'old': old_capacity, 'new': new_capacity
                    }
            
            elif action == 'reduce_capacity_allocation':
                reduction_factor = parameters.get('reduction_factor', 0.9)
                for route in params.CAP_v_r:
                    old_capacity = params.CAP_v_r[route]
                    new_capacity = int(old_capacity * reduction_factor)
                    params.CAP_v_r[route] = max(1000, new_capacity)  # 최소값 보장
                    result['changed_params'][f'capacity_{route}'] = {
                        'old': old_capacity, 'new': new_capacity
                    }
            
            elif action == 'increase_ga_exploration':
                mutation_increase = parameters.get('mutation_increase', 0.1)
                population_increase = parameters.get('population_increase', 1.5)
                
                old_mutation = params.p_mutation
                old_population = params.population_size
                
                params.p_mutation = min(0.8, params.p_mutation + mutation_increase)
                params.population_size = int(params.population_size * population_increase)
                
                result['changed_params']['p_mutation'] = {
                    'old': old_mutation, 'new': params.p_mutation
                }
                result['changed_params']['population_size'] = {
                    'old': old_population, 'new': params.population_size
                }
            
            elif action == 'enable_reactive_mode':
                # 반응형 모드: 더 짧은 윈도우, 더 자주 업데이트
                reactive_weight = parameters.get('reactive_weight', 0.8)
                
                # 윈도우 크기 감소
                old_window_size = self.rolling_optimizer.window_manager.window_size_days
                new_window_size = max(7, int(old_window_size * reactive_weight))
                
                result['changed_params']['window_size'] = {
                    'old': old_window_size, 'new': new_window_size
                }
                
                # 새로운 윈도우 매니저로 재구성 필요
                self.rolling_optimizer.window_manager = self.rolling_optimizer.window_manager.__class__(
                    params, new_window_size, 
                    self.rolling_optimizer.window_manager.overlap_days
                )
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
        
        return result
    
    def revert_to_baseline(self) -> Dict:
        """기준선 파라미터로 되돌리기"""
        print("🔄 Reverting to baseline parameters...")
        
        try:
            baseline = self.baseline_parameters
            params = self.rolling_optimizer.original_params
            
            # 수요 파라미터 복원
            params.D_ab = baseline['demand_values'].copy()
            
            # 용량 파라미터 복원
            params.CAP_v_r = baseline['capacity_values'].copy()
            
            # 비용 파라미터 복원
            cost_params = baseline['cost_parameters']
            params.CSHIP = cost_params['CSHIP']
            params.CBAF = cost_params['CBAF']
            params.CETA = cost_params['CETA']
            
            # GA 파라미터 복원
            ga_params = baseline['ga_parameters']
            params.population_size = ga_params['population_size']
            params.max_generations = ga_params['max_generations']
            params.p_mutation = ga_params['p_mutation']
            params.p_crossover = ga_params['p_crossover']
            
            print("✅ Successfully reverted to baseline parameters")
            
            return {
                'status': 'success',
                'reverted_timestamp': datetime.now(),
                'baseline_timestamp': baseline['timestamp']
            }
            
        except Exception as e:
            print(f"❌ Failed to revert to baseline: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def set_performance_baseline(self):
        """현재 성능을 기준선으로 설정"""
        if self.rolling_optimizer.performance_tracking:
            recent_performance = [p['fitness'] for p in self.rolling_optimizer.performance_tracking[-3:]]
            self.performance_baseline = np.mean(recent_performance)
            print(f"📊 Performance baseline set: {self.performance_baseline:.2f}")
    
    def get_adaptation_status(self) -> Dict:
        """적응 상태 정보 반환"""
        status = {
            'baseline_timestamp': self.baseline_parameters['timestamp'],
            'last_update_time': self.last_update_time,
            'total_updates': len(self.update_history),
            'update_threshold': self.update_threshold,
            'monitoring_interval': self.monitoring_interval,
            'performance_baseline': self.performance_baseline,
            'recent_adjustments': self.update_history[-3:] if len(self.update_history) >= 3 else self.update_history
        }
        
        # 활성 규칙 상태
        status['active_rules'] = list(self.adjustment_rules.keys())
        
        return status
    
    def save_adaptation_state(self, filepath: str):
        """적응 상태를 파일로 저장"""
        state = {
            'baseline_parameters': self.baseline_parameters,
            'update_history': self.update_history,
            'performance_baseline': self.performance_baseline,
            'adaptation_config': {
                'update_threshold': self.update_threshold,
                'monitoring_interval': self.monitoring_interval
            }
        }
        
        # datetime 객체를 문자열로 변환
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError
        
        try:
            with open(filepath, 'w') as f:
                json.dump(state, f, default=convert_datetime, indent=2)
            print(f"💾 Adaptation state saved to {filepath}")
        except Exception as e:
            print(f"❌ Failed to save adaptation state: {e}")
    
    def load_adaptation_state(self, filepath: str):
        """파일에서 적응 상태 로드"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            # datetime 문자열을 객체로 변환
            def convert_datetime_strings(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key.endswith('_timestamp') or key.endswith('_time'):
                            if isinstance(value, str):
                                obj[key] = datetime.fromisoformat(value)
                        else:
                            convert_datetime_strings(value)
                elif isinstance(obj, list):
                    for item in obj:
                        convert_datetime_strings(item)
            
            convert_datetime_strings(state)
            
            self.baseline_parameters = state['baseline_parameters']
            self.update_history = state['update_history']
            self.performance_baseline = state['performance_baseline']
            
            config = state['adaptation_config']
            self.update_threshold = config['update_threshold']
            self.monitoring_interval = config['monitoring_interval']
            
            print(f"📂 Adaptation state loaded from {filepath}")
            
        except Exception as e:
            print(f"❌ Failed to load adaptation state: {e}")