#!/usr/bin/env python3
"""
실시간 모니터링 시스템
시스템 성능, 환경 변화, 데이터 품질을 실시간으로 모니터링
"""

import sys
import os
import time
import threading
import queue
import numpy as np
import pandas as pd
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
import json
import logging

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.parameters import GAParameters
from config import get_constant


class RealTimeMonitor:
    """실시간 시스템 모니터링"""
    
    def __init__(self, ga_parameters: GAParameters, 
                 monitoring_interval: float = 10.0,
                 alert_thresholds: Optional[Dict] = None):
        """
        Parameters:
        -----------
        ga_parameters : GAParameters
            모니터링할 GA 파라미터
        monitoring_interval : float
            모니터링 간격 (초)
        alert_thresholds : Dict
            알림 임계값 설정
        """
        self.ga_params = ga_parameters
        self.monitoring_interval = monitoring_interval
        
        # 기본 임계값 설정 (설정 파일에서 로드)
        self.alert_thresholds = alert_thresholds or {
            'performance_degradation': get_constant('monitoring.alert_thresholds.performance_degradation', 0.2),  # 20% 성능 저하
            'data_anomaly_score': get_constant('monitoring.alert_thresholds.data_anomaly_score', 0.8),           # 80% 이상 이상치
            'system_load': get_constant('monitoring.alert_thresholds.system_load', 0.9),                        # 90% 시스템 부하
            'memory_usage': get_constant('monitoring.alert_thresholds.memory_usage', 0.85),                     # 85% 메모리 사용
            'response_time': get_constant('monitoring.alert_thresholds.response_time', 30.0)                    # 30초 응답시간
        }
        
        # 모니터링 상태
        self.is_monitoring = False
        self.monitor_thread = None
        self.data_queue = queue.Queue()
        
        # 메트릭 저장
        self.metrics_history = []
        self.alerts_history = []
        self.performance_baseline = None
        
        # 콜백 함수들
        self.alert_callbacks = []
        self.metric_callbacks = []
        
        # 로깅 설정
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """로깅 시스템 설정"""
        logger = logging.getLogger('RealTimeMonitor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def start_monitoring(self):
        """실시간 모니터링 시작"""
        if self.is_monitoring:
            self.logger.warning("Monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info(f"🔍 Real-time monitoring started (interval: {self.monitoring_interval}s)")
    
    def stop_monitoring(self):
        """실시간 모니터링 중지"""
        if not self.is_monitoring:
            self.logger.warning("Monitoring is not running")
            return
        
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("🛑 Real-time monitoring stopped")
    
    def _monitoring_loop(self):
        """메인 모니터링 루프"""
        self.logger.info("📡 Monitoring loop started")
        
        while self.is_monitoring:
            try:
                # 메트릭 수집
                metrics = self._collect_metrics()
                
                # 이상 감지
                anomalies = self._detect_anomalies(metrics)
                
                # 알림 처리
                if anomalies:
                    self._handle_alerts(anomalies, metrics)
                
                # 메트릭 저장
                self._store_metrics(metrics, anomalies)
                
                # 콜백 실행
                self._execute_callbacks(metrics, anomalies)
                
                # 다음 주기까지 대기
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(self.monitoring_interval)
        
        self.logger.info("📡 Monitoring loop ended")
    
    def _collect_metrics(self) -> Dict:
        """시스템 메트릭 수집"""
        metrics = {
            'timestamp': datetime.now(),
            'system_metrics': self._collect_system_metrics(),
            'data_metrics': self._collect_data_metrics(),
            'performance_metrics': self._collect_performance_metrics(),
            'ga_metrics': self._collect_ga_metrics()
        }
        
        return metrics
    
    def _collect_system_metrics(self) -> Dict:
        """시스템 리소스 메트릭 수집"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_io': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
                'process_count': len(psutil.pids()),
                'boot_time': psutil.boot_time()
            }
        except ImportError:
            # psutil이 없으면 기본 메트릭만
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_usage': 0,
                'network_io': {},
                'process_count': 0,
                'boot_time': 0
            }
    
    def _collect_data_metrics(self) -> Dict:
        """데이터 품질 메트릭 수집"""
        schedule_data = self.ga_params.schedule_data
        
        return {
            'total_schedules': len(schedule_data),
            'data_completeness': (1 - schedule_data.isnull().sum().sum() / schedule_data.size),
            'data_freshness': (datetime.now() - schedule_data['ETD'].max()).days,
            'demand_variance': schedule_data['주문량(KG)'].var() if '주문량(KG)' in schedule_data else 0,
            'schedule_distribution': self._calculate_schedule_distribution(),
            'anomalous_values': self._detect_data_anomalies()
        }
    
    def _collect_performance_metrics(self) -> Dict:
        """성능 메트릭 수집"""
        # 더미 성능 데이터 (실제 환경에서는 최근 최적화 결과 사용)
        return {
            'avg_response_time': np.random.normal(15, 3),  # 평균 15초, 표준편차 3초
            'optimization_success_rate': np.random.uniform(0.85, 0.98),
            'convergence_speed': np.random.normal(25, 5),  # 평균 25세대
            'solution_quality': np.random.uniform(-5000, -3000),  # fitness 값
            'memory_efficiency': np.random.uniform(0.7, 0.9)
        }
    
    def _collect_ga_metrics(self) -> Dict:
        """GA 특화 메트릭 수집"""
        return {
            'population_diversity': self._calculate_population_diversity(),
            'constraint_violations': self._count_constraint_violations(),
            'parameter_stability': self._measure_parameter_stability(),
            'adaptive_adjustments': self._count_recent_adjustments()
        }
    
    def _calculate_schedule_distribution(self) -> Dict:
        """스케줄 분포 계산"""
        schedule_data = self.ga_params.schedule_data
        
        # 시간별 분포
        schedule_data['hour'] = pd.to_datetime(schedule_data['ETD']).dt.hour
        hourly_dist = schedule_data['hour'].value_counts()
        
        return {
            'hourly_std': hourly_dist.std(),
            'peak_hour': hourly_dist.idxmax(),
            'min_hour': hourly_dist.idxmin(),
            'distribution_entropy': self._calculate_entropy(hourly_dist.values)
        }
    
    def _detect_data_anomalies(self) -> int:
        """데이터 이상치 감지"""
        schedule_data = self.ga_params.schedule_data
        anomalies = 0
        
        # 주문량 이상치
        if '주문량(KG)' in schedule_data:
            demand_data = schedule_data['주문량(KG)'].dropna()
            if len(demand_data) > 0:
                Q1 = demand_data.quantile(0.25)
                Q3 = demand_data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                anomalies += ((demand_data < lower_bound) | (demand_data > upper_bound)).sum()
        
        return anomalies
    
    def _calculate_population_diversity(self) -> float:
        """인구 다양성 계산 (시뮬레이션)"""
        # 실제로는 현재 GA 인구의 다양성을 계산
        return np.random.uniform(0.3, 0.8)
    
    def _count_constraint_violations(self) -> int:
        """제약 위반 개수 (시뮬레이션)"""
        return np.random.poisson(5)  # 평균 5개 위반
    
    def _measure_parameter_stability(self) -> float:
        """파라미터 안정성 측정"""
        # 최근 메트릭 이력을 기반으로 계산
        if len(self.metrics_history) < 3:
            return 1.0
        
        recent_metrics = self.metrics_history[-3:]
        stability_scores = []
        
        for metric_name in ['performance_metrics']:
            values = [m[metric_name].get('solution_quality', 0) for m in recent_metrics]
            if len(values) > 1:
                stability = 1 / (1 + np.std(values))
                stability_scores.append(stability)
        
        return np.mean(stability_scores) if stability_scores else 1.0
    
    def _count_recent_adjustments(self) -> int:
        """최근 적응 조정 횟수"""
        # 실제로는 DynamicUpdater의 이력 확인
        return np.random.poisson(2)
    
    def _calculate_entropy(self, values: np.ndarray) -> float:
        """엔트로피 계산"""
        if len(values) == 0:
            return 0
        
        probs = values / values.sum()
        probs = probs[probs > 0]  # 0 확률 제거
        
        return -np.sum(probs * np.log2(probs))
    
    def _detect_anomalies(self, metrics: Dict) -> List[Dict]:
        """이상 상황 감지"""
        anomalies = []
        
        # 성능 저하 감지
        current_quality = metrics['performance_metrics']['solution_quality']
        if self.performance_baseline is not None:
            degradation = (self.performance_baseline - current_quality) / abs(self.performance_baseline)
            if degradation > self.alert_thresholds['performance_degradation']:
                anomalies.append({
                    'type': 'performance_degradation',
                    'severity': 'high',
                    'value': degradation,
                    'threshold': self.alert_thresholds['performance_degradation'],
                    'message': f"Performance degraded by {degradation:.2%}"
                })
        
        # 시스템 부하 감지
        cpu_usage = metrics['system_metrics']['cpu_percent'] / 100
        if cpu_usage > self.alert_thresholds['system_load']:
            anomalies.append({
                'type': 'high_system_load',
                'severity': 'medium',
                'value': cpu_usage,
                'threshold': self.alert_thresholds['system_load'],
                'message': f"High CPU usage: {cpu_usage:.1%}"
            })
        
        # 메모리 사용량 감지
        memory_usage = metrics['system_metrics']['memory_percent'] / 100
        if memory_usage > self.alert_thresholds['memory_usage']:
            anomalies.append({
                'type': 'high_memory_usage',
                'severity': 'medium',
                'value': memory_usage,
                'threshold': self.alert_thresholds['memory_usage'],
                'message': f"High memory usage: {memory_usage:.1%}"
            })
        
        # 응답시간 감지
        response_time = metrics['performance_metrics']['avg_response_time']
        if response_time > self.alert_thresholds['response_time']:
            anomalies.append({
                'type': 'slow_response',
                'severity': 'low',
                'value': response_time,
                'threshold': self.alert_thresholds['response_time'],
                'message': f"Slow response time: {response_time:.1f}s"
            })
        
        # 데이터 이상치 감지
        anomaly_count = metrics['data_metrics']['anomalous_values']
        total_data = metrics['data_metrics']['total_schedules']
        anomaly_ratio = anomaly_count / total_data if total_data > 0 else 0
        
        if anomaly_ratio > self.alert_thresholds['data_anomaly_score']:
            anomalies.append({
                'type': 'data_anomaly',
                'severity': 'high',
                'value': anomaly_ratio,
                'threshold': self.alert_thresholds['data_anomaly_score'],
                'message': f"High data anomaly rate: {anomaly_ratio:.1%}"
            })
        
        return anomalies
    
    def _handle_alerts(self, anomalies: List[Dict], metrics: Dict):
        """알림 처리"""
        for anomaly in anomalies:
            alert = {
                'timestamp': datetime.now(),
                'anomaly': anomaly,
                'metrics_snapshot': metrics,
                'alert_id': f"alert_{len(self.alerts_history)}"
            }
            
            self.alerts_history.append(alert)
            
            # 로그 출력
            severity_emoji = {'low': '🟡', 'medium': '🟠', 'high': '🔴'}
            emoji = severity_emoji.get(anomaly['severity'], '⚪')
            
            self.logger.warning(f"{emoji} ALERT [{anomaly['type']}]: {anomaly['message']}")
    
    def _store_metrics(self, metrics: Dict, anomalies: List[Dict]):
        """메트릭 저장"""
        metrics_entry = {
            'timestamp': metrics['timestamp'],
            'metrics': metrics,
            'anomalies': anomalies,
            'anomaly_count': len(anomalies)
        }
        
        self.metrics_history.append(metrics_entry)
        
        # 히스토리 크기 제한 (최근 1000개만 보관)
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def _execute_callbacks(self, metrics: Dict, anomalies: List[Dict]):
        """등록된 콜백 함수 실행"""
        # 메트릭 콜백
        for callback in self.metric_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                self.logger.error(f"Metric callback error: {e}")
        
        # 알림 콜백
        if anomalies:
            for callback in self.alert_callbacks:
                try:
                    callback(anomalies, metrics)
                except Exception as e:
                    self.logger.error(f"Alert callback error: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """알림 콜백 등록"""
        self.alert_callbacks.append(callback)
        self.logger.info("Alert callback registered")
    
    def register_metric_callback(self, callback: Callable):
        """메트릭 콜백 등록"""
        self.metric_callbacks.append(callback)
        self.logger.info("Metric callback registered")
    
    def set_performance_baseline(self, baseline_value: float):
        """성능 기준선 설정"""
        self.performance_baseline = baseline_value
        self.logger.info(f"Performance baseline set: {baseline_value:.2f}")
    
    def get_current_status(self) -> Dict:
        """현재 모니터링 상태 반환"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        latest_metrics = self.metrics_history[-1]
        recent_alerts = [a for a in self.alerts_history if 
                        (datetime.now() - a['timestamp']).seconds < 3600]  # 최근 1시간
        
        return {
            'monitoring_active': self.is_monitoring,
            'latest_metrics_time': latest_metrics['timestamp'],
            'recent_alerts_count': len(recent_alerts),
            'total_metrics_collected': len(self.metrics_history),
            'system_health': self._assess_system_health(),
            'performance_baseline': self.performance_baseline
        }
    
    def _assess_system_health(self) -> str:
        """시스템 건강도 평가"""
        if not self.metrics_history:
            return 'unknown'
        
        recent_alerts = [a for a in self.alerts_history if 
                        (datetime.now() - a['timestamp']).seconds < 3600]
        
        high_severity_alerts = [a for a in recent_alerts if 
                               a['anomaly']['severity'] == 'high']
        
        if len(high_severity_alerts) > 0:
            return 'critical'
        elif len(recent_alerts) > 5:
            return 'warning'
        else:
            return 'healthy'
    
    def export_metrics(self, filepath: str, hours_back: int = 24):
        """메트릭 데이터 내보내기"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        filtered_metrics = [
            m for m in self.metrics_history 
            if m['timestamp'] >= cutoff_time
        ]
        
        try:
            # JSON으로 저장 (datetime 직렬화 처리)
            def datetime_converter(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError
            
            with open(filepath, 'w') as f:
                json.dump(filtered_metrics, f, default=datetime_converter, indent=2)
            
            self.logger.info(f"📊 Exported {len(filtered_metrics)} metrics to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")