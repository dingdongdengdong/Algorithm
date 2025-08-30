#!/usr/bin/env python3
"""
예측 결과를 GA 파라미터에 통합하는 모듈
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.parameters import GAParameters
from .demand_forecaster import DemandForecaster


class ForecastIntegrator:
    """예측 결과를 GA 최적화에 통합"""
    
    def __init__(self, ga_parameters: GAParameters, demand_forecaster: DemandForecaster):
        """
        Parameters:
        -----------
        ga_parameters : GAParameters
            GA 파라미터 인스턴스
        demand_forecaster : DemandForecaster
            수요 예측기 인스턴스
        """
        self.ga_params = ga_parameters
        self.forecaster = demand_forecaster
        self.original_demands = ga_parameters.D_ab.copy()
        self.forecast_results = None
        
    def update_demand_with_forecast(self, forecast_results: Dict, 
                                  integration_weight: float = 0.3) -> Dict:
        """
        예측 결과를 바탕으로 GA 수요 파라미터 업데이트
        
        Parameters:
        -----------
        forecast_results : Dict
            예측 결과
        integration_weight : float
            예측 통합 가중치 (0: 원본만 사용, 1: 예측만 사용)
        """
        print(f"🔄 Integrating forecast results with GA parameters (weight: {integration_weight})")
        
        self.forecast_results = forecast_results
        global_forecast = forecast_results['global_forecast']
        route_forecasts = forecast_results.get('route_forecasts', {})
        
        updated_demands = {}
        integration_stats = {
            'updated_routes': 0,
            'forecast_based_routes': 0,
            'original_routes': 0,
            'average_adjustment': 0
        }
        
        # 전체 수요 증감률 계산
        historical_avg = self.forecaster.historical_demand['total_demand'].mean()
        forecast_avg = global_forecast['predicted_demand_teu'].mean()
        global_adjustment = forecast_avg / historical_avg if historical_avg > 0 else 1.0
        
        adjustments = []
        
        for route, original_demand in self.original_demands.items():
            if route in route_forecasts:
                # 루트별 예측이 있는 경우
                route_forecast_avg = np.mean(route_forecasts[route])
                
                # 루트의 과거 평균 수요 계산
                route_schedule_data = self.ga_params.schedule_data[
                    self.ga_params.schedule_data['루트번호'] == route
                ]
                
                if not route_schedule_data.empty:
                    route_historical_avg = route_schedule_data['주문량(KG)'].mean() / 30000
                    route_adjustment = route_forecast_avg / route_historical_avg if route_historical_avg > 0 else 1.0
                else:
                    route_adjustment = global_adjustment
                
                # 가중 평균으로 조정
                final_adjustment = (
                    (1 - integration_weight) + 
                    integration_weight * route_adjustment
                )
                
                updated_demands[route] = max(1, int(original_demand * final_adjustment))
                integration_stats['forecast_based_routes'] += 1
                adjustments.append(final_adjustment)
                
            else:
                # 루트별 예측이 없으면 전역 조정 사용
                final_adjustment = (
                    (1 - integration_weight) + 
                    integration_weight * global_adjustment
                )
                
                updated_demands[route] = max(1, int(original_demand * final_adjustment))
                integration_stats['updated_routes'] += 1
                adjustments.append(final_adjustment)
        
        # 통계 업데이트
        integration_stats['average_adjustment'] = np.mean(adjustments) if adjustments else 1.0
        integration_stats['total_routes'] = len(updated_demands)
        
        # GA 파라미터 업데이트
        self.ga_params.D_ab = updated_demands
        
        print(f"✅ Demand integration completed:")
        print(f"   - Total routes updated: {integration_stats['total_routes']}")
        print(f"   - Routes with specific forecasts: {integration_stats['forecast_based_routes']}")
        print(f"   - Average demand adjustment: {integration_stats['average_adjustment']:.3f}")
        
        return integration_stats
    
    def create_dynamic_schedule_weights(self, forecast_results: Dict) -> Dict[int, float]:
        """
        예측 결과를 바탕으로 스케줄별 동적 가중치 생성
        수요가 높을 것으로 예상되는 시점의 스케줄에 높은 가중치 부여
        """
        print("⚖️ Creating dynamic schedule weights based on forecast...")
        
        global_forecast = forecast_results['global_forecast']
        schedule_weights = {}
        
        # 예측 기간 내 스케줄들에 대해 가중치 계산
        for i, schedule_id in enumerate(self.ga_params.I):
            schedule_etd = self.ga_params.ETD_i[schedule_id]
            
            # 스케줄 날짜와 가장 가까운 예측일 찾기
            forecast_dates = pd.to_datetime(global_forecast['date'])
            date_diffs = abs(forecast_dates - schedule_etd)
            closest_forecast_idx = date_diffs.idxmin()
            
            # 해당 날짜의 예측 수요
            predicted_demand = global_forecast.loc[closest_forecast_idx, 'predicted_demand_teu']
            avg_predicted_demand = global_forecast['predicted_demand_teu'].mean()
            
            # 평균 대비 수요 비율로 가중치 계산
            weight = predicted_demand / avg_predicted_demand if avg_predicted_demand > 0 else 1.0
            
            # 가중치 범위 제한 (0.5 ~ 2.0)
            weight = max(0.5, min(2.0, weight))
            
            schedule_weights[schedule_id] = weight
        
        print(f"✅ Dynamic weights created for {len(schedule_weights)} schedules")
        print(f"   - Weight range: {min(schedule_weights.values()):.3f} - {max(schedule_weights.values()):.3f}")
        
        return schedule_weights
    
    def adjust_capacity_constraints(self, forecast_results: Dict, 
                                  capacity_buffer: float = 0.1) -> Dict:
        """
        예측된 높은 수요 기간에 대해 용량 제약 조정
        """
        print(f"📦 Adjusting capacity constraints with {capacity_buffer:.0%} buffer for high-demand periods...")
        
        global_forecast = forecast_results['global_forecast']
        high_demand_threshold = global_forecast['predicted_demand_teu'].quantile(0.8)
        
        capacity_adjustments = {}
        adjusted_schedules = 0
        
        for i, schedule_id in enumerate(self.ga_params.I):
            schedule_etd = self.ga_params.ETD_i[schedule_id]
            
            # 스케줄 날짜의 예측 수요 확인
            forecast_dates = pd.to_datetime(global_forecast['date'])
            date_diffs = abs(forecast_dates - schedule_etd)
            closest_forecast_idx = date_diffs.idxmin()
            predicted_demand = global_forecast.loc[closest_forecast_idx, 'predicted_demand_teu']
            
            # 높은 수요가 예상되는 경우 용량 여유분 증가
            if predicted_demand > high_demand_threshold:
                schedule_route = None
                for route, route_schedules in self.ga_params.schedule_data.groupby('루트번호'):
                    if schedule_id in route_schedules['스케줄 번호'].values:
                        schedule_route = route
                        break
                
                if schedule_route and schedule_route in self.ga_params.CAP_v_r:
                    original_capacity = self.ga_params.CAP_v_r[schedule_route]
                    adjusted_capacity = int(original_capacity * (1 + capacity_buffer))
                    
                    capacity_adjustments[schedule_route] = {
                        'original': original_capacity,
                        'adjusted': adjusted_capacity,
                        'predicted_demand': predicted_demand
                    }
                    
                    self.ga_params.CAP_v_r[schedule_route] = adjusted_capacity
                    adjusted_schedules += 1
        
        print(f"✅ Capacity adjustments completed:")
        print(f"   - Schedules adjusted: {adjusted_schedules}")
        print(f"   - Routes with capacity increase: {len(capacity_adjustments)}")
        
        return capacity_adjustments
    
    def restore_original_parameters(self):
        """원래 GA 파라미터로 복원"""
        print("🔄 Restoring original GA parameters...")
        self.ga_params.D_ab = self.original_demands.copy()
        print("✅ Original parameters restored")
    
    def generate_integration_report(self, integration_stats: Dict, 
                                  schedule_weights: Dict, 
                                  capacity_adjustments: Dict) -> str:
        """통합 결과 리포트 생성"""
        report = []
        report.append("🔗 Forecast Integration Report")
        report.append("=" * 50)
        
        # 수요 조정 통계
        report.append("📊 Demand Adjustments:")
        report.append(f"   - Total routes: {integration_stats['total_routes']}")
        report.append(f"   - Routes with specific forecasts: {integration_stats['forecast_based_routes']}")
        report.append(f"   - Average adjustment factor: {integration_stats['average_adjustment']:.3f}")
        report.append("")
        
        # 스케줄 가중치 통계
        if schedule_weights:
            weights = list(schedule_weights.values())
            report.append("⚖️ Dynamic Schedule Weights:")
            report.append(f"   - Schedules weighted: {len(schedule_weights)}")
            report.append(f"   - Weight range: {min(weights):.3f} - {max(weights):.3f}")
            report.append(f"   - Average weight: {np.mean(weights):.3f}")
            report.append("")
        
        # 용량 조정 통계
        if capacity_adjustments:
            report.append("📦 Capacity Adjustments:")
            report.append(f"   - Routes adjusted: {len(capacity_adjustments)}")
            total_original = sum(adj['original'] for adj in capacity_adjustments.values())
            total_adjusted = sum(adj['adjusted'] for adj in capacity_adjustments.values())
            report.append(f"   - Total capacity increase: {total_adjusted - total_original} TEU")
            report.append("")
        
        # 예측 요약
        if self.forecast_results:
            forecast_df = self.forecast_results['global_forecast']
            report.append("🔮 Forecast Summary:")
            report.append(f"   - Forecast horizon: {len(forecast_df)} days")
            report.append(f"   - Average daily demand: {forecast_df['predicted_demand_teu'].mean():.1f} TEU")
            report.append(f"   - Peak demand: {forecast_df['predicted_demand_teu'].max():.1f} TEU")
        
        return "\n".join(report)