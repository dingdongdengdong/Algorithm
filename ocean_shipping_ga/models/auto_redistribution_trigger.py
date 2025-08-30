"""
자동 재배치 트리거 메커니즘
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .dynamic_imbalance_detector import DynamicImbalanceDetector, ImbalanceAlert
from .redistribution_optimizer import ContainerRedistributionOptimizer
from config import get_constant


class TriggerCondition(Enum):
    """트리거 조건 타입"""
    CRITICAL_SHORTAGE = "critical_shortage"
    MULTI_PORT_SHORTAGE = "multi_port_shortage"
    SEVERE_IMBALANCE = "severe_imbalance"
    PREDICTED_RISK = "predicted_risk"
    SCHEDULED = "scheduled"


@dataclass
class AutoTriggerRule:
    """자동 트리거 규칙"""
    condition: TriggerCondition
    threshold: float
    priority: int  # 1-5 (5가 최고 우선순위)
    cooldown_hours: int  # 재실행 대기 시간
    max_daily_triggers: int  # 일일 최대 트리거 횟수
    description: str


@dataclass
class TriggerEvent:
    """트리거 이벤트 기록"""
    timestamp: datetime
    condition: TriggerCondition
    triggered_ports: List[str]
    severity: int
    action_taken: str
    success: bool
    execution_time: float


class AutoRedistributionTrigger:
    """
    자동 재배치 트리거 시스템
    실시간 불균형 감지에 기반하여 자동으로 재배치 최적화를 실행
    """
    
    def __init__(self, params, imbalance_detector: DynamicImbalanceDetector, 
                 redistribution_optimizer: ContainerRedistributionOptimizer):
        self.params = params
        self.imbalance_detector = imbalance_detector
        self.redistribution_optimizer = redistribution_optimizer
        
        # 트리거 규칙 설정
        self.trigger_rules = self._initialize_trigger_rules()
        
        # 실행 히스토리
        self.trigger_history = []
        self.last_execution = {}  # 조건별 마지막 실행 시간
        self.daily_trigger_count = {}  # 일일 트리거 카운트
        
        # 설정값 (설정 파일에서 로드)
        self.auto_execution_enabled = True
        self.min_trigger_interval = get_constant('monitoring.min_trigger_interval', 1800)  # 30분 최소 간격 (초)
        self.max_concurrent_triggers = 3
        
        # 상태 추적
        self.active_triggers = []
        self.pending_actions = []
        
    def _initialize_trigger_rules(self) -> List[AutoTriggerRule]:
        """트리거 규칙 초기화"""
        return [
            AutoTriggerRule(
                condition=TriggerCondition.CRITICAL_SHORTAGE,
                threshold=get_constant('auto_redistribution.trigger_rules.critical_shortage.threshold', 0.15),  # 임계값 이하 15%
                priority=get_constant('auto_redistribution.trigger_rules.critical_shortage.priority', 5),
                cooldown_hours=get_constant('auto_redistribution.trigger_rules.critical_shortage.cooldown_hours', 2),
                max_daily_triggers=get_constant('auto_redistribution.trigger_rules.critical_shortage.max_daily_triggers', 6),
                description="중요 부족 상황 시 즉시 재배치"
            ),
            AutoTriggerRule(
                condition=TriggerCondition.MULTI_PORT_SHORTAGE,
                threshold=get_constant('auto_redistribution.trigger_rules.multi_port_shortage.threshold', 3),  # 3개 이상 항구
                priority=get_constant('auto_redistribution.trigger_rules.multi_port_shortage.priority', 4),
                cooldown_hours=get_constant('auto_redistribution.trigger_rules.multi_port_shortage.cooldown_hours', 4),
                max_daily_triggers=get_constant('auto_redistribution.trigger_rules.multi_port_shortage.max_daily_triggers', 4),
                description="다중 항구 부족 시 재배치"
            ),
            AutoTriggerRule(
                condition=TriggerCondition.SEVERE_IMBALANCE,
                threshold=get_constant('auto_redistribution.trigger_rules.severe_imbalance.threshold', 0.8),  # 불균형 지수 0.8 이상
                priority=get_constant('auto_redistribution.trigger_rules.severe_imbalance.priority', 3),
                cooldown_hours=get_constant('auto_redistribution.trigger_rules.severe_imbalance.cooldown_hours', 6),
                max_daily_triggers=get_constant('auto_redistribution.trigger_rules.severe_imbalance.max_daily_triggers', 3),
                description="심각한 불균형 시 재배치"
            ),
            AutoTriggerRule(
                condition=TriggerCondition.PREDICTED_RISK,
                threshold=get_constant('auto_redistribution.trigger_rules.predicted_risk.threshold', 5),  # 5일 이내 위험
                priority=get_constant('auto_redistribution.trigger_rules.predicted_risk.priority', 2),
                cooldown_hours=get_constant('auto_redistribution.trigger_rules.predicted_risk.cooldown_hours', 12),
                max_daily_triggers=get_constant('auto_redistribution.trigger_rules.predicted_risk.max_daily_triggers', 2),
                description="예측된 위험에 대한 사전 재배치"
            ),
            AutoTriggerRule(
                condition=TriggerCondition.SCHEDULED,
                threshold=get_constant('auto_redistribution.trigger_rules.scheduled.threshold', 0),  # 스케줄 기반
                priority=get_constant('auto_redistribution.trigger_rules.scheduled.priority', 1),
                cooldown_hours=get_constant('auto_redistribution.trigger_rules.scheduled.cooldown_hours', 24),
                max_daily_triggers=get_constant('auto_redistribution.trigger_rules.scheduled.max_daily_triggers', 1),
                description="정기 재배치 최적화"
            )
        ]
    
    def check_and_execute_triggers(self, individual: Dict[str, Any], 
                                 current_timestamp: datetime = None) -> Dict[str, Any]:
        """트리거 조건 확인 및 실행"""
        if current_timestamp is None:
            current_timestamp = datetime.now()
        
        # 불균형 감지 수행
        imbalance_report = self.imbalance_detector.detect_real_time_imbalance(
            individual, current_timestamp
        )
        
        # 트리거 조건 평가
        triggered_conditions = self._evaluate_trigger_conditions(
            imbalance_report, current_timestamp
        )
        
        # 실행 가능한 트리거 선별
        executable_triggers = self._filter_executable_triggers(
            triggered_conditions, current_timestamp
        )
        
        # 자동 실행
        execution_results = []
        if self.auto_execution_enabled and executable_triggers:
            execution_results = self._execute_triggers(
                executable_triggers, individual, current_timestamp
            )
        
        return {
            'timestamp': current_timestamp,
            'imbalance_report': imbalance_report,
            'triggered_conditions': triggered_conditions,
            'executable_triggers': executable_triggers,
            'execution_results': execution_results,
            'recommendations': self._generate_trigger_recommendations(
                triggered_conditions, executable_triggers
            )
        }
    
    def _evaluate_trigger_conditions(self, imbalance_report: Dict[str, Any], 
                                   current_timestamp: datetime) -> List[Dict[str, Any]]:
        """트리거 조건 평가"""
        triggered_conditions = []
        
        imbalance_analysis = imbalance_report.get('imbalance_analysis', {})
        alerts = imbalance_report.get('alerts', [])
        predictions = imbalance_report.get('predictions', {})
        
        for rule in self.trigger_rules:
            triggered = False
            severity = 1
            affected_ports = []
            details = {}
            
            if rule.condition == TriggerCondition.CRITICAL_SHORTAGE:
                # 중요 부족 항구가 있는지 확인
                critical_shortage_ports = imbalance_analysis.get('critical_shortage_ports', [])
                if critical_shortage_ports:
                    triggered = True
                    severity = 5
                    affected_ports = critical_shortage_ports
                    details = {'critical_ports': critical_shortage_ports}
                    
            elif rule.condition == TriggerCondition.MULTI_PORT_SHORTAGE:
                # 여러 항구에서 부족 상황 확인
                shortage_ports = (imbalance_analysis.get('shortage_ports', []) + 
                                imbalance_analysis.get('critical_shortage_ports', []))
                if len(shortage_ports) >= rule.threshold:
                    triggered = True
                    severity = 4
                    affected_ports = shortage_ports
                    details = {'shortage_count': len(shortage_ports)}
                    
            elif rule.condition == TriggerCondition.SEVERE_IMBALANCE:
                # 심각한 불균형 확인
                imbalance_index = imbalance_analysis.get('imbalance_index', 0)
                if imbalance_index >= rule.threshold:
                    triggered = True
                    severity = 3
                    affected_ports = (imbalance_analysis.get('excess_ports', []) + 
                                    imbalance_analysis.get('shortage_ports', []))
                    details = {'imbalance_index': imbalance_index}
                    
            elif rule.condition == TriggerCondition.PREDICTED_RISK:
                # 예측된 위험 확인
                risk_ports = []
                for port, pred in predictions.items():
                    risk_days = pred.get('risk_days', [])
                    if risk_days and min(risk_days) <= rule.threshold:
                        risk_ports.append(port)
                
                if risk_ports:
                    triggered = True
                    severity = 2
                    affected_ports = risk_ports
                    details = {'risk_ports': risk_ports}
                    
            elif rule.condition == TriggerCondition.SCHEDULED:
                # 정기 스케줄 확인
                if self._is_scheduled_time(current_timestamp):
                    triggered = True
                    severity = 1
                    affected_ports = list(imbalance_analysis.get('port_levels', {}).keys())
                    details = {'scheduled_optimization': True}
            
            if triggered:
                triggered_conditions.append({
                    'rule': rule,
                    'severity': severity,
                    'affected_ports': affected_ports,
                    'details': details,
                    'timestamp': current_timestamp
                })
        
        return triggered_conditions
    
    def _filter_executable_triggers(self, triggered_conditions: List[Dict[str, Any]], 
                                   current_timestamp: datetime) -> List[Dict[str, Any]]:
        """실행 가능한 트리거 선별"""
        executable = []
        
        # 우선순위 순으로 정렬
        triggered_conditions.sort(key=lambda x: x['rule'].priority, reverse=True)
        
        for condition in triggered_conditions:
            rule = condition['rule']
            
            # 쿨다운 시간 확인
            if not self._check_cooldown(rule.condition, current_timestamp):
                continue
            
            # 일일 실행 횟수 확인
            if not self._check_daily_limit(rule, current_timestamp):
                continue
            
            # 동시 실행 제한 확인
            if len(executable) >= self.max_concurrent_triggers:
                break
            
            executable.append(condition)
        
        return executable
    
    def _check_cooldown(self, condition: TriggerCondition, current_timestamp: datetime) -> bool:
        """쿨다운 시간 확인"""
        if condition not in self.last_execution:
            return True
        
        last_time = self.last_execution[condition]
        rule = next(r for r in self.trigger_rules if r.condition == condition)
        
        time_diff = current_timestamp - last_time
        return time_diff.total_seconds() >= rule.cooldown_hours * 3600
    
    def _check_daily_limit(self, rule: AutoTriggerRule, current_timestamp: datetime) -> bool:
        """일일 실행 횟수 제한 확인"""
        today = current_timestamp.date()
        key = f"{rule.condition.value}_{today}"
        
        current_count = self.daily_trigger_count.get(key, 0)
        return current_count < rule.max_daily_triggers
    
    def _is_scheduled_time(self, current_timestamp: datetime) -> bool:
        """정기 스케줄 시간 확인 (매일 오전 6시)"""
        return current_timestamp.hour == 6 and current_timestamp.minute < 30
    
    def _execute_triggers(self, executable_triggers: List[Dict[str, Any]], 
                         individual: Dict[str, Any], 
                         current_timestamp: datetime) -> List[Dict[str, Any]]:
        """트리거 실행"""
        execution_results = []
        
        for trigger in executable_triggers:
            start_time = datetime.now()
            rule = trigger['rule']
            
            try:
                # 재배치 최적화 실행
                result = self._execute_redistribution_optimization(
                    trigger, individual, current_timestamp
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # 실행 기록
                event = TriggerEvent(
                    timestamp=current_timestamp,
                    condition=rule.condition,
                    triggered_ports=trigger['affected_ports'],
                    severity=trigger['severity'],
                    action_taken=result.get('action_description', ''),
                    success=result.get('success', False),
                    execution_time=execution_time
                )
                
                self.trigger_history.append(event)
                
                # 카운터 업데이트
                self._update_execution_counters(rule, current_timestamp)
                
                execution_results.append({
                    'trigger': trigger,
                    'result': result,
                    'execution_time': execution_time,
                    'success': result.get('success', False)
                })
                
            except Exception as e:
                execution_results.append({
                    'trigger': trigger,
                    'result': {'success': False, 'error': str(e)},
                    'execution_time': (datetime.now() - start_time).total_seconds(),
                    'success': False
                })
        
        return execution_results
    
    def _execute_redistribution_optimization(self, trigger: Dict[str, Any], 
                                           individual: Dict[str, Any],
                                           current_timestamp: datetime) -> Dict[str, Any]:
        """재배치 최적화 실행"""
        rule = trigger['rule']
        affected_ports = trigger['affected_ports']
        
        # 불균형 항구 식별
        imbalance_result = self.redistribution_optimizer.identify_imbalance_ports(individual)
        
        excess_ports = imbalance_result['excess_ports']
        shortage_ports = imbalance_result['shortage_ports']
        
        # 트리거 조건에 따른 특별 처리
        if rule.condition == TriggerCondition.CRITICAL_SHORTAGE:
            # 중요 부족 항구만 대상으로 제한
            shortage_ports = [p for p in shortage_ports if p in affected_ports]
            max_containers = get_constant('auto_redistribution.emergency.max_containers', 2000)  # 긴급 상황이므로 높은 한계
            
        elif rule.condition == TriggerCondition.MULTI_PORT_SHORTAGE:
            max_containers = 1500
            
        elif rule.condition == TriggerCondition.SEVERE_IMBALANCE:
            max_containers = 1000
            
        else:
            max_containers = 500
        
        if not excess_ports or not shortage_ports:
            return {
                'success': False,
                'reason': 'insufficient_imbalance',
                'action_description': '재배치 대상 항구 부족'
            }
        
        # 재배치 경로 최적화
        redistribution_paths = self.redistribution_optimizer.optimize_redistribution_paths(
            excess_ports, shortage_ports, max_containers
        )
        
        if not redistribution_paths:
            return {
                'success': False,
                'reason': 'no_viable_paths',
                'action_description': '실행 가능한 재배치 경로 없음'
            }
        
        # 재배치 계획 생성
        plan = self.redistribution_optimizer.generate_redistribution_plan(
            individual, force_execution=True
        )
        
        return {
            'success': True,
            'action_description': f'{len(redistribution_paths)}개 재배치 경로 실행',
            'plan': plan,
            'total_containers': sum(path.container_count for path in redistribution_paths),
            'total_cost': sum(path.cost for path in redistribution_paths),
            'execution_priority': rule.priority
        }
    
    def _update_execution_counters(self, rule: AutoTriggerRule, current_timestamp: datetime):
        """실행 카운터 업데이트"""
        # 마지막 실행 시간 업데이트
        self.last_execution[rule.condition] = current_timestamp
        
        # 일일 카운터 업데이트
        today = current_timestamp.date()
        key = f"{rule.condition.value}_{today}"
        self.daily_trigger_count[key] = self.daily_trigger_count.get(key, 0) + 1
        
        # 오래된 카운터 정리
        cutoff_date = current_timestamp.date() - timedelta(days=7)
        keys_to_remove = [k for k in self.daily_trigger_count.keys() 
                         if k.split('_')[-1] < str(cutoff_date)]
        for key in keys_to_remove:
            del self.daily_trigger_count[key]
    
    def _generate_trigger_recommendations(self, triggered_conditions: List[Dict[str, Any]], 
                                        executable_triggers: List[Dict[str, Any]]) -> List[str]:
        """트리거 권장사항 생성"""
        recommendations = []
        
        if not triggered_conditions:
            recommendations.append("✅ 현재 자동 재배치 트리거 조건 없음")
            return recommendations
        
        if executable_triggers:
            recommendations.append(f"🤖 {len(executable_triggers)}개 자동 트리거 실행 중")
            for trigger in executable_triggers:
                rule = trigger['rule']
                recommendations.append(f"   • {rule.description}")
        
        blocked_triggers = len(triggered_conditions) - len(executable_triggers)
        if blocked_triggers > 0:
            recommendations.append(f"⏳ {blocked_triggers}개 트리거가 쿨다운/제한으로 대기 중")
        
        # 수동 개입 권장사항
        critical_triggers = [t for t in triggered_conditions if t['severity'] >= 4]
        if critical_triggers and not executable_triggers:
            recommendations.append("⚠️  중요한 상황이지만 자동 트리거 제한됨 - 수동 개입 검토 필요")
        
        return recommendations
    
    def get_trigger_status(self) -> Dict[str, Any]:
        """트리거 시스템 상태 조회"""
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        
        recent_triggers = [t for t in self.trigger_history if t.timestamp >= recent_cutoff]
        
        return {
            'auto_execution_enabled': self.auto_execution_enabled,
            'total_trigger_rules': len(self.trigger_rules),
            'recent_triggers': len(recent_triggers),
            'successful_triggers': len([t for t in recent_triggers if t.success]),
            'failed_triggers': len([t for t in recent_triggers if not t.success]),
            'active_cooldowns': self._get_active_cooldowns(now),
            'daily_limits_status': self._get_daily_limits_status(now),
            'next_scheduled_trigger': self._get_next_scheduled_trigger(now)
        }
    
    def _get_active_cooldowns(self, current_time: datetime) -> Dict[str, int]:
        """현재 활성화된 쿨다운 상태"""
        active_cooldowns = {}
        
        for condition, last_time in self.last_execution.items():
            rule = next(r for r in self.trigger_rules if r.condition == condition)
            cooldown_end = last_time + timedelta(hours=rule.cooldown_hours)
            
            if cooldown_end > current_time:
                remaining_seconds = int((cooldown_end - current_time).total_seconds())
                active_cooldowns[condition.value] = remaining_seconds
        
        return active_cooldowns
    
    def _get_daily_limits_status(self, current_time: datetime) -> Dict[str, Dict[str, int]]:
        """일일 제한 상태"""
        today = current_time.date()
        status = {}
        
        for rule in self.trigger_rules:
            key = f"{rule.condition.value}_{today}"
            used = self.daily_trigger_count.get(key, 0)
            status[rule.condition.value] = {
                'used': used,
                'limit': rule.max_daily_triggers,
                'remaining': max(0, rule.max_daily_triggers - used)
            }
        
        return status
    
    def _get_next_scheduled_trigger(self, current_time: datetime) -> Optional[datetime]:
        """다음 정기 트리거 시간"""
        next_6am = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
        if current_time >= next_6am:
            next_6am += timedelta(days=1)
        return next_6am
    
    def enable_auto_execution(self):
        """자동 실행 활성화"""
        self.auto_execution_enabled = True
    
    def disable_auto_execution(self):
        """자동 실행 비활성화"""
        self.auto_execution_enabled = False
    
    def update_trigger_rule(self, condition: TriggerCondition, **kwargs):
        """트리거 규칙 업데이트"""
        rule = next((r for r in self.trigger_rules if r.condition == condition), None)
        if rule:
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)