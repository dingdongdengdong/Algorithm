#!/usr/bin/env python3
"""
해상 운송 수요 예측 통합 시스템
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.data_loader import DataLoader
from models.parameters import GAParameters
from config import get_constant
from .lstm_predictor import LSTMPredictor, SimpleForecastingFallback


class DemandForecaster:
    """해상 운송 수요 예측 시스템"""
    
    def __init__(self, data_loader: DataLoader, forecast_days: int = 30):
        """
        Parameters:
        -----------
        data_loader : DataLoader
            데이터 로더 인스턴스
        forecast_days : int
            예측 기간 (일)
        """
        self.data_loader = data_loader
        self.forecast_days = forecast_days
        self.lstm_predictor = LSTMPredictor(forecast_horizon=forecast_days)
        self.fallback_predictor = SimpleForecastingFallback(forecast_horizon=forecast_days)
        
        # 데이터 준비
        self.schedule_data = data_loader.get_schedule_data()
        self.historical_demand = None
        self.route_predictors = {}
        
    def prepare_historical_demand(self) -> pd.DataFrame:
        """과거 수요 데이터 준비"""
        print("📊 Preparing historical demand data...")
        
        # 스케줄 데이터에서 일별 수요 집계
        schedule_data = self.schedule_data.copy()
        schedule_data['ETD_date'] = pd.to_datetime(schedule_data['ETD']).dt.date
        
        # 일별 총 수요량 계산 (TEU 단위)
        daily_demand = schedule_data.groupby('ETD_date').agg({
            '주문량(KG)': 'sum',
            '스케줄 번호': 'count'
        }).reset_index()
        
        daily_demand.columns = ['date', 'total_demand_kg', 'schedule_count']
        daily_demand['total_demand'] = daily_demand['total_demand_kg'] / 30000  # TEU 변환
        
        # 날짜 인덱스로 변환
        daily_demand['date'] = pd.to_datetime(daily_demand['date'])
        daily_demand = daily_demand.set_index('date').sort_index()
        
        # 누락된 날짜 보간 - 0이 아닌 값으로 보간
        date_range = pd.date_range(
            start=daily_demand.index.min(),
            end=daily_demand.index.max(),
            freq='D'
        )
        
        # 0이 아닌 값들만 사용하여 보간
        non_zero_demand = daily_demand[daily_demand['total_demand'] > 0]
        if len(non_zero_demand) > 0:
            # 이동평균을 사용하여 보간
            daily_demand = daily_demand.reindex(date_range)
            
            # 0인 값들을 이전/이후 값의 평균으로 보간
            for i, date in enumerate(daily_demand.index):
                if daily_demand.loc[date, 'total_demand'] == 0:
                    # 이전 7일과 이후 7일의 평균 계산
                    prev_dates = daily_demand.index[max(0, i-7):i]
                    next_dates = daily_demand.index[i+1:min(len(daily_demand), i+8)]
                    
                    prev_values = daily_demand.loc[prev_dates, 'total_demand']
                    next_values = daily_demand.loc[next_dates, 'total_demand']
                    
                    # 0이 아닌 값들만 사용
                    valid_values = pd.concat([prev_values, next_values])
                    valid_values = valid_values[valid_values > 0]
                    
                    if len(valid_values) > 0:
                        daily_demand.loc[date, 'total_demand'] = valid_values.mean()
                    else:
                        # 유효한 값이 없으면 전체 평균 사용
                        daily_demand.loc[date, 'total_demand'] = non_zero_demand['total_demand'].mean()
        else:
            # 모든 값이 0인 경우 기본값 설정
            daily_demand = daily_demand.reindex(date_range, fill_value=1000)  # 기본값 1000 TEU
        
        daily_demand.index.name = 'date'
        
        print(f"✅ Historical demand prepared: {len(daily_demand)} days")
        print(f"   - Average daily demand: {daily_demand['total_demand'].mean():.1f} TEU")
        print(f"   - Peak demand: {daily_demand['total_demand'].max():.1f} TEU")
        print(f"   - Non-zero days: {len(daily_demand[daily_demand['total_demand'] > 0])} days")
        
        self.historical_demand = daily_demand
        return daily_demand
    
    def train_global_predictor(self) -> Dict:
        """전체 수요 예측 모델 훈련"""
        if self.historical_demand is None:
            self.prepare_historical_demand()
        
        print("🎯 Training global demand predictor...")
        
        # LSTM 모델 훈련 시도
        try:
            result = self.lstm_predictor.train(
                self.historical_demand.reset_index(),
                epochs=30,
                validation_split=0.2
            )
            
            if result["status"] == "success":
                print("✅ LSTM global predictor trained successfully")
                return result
                
        except Exception as e:
            print(f"⚠️ LSTM training failed: {e}")
        
        # 폴백 모델 훈련
        print("🔄 Using fallback statistical predictor...")
        self.fallback_predictor.fit(self.historical_demand.reset_index())
        
        return {"status": "success", "method": "fallback"}
    
    def train_route_predictors(self) -> Dict[str, Dict]:
        """루트별 수요 예측 모델 훈련"""
        print("🛤️ Training route-specific predictors...")
        
        route_results = {}
        
        # 루트별 수요 데이터 준비
        for route in self.schedule_data['루트번호'].unique():
            route_data = self.schedule_data[
                self.schedule_data['루트번호'] == route
            ].copy()
            
            if len(route_data) < 10:  # 데이터가 너무 적으면 스킵
                continue
            
            # 루트별 일별 수요 집계
            route_data['ETD_date'] = pd.to_datetime(route_data['ETD']).dt.date
            route_daily = route_data.groupby('ETD_date')['주문량(KG)'].sum().reset_index()
            route_daily.columns = ['date', 'total_demand']
            route_daily['total_demand'] = route_daily['total_demand'] / 30000  # TEU
            
            if len(route_daily) >= 20:  # 충분한 데이터가 있는 경우만
                try:
                    predictor = LSTMPredictor(forecast_horizon=self.forecast_days)
                    result = predictor.train(route_daily, epochs=20)
                    
                    if result["status"] == "success":
                        self.route_predictors[route] = predictor
                        route_results[route] = result
                        
                except Exception as e:
                    print(f"⚠️ Route {route} predictor failed: {e}")
        
        print(f"✅ Trained {len(self.route_predictors)} route-specific predictors")
        return route_results
    
    def predict_future_demand(self, target_date: datetime = None) -> Dict:
        """미래 수요 예측"""
        if target_date is None:
            target_date = datetime.now()
        
        print(f"🔮 Predicting demand for {self.forecast_days} days from {target_date.date()}")
        
        # 전체 수요 예측
        if self.historical_demand is None:
            self.prepare_historical_demand()
        
        recent_demand = self.historical_demand['total_demand'].tail(30).values
        
        # NaN 값 체크 및 처리
        if np.any(np.isnan(recent_demand)):
            print(f"   ⚠️ Found {np.sum(np.isnan(recent_demand))} NaN values, replacing with mean")
            recent_mean = np.nanmean(recent_demand)
            recent_demand = np.nan_to_num(recent_demand, nan=recent_mean)
        
        try:
            if self.lstm_predictor.is_trained:
                global_forecast = self.lstm_predictor.predict(recent_demand)
            else:
                global_forecast = self.fallback_predictor.predict(self.forecast_days)
        except Exception as e:
            print(f"⚠️ Global prediction failed: {e}")
            recent_mean = recent_demand.mean()
            if np.isnan(recent_mean):
                recent_mean = get_constant('forecasting.demand.recent_mean_default', 1000)  # 기본값
            global_forecast = np.full(self.forecast_days, recent_mean)
        
        # 루트별 예측
        route_forecasts = {}
        for route, predictor in self.route_predictors.items():
            try:
                route_data = self.schedule_data[
                    self.schedule_data['루트번호'] == route
                ]['주문량(KG)'].tail(30).values / 30000
                
                route_forecasts[route] = predictor.predict(route_data)
            except Exception as e:
                print(f"⚠️ Route {route} prediction failed: {e}")
        
        # 날짜별 예측 결과 구성
        forecast_dates = [
            target_date + timedelta(days=i) 
            for i in range(self.forecast_days)
        ]
        
        forecast_df = pd.DataFrame({
            'date': forecast_dates,
            'predicted_demand_teu': global_forecast,
            'confidence_interval_lower': global_forecast * 0.8,
            'confidence_interval_upper': global_forecast * 1.2
        })
        
        return {
            'global_forecast': forecast_df,
            'route_forecasts': route_forecasts,
            'forecast_horizon_days': self.forecast_days,
            'prediction_date': target_date
        }
    
    def evaluate_predictions(self, test_start_date: datetime, test_days: int = 14) -> Dict:
        """예측 성능 평가"""
        print(f"📈 Evaluating prediction accuracy for {test_days} days...")
        
        # 테스트 데이터 준비
        test_end_date = test_start_date + timedelta(days=test_days)
        
        test_data = self.historical_demand[
            (self.historical_demand.index >= test_start_date) &
            (self.historical_demand.index < test_end_date)
        ]
        
        if len(test_data) == 0:
            return {"status": "error", "message": "No test data available"}
        
        # 예측 수행 (테스트 시작일 이전 데이터로)
        train_data = self.historical_demand[
            self.historical_demand.index < test_start_date
        ]
        
        recent_data = train_data['total_demand'].tail(30).values
        
        try:
            if self.lstm_predictor.is_trained:
                predictions = self.lstm_predictor.predict(recent_data)
            else:
                predictions = self.fallback_predictor.predict(test_days)
        except Exception as e:
            print(f"⚠️ Prediction evaluation failed: {e}")
            return {"status": "error", "message": str(e)}
        
        # 실제값과 비교
        actual_values = test_data['total_demand'].values[:len(predictions)]
        
        if len(actual_values) == 0:
            return {"status": "error", "message": "No actual values to compare"}
        
        # 성능 지표 계산
        mae = np.mean(np.abs(predictions[:len(actual_values)] - actual_values))
        mse = np.mean((predictions[:len(actual_values)] - actual_values) ** 2)
        rmse = np.sqrt(mse)
        mape = np.mean(np.abs((actual_values - predictions[:len(actual_values)]) / actual_values)) * 100
        
        return {
            "status": "success",
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "mape": mape,
            "test_days": len(actual_values),
            "predictions": predictions[:len(actual_values)].tolist(),
            "actual_values": actual_values.tolist()
        }
    
    def generate_forecast_report(self, forecast_results: Dict) -> str:
        """예측 결과 리포트 생성"""
        report = []
        report.append("🔮 Ocean Shipping Demand Forecast Report")
        report.append("=" * 60)
        
        forecast_df = forecast_results['global_forecast']
        
        report.append(f"📅 Forecast Period: {forecast_results['forecast_horizon_days']} days")
        report.append(f"📊 Prediction Date: {forecast_results['prediction_date'].strftime('%Y-%m-%d')}")
        report.append("")
        
        report.append("📈 Global Demand Forecast:")
        report.append(f"   - Average Daily Demand: {forecast_df['predicted_demand_teu'].mean():.1f} TEU")
        report.append(f"   - Peak Demand: {forecast_df['predicted_demand_teu'].max():.1f} TEU")
        report.append(f"   - Minimum Demand: {forecast_df['predicted_demand_teu'].min():.1f} TEU")
        report.append("")
        
        # 주별 예측 요약
        forecast_df['week'] = pd.to_datetime(forecast_df['date']).dt.isocalendar().week
        weekly_avg = forecast_df.groupby('week')['predicted_demand_teu'].mean()
        
        report.append("📅 Weekly Forecast Summary:")
        for week, avg_demand in weekly_avg.items():
            report.append(f"   - Week {week}: {avg_demand:.1f} TEU/day")
        report.append("")
        
        # 루트별 예측 요약
        if forecast_results['route_forecasts']:
            report.append("🛤️ Route-Specific Forecasts:")
            for route, forecast in list(forecast_results['route_forecasts'].items())[:5]:
                avg_route_demand = np.mean(forecast)
                report.append(f"   - Route {route}: {avg_route_demand:.1f} TEU/day")
        
        return "\n".join(report)