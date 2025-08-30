"""
동적 불균형 감지 시스템
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from config import get_constant


@dataclass
class ImbalanceAlert:
    """불균형 경고 데이터 클래스"""
    port: str
    alert_type: str  # 'excess', 'shortage', 'critical_shortage'
    severity: int    # 1-5 (1=낮음, 5=매우 높음)
    current_level: float
    threshold_level: float
    deviation: float
    timestamp: datetime
    estimated_duration: Optional[int]  # 예상 지속 시간(일)
    recommended_action: str


class DynamicImbalanceDetector:
    """
    실시간 컨테이너 불균형 감지 및 예측 시스템
    """
    
    def __init__(self, params):
        self.params = params
        
        # 임계값 설정 (설정 파일에서 로드)
        self.critical_shortage_threshold = get_constant('imbalance_detection.critical_shortage_threshold', 0.2)  # 20% 이하
        self.shortage_threshold = get_constant('imbalance_detection.shortage_threshold', 0.4)                   # 40% 이하
        self.excess_threshold = get_constant('imbalance_detection.excess_threshold', 1.6)                       # 160% 이상
        self.critical_excess_threshold = get_constant('imbalance_detection.critical_excess_threshold', 2.0)    # 200% 이상
        
        # 히스토리 추적
        self.inventory_history = []
        self.alert_history = []
        self.prediction_horizon = get_constant('imbalance_detection.prediction_horizon', 30)  # 30일 예측
        
        # 동적 임계값 계산을 위한 통계
        self.rolling_window = get_constant('imbalance_detection.rolling_window', 14)  # 14일 롤링 윈도우
        self.adaptive_thresholds = {}
        
    def detect_real_time_imbalance(self, individual: Dict[str, Any], 
                                 current_timestamp: datetime = None) -> Dict[str, Any]:
        """실시간 불균형 감지"""
        if current_timestamp is None:
            current_timestamp = datetime.now()
            
        # 현재 컨테이너 수준 계산
        current_levels = self._calculate_current_inventory_levels(individual)
        
        # 동적 임계값 업데이트
        self._update_adaptive_thresholds(current_levels, current_timestamp)
        
        # 불균형 분석
        imbalance_analysis = self._analyze_imbalance_patterns(current_levels)
        
        # 경고 생성
        alerts = self._generate_alerts(current_levels, imbalance_analysis, current_timestamp)
        
        # 예측 수행
        predictions = self._predict_future_imbalance(current_levels, current_timestamp)
        
        # 권장사항 생성
        recommendations = self._generate_recommendations(alerts, predictions)
        
        # 히스토리 업데이트
        self._update_history(current_levels, alerts, current_timestamp)
        
        return {
            'timestamp': current_timestamp,
            'current_levels': current_levels,
            'imbalance_analysis': imbalance_analysis,
            'alerts': alerts,
            'predictions': predictions,
            'recommendations': recommendations,
            'statistics': self._calculate_statistics(current_levels)
        }
    
    def _calculate_current_inventory_levels(self, individual: Dict[str, Any]) -> Dict[str, float]:
        """현재 컨테이너 재고 수준 계산"""
        # 최종 컨테이너 수준 계산
        final_levels = self.params.calculate_empty_container_levels(individual)
        
        # 항구별 평균 재고 수준
        port_levels = {}
        for p_idx, port in enumerate(self.params.P):
            # 최근 스케줄들의 평균 재고 수준
            recent_levels = final_levels[-min(5, len(final_levels)):, p_idx]
            port_levels[port] = np.mean(recent_levels) if len(recent_levels) > 0 else 0
            
        return port_levels
    
    def _update_adaptive_thresholds(self, current_levels: Dict[str, float], 
                                  timestamp: datetime):
        """동적 임계값 업데이트"""
        # 롤링 통계 계산
        if len(self.inventory_history) >= self.rolling_window:
            recent_data = []
            cutoff_time = timestamp - timedelta(days=self.rolling_window)
            
            for record in self.inventory_history:
                if record['timestamp'] >= cutoff_time:
                    recent_data.extend(record['levels'].values())
            
            if recent_data:
                mean_level = np.mean(recent_data)
                std_level = np.std(recent_data)
                
                # 적응적 임계값 계산
                self.adaptive_thresholds = {
                    'critical_shortage': max(mean_level - 2 * std_level, 0),
                    'shortage': mean_level - std_level,
                    'normal_low': mean_level - 0.5 * std_level,
                    'normal_high': mean_level + 0.5 * std_level,
                    'excess': mean_level + std_level,
                    'critical_excess': mean_level + 2 * std_level
                }
    
    def _analyze_imbalance_patterns(self, current_levels: Dict[str, float]) -> Dict[str, Any]:
        """불균형 패턴 분석"""
        all_levels = list(current_levels.values())
        
        if not all_levels:
            return {}
            
        mean_level = np.mean(all_levels)
        std_level = np.std(all_levels)
        
        # 불균형 지수 계산
        imbalance_index = std_level / mean_level if mean_level > 0 else 0
        
        # 항구 분류
        excess_ports = []
        shortage_ports = []
        critical_shortage_ports = []
        balanced_ports = []
        
        # 적응적 임계값 사용 (없으면 기본 임계값)
        thresholds = self.adaptive_thresholds if self.adaptive_thresholds else {
            'critical_shortage': mean_level * self.critical_shortage_threshold,
            'shortage': mean_level * self.shortage_threshold,
            'excess': mean_level * self.excess_threshold,
            'critical_excess': mean_level * self.critical_excess_threshold
        }
        
        for port, level in current_levels.items():
            if level <= thresholds['critical_shortage']:
                critical_shortage_ports.append(port)
            elif level <= thresholds['shortage']:
                shortage_ports.append(port)
            elif level >= thresholds['critical_excess']:
                excess_ports.append(port)
            elif level >= thresholds['excess']:
                excess_ports.append(port)
            else:
                balanced_ports.append(port)
        
        return {
            'imbalance_index': imbalance_index,
            'mean_level': mean_level,
            'std_level': std_level,
            'excess_ports': excess_ports,
            'shortage_ports': shortage_ports,
            'critical_shortage_ports': critical_shortage_ports,
            'balanced_ports': balanced_ports,
            'total_excess': sum(current_levels[p] for p in excess_ports),
            'total_shortage': sum(thresholds['shortage'] - current_levels[p] 
                                for p in shortage_ports + critical_shortage_ports),
            'severity_score': self._calculate_severity_score(imbalance_index, 
                                                           len(critical_shortage_ports),
                                                           len(excess_ports))
        }
    
    def _calculate_severity_score(self, imbalance_index: float, 
                                critical_shortage_count: int, excess_count: int) -> int:
        """심각도 점수 계산 (1-5)"""
        score = 1
        
        # 불균형 지수 기반
        if imbalance_index > 0.8:
            score += 2
        elif imbalance_index > 0.5:
            score += 1
            
        # 중요 부족 항구 수
        if critical_shortage_count > 2:
            score += 2
        elif critical_shortage_count > 0:
            score += 1
            
        # 과잉 항구 수
        if excess_count > 3:
            score += 1
            
        return min(score, 5)
    
    def _generate_alerts(self, current_levels: Dict[str, float], 
                        imbalance_analysis: Dict[str, Any], 
                        timestamp: datetime) -> List[ImbalanceAlert]:
        """경고 생성"""
        alerts = []
        
        # 중요 부족 경고
        for port in imbalance_analysis.get('critical_shortage_ports', []):
            alerts.append(ImbalanceAlert(
                port=port,
                alert_type='critical_shortage',
                severity=5,
                current_level=current_levels[port],
                threshold_level=self.adaptive_thresholds.get('critical_shortage', 
                                                           imbalance_analysis['mean_level'] * self.critical_shortage_threshold),
                deviation=abs(current_levels[port] - imbalance_analysis['mean_level']),
                timestamp=timestamp,
                estimated_duration=self._estimate_duration(port, 'critical_shortage'),
                recommended_action=f"즉시 {port}로 빈 컨테이너 긴급 배송 필요"
            ))
        
        # 부족 경고
        for port in imbalance_analysis.get('shortage_ports', []):
            alerts.append(ImbalanceAlert(
                port=port,
                alert_type='shortage',
                severity=3,
                current_level=current_levels[port],
                threshold_level=self.adaptive_thresholds.get('shortage',
                                                           imbalance_analysis['mean_level'] * self.shortage_threshold),
                deviation=abs(current_levels[port] - imbalance_analysis['mean_level']),
                timestamp=timestamp,
                estimated_duration=self._estimate_duration(port, 'shortage'),
                recommended_action=f"{port}로 빈 컨테이너 배송 계획 수립"
            ))
        
        # 과잉 경고
        for port in imbalance_analysis.get('excess_ports', []):
            severity = 4 if current_levels[port] >= self.adaptive_thresholds.get('critical_excess', 
                                                                               imbalance_analysis['mean_level'] * self.critical_excess_threshold) else 2
            alerts.append(ImbalanceAlert(
                port=port,
                alert_type='excess',
                severity=severity,
                current_level=current_levels[port],
                threshold_level=self.adaptive_thresholds.get('excess',
                                                           imbalance_analysis['mean_level'] * self.excess_threshold),
                deviation=current_levels[port] - imbalance_analysis['mean_level'],
                timestamp=timestamp,
                estimated_duration=self._estimate_duration(port, 'excess'),
                recommended_action=f"{port}에서 빈 컨테이너 재배치 실행"
            ))
        
        return alerts
    
    def _estimate_duration(self, port: str, alert_type: str) -> int:
        """문제 지속 시간 추정"""
        # 단순 휴리스틱 - 실제로는 더 복잡한 예측 모델 사용
        base_duration = {
            'critical_shortage': 7,  # 1주일
            'shortage': 14,          # 2주일
            'excess': 21             # 3주일
        }
        
        return base_duration.get(alert_type, 14)
    
    def _predict_future_imbalance(self, current_levels: Dict[str, float], 
                                timestamp: datetime) -> Dict[str, Any]:
        """미래 불균형 예측"""
        predictions = {}
        
        # 단순 트렌드 기반 예측 (실제로는 ML 모델 사용)
        if len(self.inventory_history) >= 7:
            for port in self.params.P:
                recent_levels = []
                for record in self.inventory_history[-7:]:
                    if port in record['levels']:
                        recent_levels.append(record['levels'][port])
                
                if len(recent_levels) >= 3:
                    # 선형 트렌드 계산
                    x = np.arange(len(recent_levels))
                    trend = np.polyfit(x, recent_levels, 1)[0]
                    
                    # 미래 예측
                    future_levels = []
                    current_level = current_levels.get(port, 0)
                    for days_ahead in range(1, self.prediction_horizon + 1):
                        predicted_level = current_level + trend * days_ahead
                        future_levels.append(max(predicted_level, 0))  # 음수 방지
                    
                    predictions[port] = {
                        'trend': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable',
                        'trend_rate': abs(trend),
                        'future_levels': future_levels,
                        'risk_days': self._calculate_risk_days(future_levels, port)
                    }
        
        return predictions
    
    def _calculate_risk_days(self, future_levels: List[float], port: str) -> List[int]:
        """위험 일자 계산"""
        risk_days = []
        thresholds = self.adaptive_thresholds if self.adaptive_thresholds else {}
        
        critical_shortage = thresholds.get('critical_shortage', 100)
        excess = thresholds.get('excess', 2000)
        
        for day, level in enumerate(future_levels, 1):
            if level <= critical_shortage or level >= excess:
                risk_days.append(day)
        
        return risk_days
    
    def _generate_recommendations(self, alerts: List[ImbalanceAlert], 
                                predictions: Dict[str, Any]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        # 경고 기반 권장사항
        critical_alerts = [a for a in alerts if a.severity >= 4]
        if critical_alerts:
            recommendations.append("🚨 긴급: 중요 불균형 항구에 대한 즉시 대응 필요")
            for alert in critical_alerts[:3]:  # 상위 3개만
                recommendations.append(f"   • {alert.recommended_action}")
        
        # 예측 기반 권장사항
        high_risk_ports = []
        for port, pred in predictions.items():
            if pred.get('risk_days') and len(pred['risk_days']) >= 7:
                high_risk_ports.append(port)
        
        if high_risk_ports:
            recommendations.append(f"⚠️  예측: {', '.join(high_risk_ports)}에서 7일 이내 불균형 위험")
            recommendations.append("   • 사전 예방적 재배치 계획 수립 권장")
        
        # 전반적인 권장사항
        if len(alerts) > 5:
            recommendations.append("📋 전체적인 재배치 전략 재검토 필요")
        
        return recommendations
    
    def _calculate_statistics(self, current_levels: Dict[str, float]) -> Dict[str, Any]:
        """통계 계산"""
        all_levels = list(current_levels.values())
        
        if not all_levels:
            return {}
            
        return {
            'total_ports': len(all_levels),
            'mean_level': np.mean(all_levels),
            'median_level': np.median(all_levels),
            'std_level': np.std(all_levels),
            'min_level': np.min(all_levels),
            'max_level': np.max(all_levels),
            'cv': np.std(all_levels) / np.mean(all_levels) if np.mean(all_levels) > 0 else 0
        }
    
    def _update_history(self, current_levels: Dict[str, float], 
                       alerts: List[ImbalanceAlert], timestamp: datetime):
        """히스토리 업데이트"""
        # 재고 히스토리 추가
        self.inventory_history.append({
            'timestamp': timestamp,
            'levels': current_levels.copy()
        })
        
        # 경고 히스토리 추가
        self.alert_history.extend(alerts)
        
        # 오래된 데이터 정리 (30일 이상)
        cutoff_time = timestamp - timedelta(days=30)
        self.inventory_history = [
            record for record in self.inventory_history 
            if record['timestamp'] >= cutoff_time
        ]
        self.alert_history = [
            alert for alert in self.alert_history 
            if alert.timestamp >= cutoff_time
        ]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """경고 요약 정보"""
        if not self.alert_history:
            return {'total_alerts': 0, 'active_alerts': 0}
        
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        
        recent_alerts = [a for a in self.alert_history if a.timestamp >= recent_cutoff]
        
        return {
            'total_alerts': len(self.alert_history),
            'active_alerts': len(recent_alerts),
            'critical_alerts': len([a for a in recent_alerts if a.severity >= 4]),
            'alert_types': {
                alert_type: len([a for a in recent_alerts if a.alert_type == alert_type])
                for alert_type in ['critical_shortage', 'shortage', 'excess']
            },
            'most_problematic_ports': self._get_most_problematic_ports()
        }
    
    def _get_most_problematic_ports(self) -> List[str]:
        """가장 문제가 많은 항구 목록"""
        port_alert_counts = {}
        
        for alert in self.alert_history:
            port_alert_counts[alert.port] = port_alert_counts.get(alert.port, 0) + 1
        
        # 상위 5개 항구
        sorted_ports = sorted(port_alert_counts.items(), key=lambda x: x[1], reverse=True)
        return [port for port, count in sorted_ports[:5]]