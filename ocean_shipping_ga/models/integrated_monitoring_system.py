"""
통합 모니터링 및 알림 시스템
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import logging
from threading import Thread, Event
import time

from .dynamic_imbalance_detector import DynamicImbalanceDetector, ImbalanceAlert
from .auto_redistribution_trigger import AutoRedistributionTrigger, TriggerEvent
from .monitoring_dashboard import RealTimeMonitoringDashboard
from visualization.graph_visualizer import GraphVisualizer
from config import get_constant


class AlertSeverity(Enum):
    """알림 심각도"""
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4


class SystemStatus(Enum):
    """시스템 상태"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


@dataclass
class SystemAlert:
    """시스템 알림"""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    category: str
    title: str
    message: str
    affected_ports: List[str]
    recommended_actions: List[str]
    auto_resolved: bool = False
    acknowledged: bool = False
    resolved_timestamp: Optional[datetime] = None


@dataclass
class MonitoringMetrics:
    """모니터링 메트릭"""
    timestamp: datetime
    system_health_score: float  # 0-100
    total_alerts: int
    critical_alerts: int
    imbalance_index: float
    efficiency_score: float
    redistribution_cost: float
    auto_trigger_success_rate: float


class IntegratedMonitoringSystem:
    """
    통합 모니터링 및 알림 시스템
    모든 하위 시스템을 통합하여 실시간 모니터링 및 알림을 제공
    """
    
    def __init__(self, params):
        self.params = params
        
        # 하위 시스템 초기화
        self.imbalance_detector = DynamicImbalanceDetector(params)
        self.auto_trigger = AutoRedistributionTrigger(params, self.imbalance_detector, None)  # redistribution_optimizer는 나중에 설정
        self.dashboard = RealTimeMonitoringDashboard(params, self.imbalance_detector, self.auto_trigger)
        self.graph_visualizer = GraphVisualizer(params)
        
        # 시스템 상태
        self.system_status = SystemStatus.HEALTHY
        self.last_update = None
        self.monitoring_enabled = False
        self.monitoring_thread = None
        self.stop_event = Event()
        
        # 알림 시스템
        self.alerts = []
        self.alert_handlers = []  # 외부 알림 핸들러들
        self.alert_id_counter = 0
        
        # 메트릭 히스토리
        self.metrics_history = []
        self.max_history_size = 10000
        
        # 설정 (설정 파일에서 로드)
        self.monitoring_interval = get_constant('monitoring.monitoring_interval', 60)  # 60초마다 모니터링
        self.alert_retention_days = 30
        self.health_threshold = {
            'critical': 40,
            'warning': 70,
            'healthy': 85
        }
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring_enabled:
            self.logger.warning("모니터링이 이미 실행 중입니다")
            return
        
        self.monitoring_enabled = True
        self.stop_event.clear()
        
        # 모니터링 스레드 시작
        self.monitoring_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("통합 모니터링 시스템이 시작되었습니다")
        
        # 시작 알림
        self._create_system_alert(
            AlertSeverity.INFO,
            "system",
            "모니터링 시스템 시작",
            "통합 모니터링 시스템이 성공적으로 시작되었습니다",
            [],
            ["시스템 상태 확인"]
        )
    
    def stop_monitoring(self):
        """모니터링 중지"""
        if not self.monitoring_enabled:
            self.logger.warning("모니터링이 실행되고 있지 않습니다")
            return
        
        self.monitoring_enabled = False
        self.stop_event.set()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("통합 모니터링 시스템이 중지되었습니다")
        
        # 중지 알림
        self._create_system_alert(
            AlertSeverity.INFO,
            "system", 
            "모니터링 시스템 중지",
            "통합 모니터링 시스템이 중지되었습니다",
            [],
            []
        )
    
    def _monitoring_loop(self):
        """모니터링 메인 루프"""
        while self.monitoring_enabled and not self.stop_event.is_set():
            try:
                # 현재 시스템 상태 수집
                current_time = datetime.now()
                
                # 더미 개체 생성 (실제 구현에서는 현재 최적 솔루션 사용)
                dummy_individual = self._create_dummy_individual()
                
                # 통합 상태 업데이트
                self._update_system_status(dummy_individual, current_time)
                
                # 메트릭 수집 및 저장
                metrics = self._collect_metrics(current_time)
                self._store_metrics(metrics)
                
                # 시스템 헬스 체크
                self._perform_health_check(metrics)
                
                # 자동 복구 시도
                self._attempt_auto_recovery()
                
                # 알림 정리
                self._cleanup_old_alerts()
                
            except Exception as e:
                self.logger.error(f"모니터링 루프 오류: {e}")
                self._create_system_alert(
                    AlertSeverity.CRITICAL,
                    "system_error",
                    "모니터링 시스템 오류",
                    f"모니터링 과정에서 오류가 발생했습니다: {e}",
                    [],
                    ["시스템 로그 확인", "재시작 고려"]
                )
            
            # 다음 모니터링까지 대기
            self.stop_event.wait(self.monitoring_interval)
    
    def _create_dummy_individual(self) -> Dict[str, Any]:
        """더미 개체 생성 (테스트용)"""
        num_schedules = len(self.params.I) if hasattr(self.params, 'I') else 10
        num_ports = len(self.params.P) if hasattr(self.params, 'P') else 8
        
        return {
            'xF': np.random.randint(100, 1000, num_schedules),
            'xE': np.random.randint(50, 500, num_schedules),
            'y': np.random.randint(1000, 5000, (num_schedules, num_ports)),
            'fitness': -50000
        }
    
    def _update_system_status(self, individual: Dict[str, Any], current_time: datetime):
        """시스템 상태 업데이트"""
        try:
            # 대시보드 데이터 업데이트
            snapshot = self.dashboard.update_dashboard_data(individual, current_time)
            
            # 자동 트리거 확인
            trigger_result = self.auto_trigger.check_and_execute_triggers(individual, current_time)
            
            # 불균형 분석
            imbalance_report = snapshot['imbalance_report']
            
            # 새로운 알림 생성
            self._process_imbalance_alerts(imbalance_report.get('alerts', []))
            self._process_trigger_results(trigger_result.get('execution_results', []))
            
            self.last_update = current_time
            
        except Exception as e:
            self.logger.error(f"시스템 상태 업데이트 실패: {e}")
            self._update_system_status_to_critical("상태 업데이트 실패")
    
    def _collect_metrics(self, current_time: datetime) -> MonitoringMetrics:
        """메트릭 수집"""
        try:
            # 대시보드에서 현재 메트릭 가져오기
            dashboard_snapshot = self.dashboard.current_snapshot
            
            if dashboard_snapshot:
                metrics_data = dashboard_snapshot['metrics']
                trigger_status = dashboard_snapshot['trigger_status']
                
                return MonitoringMetrics(
                    timestamp=current_time,
                    system_health_score=self._calculate_system_health_score(),
                    total_alerts=len(self.alerts),
                    critical_alerts=len([a for a in self.alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]]),
                    imbalance_index=metrics_data.imbalance_index,
                    efficiency_score=metrics_data.efficiency_score,
                    redistribution_cost=metrics_data.redistribution_cost,
                    auto_trigger_success_rate=self._calculate_trigger_success_rate(trigger_status)
                )
            else:
                # 기본값 반환
                return MonitoringMetrics(
                    timestamp=current_time,
                    system_health_score=50.0,
                    total_alerts=len(self.alerts),
                    critical_alerts=0,
                    imbalance_index=0.0,
                    efficiency_score=0.0,
                    redistribution_cost=0.0,
                    auto_trigger_success_rate=0.0
                )
                
        except Exception as e:
            self.logger.error(f"메트릭 수집 실패: {e}")
            return MonitoringMetrics(
                timestamp=current_time,
                system_health_score=0.0,
                total_alerts=len(self.alerts),
                critical_alerts=1,
                imbalance_index=1.0,
                efficiency_score=0.0,
                redistribution_cost=0.0,
                auto_trigger_success_rate=0.0
            )
    
    def _calculate_system_health_score(self) -> float:
        """시스템 헬스 점수 계산 (0-100)"""
        try:
            score = 100.0
            
            # 활성 알림으로 인한 감점
            critical_alerts = len([a for a in self.alerts if a.severity == AlertSeverity.CRITICAL])
            emergency_alerts = len([a for a in self.alerts if a.severity == AlertSeverity.EMERGENCY])
            warning_alerts = len([a for a in self.alerts if a.severity == AlertSeverity.WARNING])
            
            score -= emergency_alerts * 30  # 응급 알림당 30점 감점
            score -= critical_alerts * 15   # 중요 알림당 15점 감점  
            score -= warning_alerts * 5     # 경고 알림당 5점 감점
            
            # 최근 업데이트 시간으로 인한 감점
            if self.last_update:
                time_since_update = (datetime.now() - self.last_update).total_seconds()
                if time_since_update > 300:  # 5분 이상 업데이트 없음
                    score -= min(30, time_since_update / 60)  # 분당 1점, 최대 30점 감점
            
            # 시스템 상태로 인한 감점
            if self.system_status == SystemStatus.CRITICAL:
                score -= 40
            elif self.system_status == SystemStatus.WARNING:
                score -= 20
            elif self.system_status == SystemStatus.MAINTENANCE:
                score -= 10
            
            return max(0.0, min(100.0, score))
            
        except Exception:
            return 0.0
    
    def _calculate_trigger_success_rate(self, trigger_status: Dict[str, Any]) -> float:
        """트리거 성공률 계산"""
        successful = trigger_status.get('successful_triggers', 0)
        failed = trigger_status.get('failed_triggers', 0)
        total = successful + failed
        
        return (successful / total * 100) if total > 0 else 100.0
    
    def _store_metrics(self, metrics: MonitoringMetrics):
        """메트릭 저장"""
        self.metrics_history.append(metrics)
        
        # 히스토리 크기 제한
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
    
    def _perform_health_check(self, metrics: MonitoringMetrics):
        """시스템 헬스 체크"""
        health_score = metrics.system_health_score
        
        previous_status = self.system_status
        
        # 시스템 상태 결정
        if health_score >= self.health_threshold['healthy']:
            self.system_status = SystemStatus.HEALTHY
        elif health_score >= self.health_threshold['warning']:
            self.system_status = SystemStatus.WARNING
        elif health_score >= self.health_threshold['critical']:
            self.system_status = SystemStatus.CRITICAL
        else:
            self.system_status = SystemStatus.CRITICAL
        
        # 상태 변경 시 알림
        if previous_status != self.system_status:
            self._create_status_change_alert(previous_status, self.system_status, health_score)
    
    def _create_status_change_alert(self, old_status: SystemStatus, 
                                  new_status: SystemStatus, health_score: float):
        """상태 변경 알림 생성"""
        severity_map = {
            SystemStatus.HEALTHY: AlertSeverity.INFO,
            SystemStatus.WARNING: AlertSeverity.WARNING,
            SystemStatus.CRITICAL: AlertSeverity.CRITICAL,
            SystemStatus.MAINTENANCE: AlertSeverity.INFO,
            SystemStatus.OFFLINE: AlertSeverity.EMERGENCY
        }
        
        self._create_system_alert(
            severity_map[new_status],
            "system_status",
            f"시스템 상태 변경: {old_status.value} → {new_status.value}",
            f"시스템 헬스 점수: {health_score:.1f}/100",
            [],
            self._get_status_recommendations(new_status)
        )
    
    def _get_status_recommendations(self, status: SystemStatus) -> List[str]:
        """상태별 권장사항"""
        recommendations = {
            SystemStatus.HEALTHY: ["정상 운영 중"],
            SystemStatus.WARNING: ["시스템 상태 모니터링 강화", "예방적 조치 검토"],
            SystemStatus.CRITICAL: ["즉시 문제 해결 필요", "수동 개입 고려"],
            SystemStatus.MAINTENANCE: ["유지보수 모드 활성"],
            SystemStatus.OFFLINE: ["시스템 재시작 필요"]
        }
        
        return recommendations.get(status, [])
    
    def _attempt_auto_recovery(self):
        """자동 복구 시도"""
        if self.system_status in [SystemStatus.CRITICAL, SystemStatus.OFFLINE]:
            try:
                # 간단한 자동 복구 로직
                recovery_success = self._perform_basic_recovery()
                
                if recovery_success:
                    self._create_system_alert(
                        AlertSeverity.INFO,
                        "auto_recovery",
                        "자동 복구 성공",
                        "시스템이 자동으로 복구되었습니다",
                        [],
                        ["상태 모니터링 계속"]
                    )
                    
            except Exception as e:
                self.logger.error(f"자동 복구 실패: {e}")
    
    def _perform_basic_recovery(self) -> bool:
        """기본 복구 작업"""
        try:
            # 기본 복구 로직 (예: 캐시 정리, 재연결 등)
            # 실제 구현에서는 더 구체적인 복구 작업 수행
            
            # 알림 정리
            self._cleanup_old_alerts()
            
            # 메트릭 재계산
            if self.dashboard.current_snapshot:
                return True
                
            return False
            
        except Exception:
            return False
    
    def _process_imbalance_alerts(self, imbalance_alerts: List[ImbalanceAlert]):
        """불균형 알림 처리"""
        for alert in imbalance_alerts:
            if alert.severity >= 4:  # 중요한 알림만
                self._create_system_alert(
                    AlertSeverity.CRITICAL if alert.severity >= 5 else AlertSeverity.WARNING,
                    "imbalance",
                    f"{alert.port} 항구 {alert.alert_type}",
                    f"현재 수준: {alert.current_level:.0f} TEU, 임계값: {alert.threshold_level:.0f} TEU",
                    [alert.port],
                    [alert.recommended_action]
                )
    
    def _process_trigger_results(self, trigger_results: List[Dict[str, Any]]):
        """트리거 결과 처리"""
        for result in trigger_results:
            if not result.get('success', True):
                self._create_system_alert(
                    AlertSeverity.WARNING,
                    "trigger_failure",
                    "자동 트리거 실행 실패",
                    f"트리거 실행 중 오류 발생: {result.get('error', '알 수 없는 오류')}",
                    [],
                    ["수동 재배치 검토", "트리거 설정 확인"]
                )
    
    def _create_system_alert(self, severity: AlertSeverity, category: str,
                           title: str, message: str, affected_ports: List[str],
                           recommended_actions: List[str]) -> SystemAlert:
        """시스템 알림 생성"""
        self.alert_id_counter += 1
        alert_id = f"ALERT_{self.alert_id_counter:06d}"
        
        alert = SystemAlert(
            id=alert_id,
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            title=title,
            message=message,
            affected_ports=affected_ports,
            recommended_actions=recommended_actions
        )
        
        self.alerts.append(alert)
        
        # 외부 핸들러에 알림
        self._notify_alert_handlers(alert)
        
        # 로그 기록
        self.logger.log(
            self._get_log_level(severity),
            f"[{category.upper()}] {title}: {message}"
        )
        
        return alert
    
    def _get_log_level(self, severity: AlertSeverity) -> int:
        """심각도에 따른 로그 레벨"""
        level_map = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.CRITICAL: logging.ERROR,
            AlertSeverity.EMERGENCY: logging.CRITICAL
        }
        return level_map.get(severity, logging.INFO)
    
    def _notify_alert_handlers(self, alert: SystemAlert):
        """알림 핸들러들에 통지"""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"알림 핸들러 실행 실패: {e}")
    
    def _cleanup_old_alerts(self):
        """오래된 알림 정리"""
        cutoff_time = datetime.now() - timedelta(days=self.alert_retention_days)
        
        # 해결되지 않은 중요 알림은 보존
        self.alerts = [
            alert for alert in self.alerts
            if (alert.timestamp >= cutoff_time or 
                (not alert.auto_resolved and alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]))
        ]
    
    def add_alert_handler(self, handler: Callable[[SystemAlert], None]):
        """알림 핸들러 추가"""
        self.alert_handlers.append(handler)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """알림 확인"""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                alert.resolved_timestamp = datetime.now()
                
                self.logger.info(f"알림 확인됨: {alert_id}")
                return True
        
        return False
    
    def get_system_summary(self) -> Dict[str, Any]:
        """시스템 요약 정보"""
        current_time = datetime.now()
        recent_cutoff = current_time - timedelta(hours=24)
        
        recent_alerts = [a for a in self.alerts if a.timestamp >= recent_cutoff]
        active_alerts = [a for a in self.alerts if not a.acknowledged and not a.auto_resolved]
        
        latest_metrics = self.metrics_history[-1] if self.metrics_history else None
        
        return {
            'system_status': self.system_status.value,
            'health_score': latest_metrics.system_health_score if latest_metrics else 0,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'monitoring_enabled': self.monitoring_enabled,
            'total_alerts': len(self.alerts),
            'active_alerts': len(active_alerts),
            'recent_alerts_24h': len(recent_alerts),
            'critical_alerts': len([a for a in active_alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]]),
            'efficiency_score': latest_metrics.efficiency_score if latest_metrics else 0,
            'imbalance_index': latest_metrics.imbalance_index if latest_metrics else 0,
            'auto_trigger_success_rate': latest_metrics.auto_trigger_success_rate if latest_metrics else 0
        }
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """알림 요약 정보"""
        active_alerts = [a for a in self.alerts if not a.acknowledged and not a.auto_resolved]
        
        by_severity = {}
        by_category = {}
        
        for alert in active_alerts:
            # 심각도별
            severity_key = alert.severity.name
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
            
            # 카테고리별
            by_category[alert.category] = by_category.get(alert.category, 0) + 1
        
        return {
            'total_active': len(active_alerts),
            'by_severity': by_severity,
            'by_category': by_category,
            'oldest_unresolved': min((a.timestamp for a in active_alerts), default=None),
            'most_recent': max((a.timestamp for a in active_alerts), default=None)
        }
    
    def export_monitoring_data(self, file_path: str = None) -> str:
        """모니터링 데이터 내보내기"""
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = f"monitoring_export_{timestamp}.json"
        
        # datetime 객체를 문자열로 변환하는 헬퍼 함수
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        # alert_summary에서 datetime 객체 처리
        alert_summary = self.get_alert_summary()
        if alert_summary.get('oldest_unresolved'):
            alert_summary['oldest_unresolved'] = alert_summary['oldest_unresolved'].isoformat()
        if alert_summary.get('most_recent'):
            alert_summary['most_recent'] = alert_summary['most_recent'].isoformat()
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'system_summary': self.get_system_summary(),
            'alert_summary': alert_summary,
            'recent_metrics': [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'health_score': m.system_health_score,
                    'total_alerts': m.total_alerts,
                    'critical_alerts': m.critical_alerts,
                    'imbalance_index': m.imbalance_index,
                    'efficiency_score': m.efficiency_score
                }
                for m in self.metrics_history[-100:]  # 최근 100개
            ],
            'active_alerts': [
                {
                    'id': alert.id,
                    'timestamp': alert.timestamp.isoformat(),
                    'severity': alert.severity.name,
                    'category': alert.category,
                    'title': alert.title,
                    'message': alert.message,
                    'affected_ports': alert.affected_ports,
                    'acknowledged': alert.acknowledged
                }
                for alert in self.alerts if not alert.acknowledged and not alert.auto_resolved
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def _update_system_status_to_critical(self, reason: str):
        """시스템 상태를 중요로 변경"""
        if self.system_status != SystemStatus.CRITICAL:
            old_status = self.system_status
            self.system_status = SystemStatus.CRITICAL
            
            self._create_system_alert(
                AlertSeverity.CRITICAL,
                "system_critical",
                "시스템 상태 중요",
                f"시스템이 중요 상태로 변경되었습니다: {reason}",
                [],
                ["즉시 점검 필요", "수동 개입 고려"]
            )
    
    def force_health_check(self) -> Dict[str, Any]:
        """강제 헬스 체크 실행"""
        current_time = datetime.now()
        metrics = self._collect_metrics(current_time)
        self._perform_health_check(metrics)
        
        return {
            'timestamp': current_time.isoformat(),
            'health_score': metrics.system_health_score,
            'system_status': self.system_status.value,
            'metrics': {
                'total_alerts': metrics.total_alerts,
                'critical_alerts': metrics.critical_alerts,
                'imbalance_index': metrics.imbalance_index,
                'efficiency_score': metrics.efficiency_score
            }
        }