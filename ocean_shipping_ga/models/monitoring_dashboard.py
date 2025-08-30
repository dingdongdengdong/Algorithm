"""
실시간 재고 모니터링 대시보드
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

from .dynamic_imbalance_detector import DynamicImbalanceDetector, ImbalanceAlert
from .auto_redistribution_trigger import AutoRedistributionTrigger, TriggerEvent
from config import get_constant


@dataclass
class DashboardMetrics:
    """대시보드 메트릭 데이터"""
    timestamp: datetime
    total_containers: int
    balanced_ports: int
    excess_ports: int
    shortage_ports: int
    critical_alerts: int
    imbalance_index: float
    redistribution_cost: float
    efficiency_score: float


class RealTimeMonitoringDashboard:
    """
    실시간 컨테이너 재고 모니터링 대시보드
    """
    
    def __init__(self, params, imbalance_detector: DynamicImbalanceDetector,
                 auto_trigger: AutoRedistributionTrigger):
        self.params = params
        self.imbalance_detector = imbalance_detector
        self.auto_trigger = auto_trigger
        
        # 대시보드 설정 (설정 파일에서 로드)
        self.refresh_interval = get_constant('monitoring.refresh_interval', 30)  # 30초마다 업데이트
        self.history_retention_days = 7
        self.max_display_points = get_constant('monitoring.max_display_points', 288)  # 24시간 * 12 (5분 간격)
        
        # 데이터 저장
        self.metrics_history = []
        self.current_snapshot = None
        self.dashboard_config = self._load_dashboard_config()
        
        # 시각화 설정
        plt.style.use('default')
        self.color_scheme = {
            'critical': '#FF4444',
            'warning': '#FFA500', 
            'normal': '#00AA44',
            'info': '#4488FF',
            'background': '#F5F5F5',
            'grid': '#E0E0E0'
        }
        
    def _load_dashboard_config(self) -> Dict[str, Any]:
        """대시보드 설정 로드"""
        return {
            'port_display_limit': 10,
            'alert_display_limit': 20,
            'chart_update_interval': 5,  # 5초
            'auto_refresh': True,
            'show_predictions': True,
            'show_redistributions': True,
            'theme': 'light'
        }
    
    def update_dashboard_data(self, individual: Dict[str, Any], 
                            current_timestamp: datetime = None) -> Dict[str, Any]:
        """대시보드 데이터 업데이트"""
        if current_timestamp is None:
            current_timestamp = datetime.now()
        
        # 불균형 감지 실행
        imbalance_report = self.imbalance_detector.detect_real_time_imbalance(
            individual, current_timestamp
        )
        
        # 자동 트리거 상태 확인
        trigger_status = self.auto_trigger.get_trigger_status()
        
        # 메트릭 계산
        metrics = self._calculate_dashboard_metrics(
            imbalance_report, trigger_status, current_timestamp
        )
        
        # 현재 스냅샷 업데이트
        self.current_snapshot = {
            'timestamp': current_timestamp,
            'imbalance_report': imbalance_report,
            'trigger_status': trigger_status,
            'metrics': metrics,
            'individual': individual
        }
        
        # 히스토리 업데이트
        self.metrics_history.append(metrics)
        self._cleanup_old_data(current_timestamp)
        
        return self.current_snapshot
    
    def _calculate_dashboard_metrics(self, imbalance_report: Dict[str, Any], 
                                   trigger_status: Dict[str, Any],
                                   timestamp: datetime) -> DashboardMetrics:
        """대시보드 메트릭 계산"""
        imbalance_analysis = imbalance_report.get('imbalance_analysis', {})
        alerts = imbalance_report.get('alerts', [])
        current_levels = imbalance_report.get('current_levels', {})
        
        # 기본 메트릭
        total_containers = sum(current_levels.values())
        balanced_ports = len(imbalance_analysis.get('balanced_ports', []))
        excess_ports = len(imbalance_analysis.get('excess_ports', []))
        shortage_ports = len(imbalance_analysis.get('shortage_ports', []) + 
                           imbalance_analysis.get('critical_shortage_ports', []))
        critical_alerts = len([a for a in alerts if a.severity >= 4])
        imbalance_index = imbalance_analysis.get('imbalance_index', 0)
        
        # 재배치 비용 추정
        redistribution_cost = self._estimate_redistribution_cost(imbalance_analysis)
        
        # 효율성 점수 계산 (0-100)
        efficiency_score = self._calculate_efficiency_score(
            imbalance_analysis, alerts, trigger_status
        )
        
        return DashboardMetrics(
            timestamp=timestamp,
            total_containers=int(total_containers),
            balanced_ports=balanced_ports,
            excess_ports=excess_ports,
            shortage_ports=shortage_ports,
            critical_alerts=critical_alerts,
            imbalance_index=imbalance_index,
            redistribution_cost=redistribution_cost,
            efficiency_score=efficiency_score
        )
    
    def _estimate_redistribution_cost(self, imbalance_analysis: Dict[str, Any]) -> float:
        """재배치 비용 추정"""
        total_excess = imbalance_analysis.get('total_excess', 0)
        total_shortage = imbalance_analysis.get('total_shortage', 0)
        
        # 단순 비용 추정 (실제로는 더 복잡한 계산)
        redistribution_amount = min(total_excess, total_shortage)
        average_cost_per_teu = get_constant('costs.display.average_cost_per_teu', 150)  # USD per TEU
        
        return redistribution_amount * average_cost_per_teu
    
    def _calculate_efficiency_score(self, imbalance_analysis: Dict[str, Any], 
                                  alerts: List[ImbalanceAlert],
                                  trigger_status: Dict[str, Any]) -> float:
        """효율성 점수 계산 (0-100)"""
        base_score = 100
        
        # 불균형 지수로 인한 감점
        imbalance_index = imbalance_analysis.get('imbalance_index', 0)
        base_score -= min(imbalance_index * 30, 40)
        
        # 알림으로 인한 감점
        critical_alerts = len([a for a in alerts if a.severity >= 4])
        warning_alerts = len([a for a in alerts if a.severity == 3])
        base_score -= critical_alerts * 10 + warning_alerts * 5
        
        # 트리거 실패로 인한 감점
        failed_triggers = trigger_status.get('failed_triggers', 0)
        base_score -= failed_triggers * 5
        
        return max(0, min(100, base_score))
    
    def _cleanup_old_data(self, current_timestamp: datetime):
        """오래된 데이터 정리"""
        cutoff_time = current_timestamp - timedelta(days=self.history_retention_days)
        
        # 메트릭 히스토리 정리
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        # 최대 표시 포인트 제한
        if len(self.metrics_history) > self.max_display_points:
            self.metrics_history = self.metrics_history[-self.max_display_points:]
    
    def generate_console_dashboard(self) -> str:
        """콘솔용 대시보드 생성"""
        if not self.current_snapshot:
            return "대시보드 데이터 없음"
        
        snapshot = self.current_snapshot
        metrics = snapshot['metrics']
        imbalance_report = snapshot['imbalance_report']
        trigger_status = snapshot['trigger_status']
        
        # 헤더
        dashboard_text = []
        dashboard_text.append("=" * 80)
        dashboard_text.append("🖥️  OCEAN SHIPPING GA - 실시간 모니터링 대시보드")
        dashboard_text.append("=" * 80)
        dashboard_text.append(f"⏰ 업데이트: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        dashboard_text.append("")
        
        # 주요 메트릭
        dashboard_text.append("📊 주요 지표")
        dashboard_text.append("-" * 40)
        dashboard_text.append(f"총 컨테이너:     {metrics.total_containers:,} TEU")
        dashboard_text.append(f"균형 항구:       {metrics.balanced_ports}개")
        dashboard_text.append(f"과잉 항구:       {metrics.excess_ports}개")
        dashboard_text.append(f"부족 항구:       {metrics.shortage_ports}개")
        dashboard_text.append(f"불균형 지수:     {metrics.imbalance_index:.3f}")
        dashboard_text.append(f"효율성 점수:     {metrics.efficiency_score:.1f}/100")
        dashboard_text.append("")
        
        # 알림 상태
        alerts = imbalance_report.get('alerts', [])
        critical_alerts = [a for a in alerts if a.severity >= 4]
        warning_alerts = [a for a in alerts if a.severity == 3]
        
        status_icon = "🟢" if not alerts else "🟡" if not critical_alerts else "🔴"
        dashboard_text.append(f"{status_icon} 알림 상태")
        dashboard_text.append("-" * 40)
        dashboard_text.append(f"중요 알림:       {len(critical_alerts)}건")
        dashboard_text.append(f"경고 알림:       {len(warning_alerts)}건")
        dashboard_text.append(f"총 알림:         {len(alerts)}건")
        
        # 최신 알림 표시
        if alerts:
            dashboard_text.append("")
            dashboard_text.append("🚨 최신 알림 (최대 5건)")
            dashboard_text.append("-" * 40)
            for alert in sorted(alerts, key=lambda x: x.severity, reverse=True)[:5]:
                severity_icon = "🔴" if alert.severity >= 4 else "🟡" if alert.severity == 3 else "🟢"
                dashboard_text.append(
                    f"{severity_icon} {alert.port}: {alert.alert_type} "
                    f"(레벨: {alert.current_level:.0f}, 심각도: {alert.severity})"
                )
        
        # 자동 트리거 상태
        dashboard_text.append("")
        auto_icon = "🤖" if trigger_status.get('auto_execution_enabled') else "⏸️"
        dashboard_text.append(f"{auto_icon} 자동 트리거 시스템")
        dashboard_text.append("-" * 40)
        dashboard_text.append(f"자동 실행:       {'활성화' if trigger_status.get('auto_execution_enabled') else '비활성화'}")
        dashboard_text.append(f"최근 트리거:     {trigger_status.get('recent_triggers', 0)}건")
        dashboard_text.append(f"성공률:         {self._calculate_trigger_success_rate(trigger_status):.1f}%")
        
        # 항구별 상태
        current_levels = imbalance_report.get('current_levels', {})
        if current_levels:
            dashboard_text.append("")
            dashboard_text.append("🏢 항구별 재고 상태 (상위 10개)")
            dashboard_text.append("-" * 40)
            
            # 재고 수준순으로 정렬
            sorted_ports = sorted(current_levels.items(), key=lambda x: x[1], reverse=True)
            for port, level in sorted_ports[:10]:
                status = self._get_port_status_icon(port, imbalance_report)
                dashboard_text.append(f"{status} {port:15s}: {level:8.0f} TEU")
        
        # 재배치 정보
        if metrics.redistribution_cost > 0:
            dashboard_text.append("")
            dashboard_text.append("🔄 재배치 정보")
            dashboard_text.append("-" * 40)
            dashboard_text.append(f"예상 비용:       ${metrics.redistribution_cost:,.0f}")
            dashboard_text.append(f"예상 절약:       ${self._estimate_cost_savings():.0f}")
        
        # 추천 사항
        recommendations = imbalance_report.get('recommendations', [])
        if recommendations:
            dashboard_text.append("")
            dashboard_text.append("💡 추천 사항")
            dashboard_text.append("-" * 40)
            for i, rec in enumerate(recommendations[:5], 1):
                dashboard_text.append(f"{i}. {rec}")
        
        dashboard_text.append("")
        dashboard_text.append("=" * 80)
        
        return "\n".join(dashboard_text)
    
    def _calculate_trigger_success_rate(self, trigger_status: Dict[str, Any]) -> float:
        """트리거 성공률 계산"""
        successful = trigger_status.get('successful_triggers', 0)
        failed = trigger_status.get('failed_triggers', 0)
        total = successful + failed
        
        return (successful / total * 100) if total > 0 else 100
    
    def _get_port_status_icon(self, port: str, imbalance_report: Dict[str, Any]) -> str:
        """항구 상태 아이콘"""
        imbalance_analysis = imbalance_report.get('imbalance_analysis', {})
        
        if port in imbalance_analysis.get('critical_shortage_ports', []):
            return "🔴"
        elif port in imbalance_analysis.get('shortage_ports', []):
            return "🟡"
        elif port in imbalance_analysis.get('excess_ports', []):
            return "🟠"
        else:
            return "🟢"
    
    def _estimate_cost_savings(self) -> float:
        """비용 절약 추정"""
        # 단순 추정 - 실제로는 더 정교한 계산 필요
        if not self.current_snapshot:
            return 0
        
        metrics = self.current_snapshot['metrics']
        return metrics.redistribution_cost * 0.15  # 15% 절약 추정
    
    def create_trend_chart(self, metric: str = 'imbalance_index', 
                          hours: int = 24) -> Optional[plt.Figure]:
        """트렌드 차트 생성"""
        if len(self.metrics_history) < 2:
            return None
        
        # 데이터 준비
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return None
        
        timestamps = [m.timestamp for m in recent_metrics]
        values = [getattr(m, metric) for m in recent_metrics]
        
        # 차트 생성
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(timestamps, values, linewidth=2, color=self.color_scheme['info'])
        ax.fill_between(timestamps, values, alpha=0.3, color=self.color_scheme['info'])
        
        # 차트 설정
        ax.set_title(f'{metric.replace("_", " ").title()} - 최근 {hours}시간', fontsize=14, fontweight='bold')
        ax.set_xlabel('시간')
        ax.set_ylabel(metric.replace('_', ' ').title())
        ax.grid(True, alpha=0.3)
        
        # 시간 축 포맷팅
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours//12)))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # 임계값 표시 (메트릭에 따라)
        if metric == 'imbalance_index':
            ax.axhline(y=0.5, color=self.color_scheme['warning'], linestyle='--', alpha=0.7, label='경고 수준')
            ax.axhline(y=0.8, color=self.color_scheme['critical'], linestyle='--', alpha=0.7, label='위험 수준')
            ax.legend()
        elif metric == 'efficiency_score':
            ax.axhline(y=80, color=self.color_scheme['warning'], linestyle='--', alpha=0.7, label='목표 수준')
            ax.axhline(y=60, color=self.color_scheme['critical'], linestyle='--', alpha=0.7, label='최소 수준')
            ax.legend()
        
        plt.tight_layout()
        return fig
    
    def create_port_status_chart(self) -> Optional[plt.Figure]:
        """항구 상태 차트 생성"""
        if not self.current_snapshot:
            return None
        
        current_levels = self.current_snapshot['imbalance_report'].get('current_levels', {})
        if not current_levels:
            return None
        
        # 데이터 준비 (상위 15개 항구)
        sorted_ports = sorted(current_levels.items(), key=lambda x: x[1], reverse=True)[:15]
        ports = [p[0] for p in sorted_ports]
        levels = [p[1] for p in sorted_ports]
        
        # 항구별 색상 결정
        imbalance_analysis = self.current_snapshot['imbalance_report'].get('imbalance_analysis', {})
        colors = []
        for port in ports:
            if port in imbalance_analysis.get('critical_shortage_ports', []):
                colors.append(self.color_scheme['critical'])
            elif port in imbalance_analysis.get('shortage_ports', []):
                colors.append(self.color_scheme['warning'])
            elif port in imbalance_analysis.get('excess_ports', []):
                colors.append('#FFA500')
            else:
                colors.append(self.color_scheme['normal'])
        
        # 차트 생성
        fig, ax = plt.subplots(figsize=(14, 8))
        bars = ax.bar(ports, levels, color=colors)
        
        # 차트 설정
        ax.set_title('항구별 컨테이너 재고 현황', fontsize=14, fontweight='bold')
        ax.set_xlabel('항구')
        ax.set_ylabel('컨테이너 수량 (TEU)')
        ax.grid(True, alpha=0.3, axis='y')
        
        # x축 레이블 회전
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 범례 추가
        legend_elements = [
            plt.Rectangle((0,0),1,1, facecolor=self.color_scheme['critical'], label='심각한 부족'),
            plt.Rectangle((0,0),1,1, facecolor=self.color_scheme['warning'], label='부족'),
            plt.Rectangle((0,0),1,1, facecolor='#FFA500', label='과잉'),
            plt.Rectangle((0,0),1,1, facecolor=self.color_scheme['normal'], label='균형')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        # 값 표시
        for bar, level in zip(bars, levels):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                   f'{int(level):,}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        return fig
    
    def create_alert_timeline(self, hours: int = 48) -> Optional[plt.Figure]:
        """알림 타임라인 차트 생성"""
        # 알림 히스토리 수집
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_alerts = []
        
        for alert in self.imbalance_detector.alert_history:
            if alert.timestamp >= cutoff_time:
                recent_alerts.append(alert)
        
        if not recent_alerts:
            return None
        
        # 데이터 준비
        timestamps = [a.timestamp for a in recent_alerts]
        severities = [a.severity for a in recent_alerts]
        ports = [a.port for a in recent_alerts]
        
        # 차트 생성
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # 심각도별 색상 매핑
        colors = [self.color_scheme['critical'] if s >= 4 else 
                 self.color_scheme['warning'] if s == 3 else 
                 self.color_scheme['info'] for s in severities]
        
        # 스캐터 플롯
        scatter = ax.scatter(timestamps, severities, c=colors, s=100, alpha=0.7)
        
        # 차트 설정
        ax.set_title(f'알림 발생 현황 - 최근 {hours}시간', fontsize=14, fontweight='bold')
        ax.set_xlabel('시간')
        ax.set_ylabel('심각도')
        ax.set_ylim(0, 6)
        ax.grid(True, alpha=0.3)
        
        # 시간 축 포맷팅
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=max(1, hours//12)))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # 심각도 수준 표시
        ax.axhline(y=4, color=self.color_scheme['critical'], linestyle='--', alpha=0.5, label='중요 수준')
        ax.axhline(y=3, color=self.color_scheme['warning'], linestyle='--', alpha=0.5, label='경고 수준')
        ax.legend()
        
        plt.tight_layout()
        return fig
    
    def export_dashboard_data(self, file_path: str = None) -> str:
        """대시보드 데이터 내보내기"""
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = f"dashboard_export_{timestamp}.json"
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'current_snapshot': self._serialize_snapshot(self.current_snapshot) if self.current_snapshot else None,
            'metrics_history': [self._serialize_metrics(m) for m in self.metrics_history[-100:]],
            'dashboard_config': self.dashboard_config,
            'alert_summary': self.imbalance_detector.get_alert_summary()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return file_path
    
    def _serialize_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """스냅샷 직렬화"""
        if not snapshot:
            return {}
        
        return {
            'timestamp': snapshot['timestamp'].isoformat(),
            'metrics': self._serialize_metrics(snapshot['metrics']),
            'alert_count': len(snapshot['imbalance_report'].get('alerts', [])),
            'imbalance_index': snapshot['imbalance_report'].get('imbalance_analysis', {}).get('imbalance_index', 0),
            'trigger_status': snapshot['trigger_status']
        }
    
    def _serialize_metrics(self, metrics: DashboardMetrics) -> Dict[str, Any]:
        """메트릭 직렬화"""
        return {
            'timestamp': metrics.timestamp.isoformat(),
            'total_containers': metrics.total_containers,
            'balanced_ports': metrics.balanced_ports,
            'excess_ports': metrics.excess_ports,
            'shortage_ports': metrics.shortage_ports,
            'critical_alerts': metrics.critical_alerts,
            'imbalance_index': metrics.imbalance_index,
            'redistribution_cost': metrics.redistribution_cost,
            'efficiency_score': metrics.efficiency_score
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """대시보드 요약 정보"""
        if not self.current_snapshot:
            return {'status': 'no_data'}
        
        metrics = self.current_snapshot['metrics']
        alerts = self.current_snapshot['imbalance_report'].get('alerts', [])
        
        return {
            'status': 'active',
            'last_update': metrics.timestamp.isoformat(),
            'efficiency_score': metrics.efficiency_score,
            'total_ports': len(self.current_snapshot['imbalance_report'].get('current_levels', {})),
            'alert_summary': {
                'total': len(alerts),
                'critical': len([a for a in alerts if a.severity >= 4]),
                'warning': len([a for a in alerts if a.severity == 3])
            },
            'imbalance_status': {
                'index': metrics.imbalance_index,
                'balanced_ports': metrics.balanced_ports,
                'problematic_ports': metrics.excess_ports + metrics.shortage_ports
            },
            'auto_trigger_enabled': self.current_snapshot['trigger_status'].get('auto_execution_enabled', False)
        }