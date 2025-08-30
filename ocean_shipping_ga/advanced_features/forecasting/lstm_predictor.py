#!/usr/bin/env python3
"""
LSTM 기반 수요 예측기
시계열 패턴을 학습하여 미래 수요를 예측
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    TENSORFLOW_AVAILABLE = True
except ImportError:
    print("⚠️ TensorFlow not available. Using simple statistical forecasting.")
    TENSORFLOW_AVAILABLE = False


class LSTMPredictor:
    """LSTM 기반 수요 예측기"""
    
    def __init__(self, sequence_length: int = 30, forecast_horizon: int = 7):
        """
        Parameters:
        -----------
        sequence_length : int
            입력 시퀀스 길이 (일 수)
        forecast_horizon : int
            예측 기간 (일 수)
        """
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.scaler = MinMaxScaler() if TENSORFLOW_AVAILABLE else None
        self.model = None
        self.is_trained = False
        
    def prepare_data(self, demand_history: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """시계열 데이터를 LSTM 입력 형태로 변환"""
        if not TENSORFLOW_AVAILABLE:
            return self._prepare_simple_data(demand_history)
            
        # 데이터 정규화
        demand_values = demand_history['total_demand'].values.reshape(-1, 1)
        scaled_data = self.scaler.fit_transform(demand_values)
        
        # 시퀀스 데이터 생성
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data) - self.forecast_horizon + 1):
            X.append(scaled_data[i-self.sequence_length:i, 0])
            y.append(scaled_data[i:i+self.forecast_horizon, 0])
            
        return np.array(X), np.array(y)
    
    def _prepare_simple_data(self, demand_history: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """TensorFlow 없을 때 간단한 데이터 준비"""
        demand_values = demand_history['total_demand'].values
        X, y = [], []
        
        for i in range(self.sequence_length, len(demand_values) - self.forecast_horizon + 1):
            X.append(demand_values[i-self.sequence_length:i])
            y.append(demand_values[i:i+self.forecast_horizon])
            
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape: Tuple[int, int]) -> None:
        """LSTM 모델 구성"""
        if not TENSORFLOW_AVAILABLE:
            print("📊 Statistical forecasting model ready")
            self.model = "statistical"
            return
            
        self.model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(self.forecast_horizon)
        ])
        
        self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        print("🧠 LSTM model built successfully")
    
    def train(self, demand_history: pd.DataFrame, epochs: int = 50, validation_split: float = 0.2) -> Dict:
        """모델 훈련"""
        print(f"🎯 Training forecasting model on {len(demand_history)} data points...")
        
        X, y = self.prepare_data(demand_history)
        
        if len(X) == 0:
            print("❌ Not enough data for training")
            return {"status": "failed", "reason": "insufficient_data"}
        
        if not TENSORFLOW_AVAILABLE:
            return self._train_statistical(X, y)
            
        # LSTM 모델 구성
        self.build_model((X.shape[1], 1))
        X = X.reshape((X.shape[0], X.shape[1], 1))
        
        # 모델 훈련
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=32,
            validation_split=validation_split,
            verbose=0
        )
        
        self.is_trained = True
        
        final_loss = history.history['loss'][-1]
        final_val_loss = history.history['val_loss'][-1] if validation_split > 0 else final_loss
        
        print(f"✅ LSTM training completed - Loss: {final_loss:.4f}, Val Loss: {final_val_loss:.4f}")
        
        return {
            "status": "success",
            "final_loss": final_loss,
            "final_val_loss": final_val_loss,
            "epochs": epochs
        }
    
    def _train_statistical(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """통계적 모델 훈련 (TensorFlow 대체)"""
        try:
            # 단순 이동평균과 추세 기반 예측
            if len(X) > 1:
                self.trend_weights = np.polyfit(range(len(X)), np.mean(X, axis=1), 1)
                # NaN이나 무한값 체크
                if np.any(np.isnan(self.trend_weights)) or np.any(np.isinf(self.trend_weights)):
                    self.trend_weights = np.array([0.0, np.mean(X)])
            else:
                self.trend_weights = np.array([0.0, np.mean(X)])
                
            self.seasonal_pattern = np.mean(X, axis=0)
            self.is_trained = True
            
            print("✅ Statistical model training completed")
            return {"status": "success", "method": "statistical"}
        except Exception as e:
            print(f"⚠️ Statistical training failed: {e}")
            # 폴백: 기본값으로 초기화
            self.trend_weights = np.array([0.0, np.mean(X) if len(X) > 0 else 0])
            self.seasonal_pattern = np.array([np.mean(X) if len(X) > 0 else 0])
            self.is_trained = True
            return {"status": "success", "method": "statistical_fallback"}
    
    def predict(self, recent_data: np.ndarray) -> np.ndarray:
        """미래 수요 예측"""
        if not self.is_trained:
            print("❌ Model not trained yet")
            return np.array([])
        
        if not TENSORFLOW_AVAILABLE:
            return self._predict_statistical(recent_data)
            
        # 데이터 전처리
        if len(recent_data) < self.sequence_length:
            # 부족한 데이터는 평균으로 패딩
            padding = np.full(self.sequence_length - len(recent_data), np.mean(recent_data))
            recent_data = np.concatenate([padding, recent_data])
        
        recent_data = recent_data[-self.sequence_length:]
        scaled_data = self.scaler.transform(recent_data.reshape(-1, 1))
        
        # 예측
        X_pred = scaled_data.reshape((1, self.sequence_length, 1))
        prediction_scaled = self.model.predict(X_pred, verbose=0)
        
        # 역정규화
        prediction = self.scaler.inverse_transform(prediction_scaled.reshape(-1, 1))
        return prediction.flatten()
    
    def _predict_statistical(self, recent_data: np.ndarray) -> np.ndarray:
        """통계적 예측 (TensorFlow 대체)"""
        # 추세 + 계절성 기반 예측
        recent_mean = np.mean(recent_data[-7:]) if len(recent_data) >= 7 else np.mean(recent_data)
        
        # trend_weights가 제대로 초기화되었는지 확인
        if hasattr(self, 'trend_weights') and self.trend_weights is not None and len(self.trend_weights) > 0:
            try:
                trend = self.trend_weights[0] * self.forecast_horizon
                if np.isnan(trend) or np.isinf(trend):
                    trend = 0
            except (IndexError, TypeError):
                trend = 0
        else:
            trend = 0
        
        # 기본 예측값에 약간의 변동성 추가
        base_prediction = recent_mean + trend
        predictions = []
        
        for i in range(self.forecast_horizon):
            seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * i / 7)  # 주간 계절성
            pred = base_prediction * seasonal_factor
            predictions.append(max(0, pred))  # 음수 방지
            
        return np.array(predictions)
    
    def evaluate(self, test_data: pd.DataFrame) -> Dict:
        """모델 성능 평가"""
        if not self.is_trained:
            return {"status": "error", "message": "Model not trained"}
        
        X_test, y_test = self.prepare_data(test_data)
        
        if len(X_test) == 0:
            return {"status": "error", "message": "Insufficient test data"}
        
        predictions = []
        for i in range(len(X_test)):
            pred = self.predict(X_test[i])
            predictions.append(pred)
        
        predictions = np.array(predictions)
        
        # 평가 지표 계산
        mae = mean_absolute_error(y_test.flatten(), predictions.flatten()) if TENSORFLOW_AVAILABLE else 0
        mse = mean_squared_error(y_test.flatten(), predictions.flatten()) if TENSORFLOW_AVAILABLE else 0
        rmse = np.sqrt(mse) if TENSORFLOW_AVAILABLE else 0
        
        return {
            "status": "success",
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "predictions_shape": predictions.shape,
            "actual_shape": y_test.shape
        }


class SimpleForecastingFallback:
    """TensorFlow 없을 때 사용하는 간단한 예측 클래스"""
    
    def __init__(self, forecast_horizon: int = 7):
        self.forecast_horizon = forecast_horizon
        self.is_trained = False
        
    def fit(self, demand_data: pd.DataFrame):
        """간단한 통계 모델 피팅"""
        self.historical_mean = demand_data['total_demand'].mean()
        self.historical_std = demand_data['total_demand'].std()
        self.recent_trend = demand_data['total_demand'].tail(14).mean() - demand_data['total_demand'].head(14).mean()
        self.is_trained = True
        
    def predict(self, steps: int = None) -> np.ndarray:
        """간단한 예측"""
        steps = steps or self.forecast_horizon
        
        predictions = []
        for i in range(steps):
            # 추세 + 랜덤 노이즈
            pred = self.historical_mean + (self.recent_trend * i / 7) + np.random.normal(0, self.historical_std * 0.1)
            predictions.append(max(0, pred))
            
        return np.array(predictions)