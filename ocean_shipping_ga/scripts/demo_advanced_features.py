#!/usr/bin/env python3
"""
고급 기능 데모 스크립트
각 고급 기능을 개별적으로 테스트하고 시연하는 Python 스크립트
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import argparse

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_loader import DataLoader
from models.parameters import GAParameters
from config import get_constant
from advanced_features.forecasting import DemandForecaster, ForecastIntegrator
from advanced_features.rolling_optimization import RollingOptimizer, TimeWindowManager
from advanced_features.adaptive_systems import AdaptiveGA, RealTimeMonitor, LearningSystem


def demo_demand_forecasting():
    """수요 예측 기능 데모"""
    print("🔮 Demand Forecasting Demo")
    print("=" * 50)
    
    try:
        # 데이터 로드
        print("📂 Loading data...")
        data_loader = DataLoader()
        
        # 수요 예측기 생성
        forecaster = DemandForecaster(data_loader, forecast_days=14)
        
        # 과거 데이터 준비
        print("📊 Preparing historical demand data...")
        historical_demand = forecaster.prepare_historical_demand()
        print(f"   - Historical data points: {len(historical_demand)}")
        
        # 예측 모델 훈련 (빠른 데모용)
        print("🎯 Training forecasting model...")
        training_result = forecaster.train_global_predictor()
        
        if training_result['status'] == 'success':
            print("✅ Model trained successfully")
            
            # 미래 수요 예측
            print("🔮 Generating forecast...")
            forecast_results = forecaster.predict_future_demand()
            
            # 결과 출력
            global_forecast = forecast_results['global_forecast']
            print(f"✅ Forecast generated for {len(global_forecast)} days")
            print(f"   - Average demand: {global_forecast['predicted_demand_teu'].mean():.1f} TEU/day")
            print(f"   - Peak demand: {global_forecast['predicted_demand_teu'].max():.1f} TEU")
            
            return forecast_results
        else:
            print(f"⚠️ Training status: {training_result['status']}")
            return None
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return None


def demo_rolling_optimization():
    """롤링 최적화 기능 데모"""
    print("\n🔄 Rolling Optimization Demo") 
    print("=" * 50)
    
    try:
        # 데이터 로드
        print("📂 Loading data...")
        data_loader = DataLoader()
        ga_params = GAParameters(data_loader, version='quick')
        
        # 롤링 최적화기 생성 (빠른 데모용)
        print("🔄 Creating rolling optimizer...")
        rolling_optimizer = RollingOptimizer(
            ga_params,
            window_size_days=20,  # 작은 윈도우로 빠른 테스트
            overlap_days=5,
            ga_generations=15     # 적은 세대로 빠른 실행
        )
        
        # 윈도우 정보 출력
        window_stats = rolling_optimizer.window_manager.get_window_stats()
        print(f"🪟 Window configuration:")
        print(f"   - Total windows: {window_stats['total_windows']}")
        print(f"   - Avg schedules/window: {window_stats['avg_schedules_per_window']:.1f}")
        
        # 첫 번째 윈도우만 최적화 (데모용)
        print("⚡ Running optimization for first window...")
        window_result = rolling_optimizer.optimize_single_window(0)
        
        if window_result['status'] == 'success':
            print(f"✅ Window optimization completed:")
            print(f"   - Final fitness: {window_result['final_fitness']:.2f}")
            print(f"   - Optimization time: {window_result['optimization_time']:.1f}s")
            print(f"   - Schedules optimized: {window_result['schedules_count']}")
            
            return window_result
        else:
            print(f"❌ Window optimization failed: {window_result.get('error', 'unknown')}")
            return None
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return None


def demo_adaptive_ga():
    """적응형 GA 기능 데모"""
    print("\n🧠 Adaptive GA System Demo")
    print("=" * 50)
    
    try:
        # 데이터 로드
        print("📂 Loading data...")
        data_loader = DataLoader()
        ga_params = GAParameters(data_loader, version='quick')
        
        # 적응형 GA 생성 (빠른 데모용 설정)
        print("🧠 Creating adaptive GA system...")
        adaptive_ga = AdaptiveGA(
            ga_params,
            adaptation_interval=30,  # 30초 간격으로 빠른 적응
            learning_enabled=True
        )
        
        # 초기 전략 설정
        adaptive_ga.change_adaptation_strategy('balanced')
        
        # 실시간 모니터링 시스템 테스트
        print("🔍 Testing real-time monitoring...")
        monitor_status = adaptive_ga.monitor.get_current_status()
        print(f"   - Monitoring system ready: {monitor_status}")
        
        # 짧은 시간 동안 적응형 모드 실행
        print("🔄 Starting adaptive mode for demo (30 seconds)...")
        adaptive_ga.start_adaptive_mode()
        
        # 30초 동안 상태 모니터링
        demo_duration = get_constant('performance.quick_test.demo_duration', 30)
        start_time = time.time()
        
        print(f"⏰ Running adaptive system for {demo_duration} seconds...")
        
        while time.time() - start_time < demo_duration:
            time.sleep(5)  # 5초마다 상태 체크
            
            current_status = adaptive_ga.get_adaptation_status()
            elapsed = int(time.time() - start_time)
            
            print(f"   [{elapsed:2d}s] Strategy: {current_status['current_strategy']}, "
                  f"Adaptations: {current_status['total_adaptations']}")
        
        # 적응형 모드 중지
        print("🛑 Stopping adaptive mode...")
        adaptive_ga.stop_adaptive_mode()
        
        # 최종 결과
        final_status = adaptive_ga.get_adaptation_status()
        print(f"✅ Adaptive GA demo completed:")
        print(f"   - Total adaptations: {final_status['total_adaptations']}")
        print(f"   - Successful adaptations: {final_status['successful_adaptations']}")
        print(f"   - Final strategy: {final_status['current_strategy']}")
        
        # 학습 시스템 통계
        if adaptive_ga.learning_system:
            learning_stats = adaptive_ga.learning_system.get_learning_stats()
            if learning_stats.get('status') != 'no_data':
                print(f"   - Learning experiences: {learning_stats['total_experiences']}")
        
        return final_status
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return None


def demo_integration():
    """통합 기능 데모"""
    print("\n🔗 Integration Features Demo")
    print("=" * 50)
    
    try:
        # 데이터 로드
        print("📂 Loading data...")
        data_loader = DataLoader()
        ga_params = GAParameters(data_loader, version='quick')
        
        # 수요 예측 및 GA 통합 테스트
        print("🔮 Testing forecast-GA integration...")
        forecaster = DemandForecaster(data_loader, forecast_days=7)
        
        # 간단한 예측 생성
        historical_demand = forecaster.prepare_historical_demand()
        forecaster.train_global_predictor()
        forecast_results = forecaster.predict_future_demand()
        
        # 예측 결과를 GA 파라미터에 통합
        integrator = ForecastIntegrator(ga_params, forecaster)
        integration_stats = integrator.update_demand_with_forecast(
            forecast_results, 
            integration_weight=0.2
        )
        
        print(f"✅ Forecast integration completed:")
        print(f"   - Routes updated: {integration_stats['total_routes']}")
        print(f"   - Adjustment factor: {integration_stats['average_adjustment']:.3f}")
        
        # 동적 스케줄 가중치 생성
        schedule_weights = integrator.create_dynamic_schedule_weights(forecast_results)
        print(f"   - Dynamic weights created: {len(schedule_weights)} schedules")
        
        # 시간 윈도우 매니저와 통합 테스트
        print("🪟 Testing time window integration...")
        window_manager = TimeWindowManager(ga_params, window_size_days=15, overlap_days=3)
        
        window_stats = window_manager.get_window_stats()
        print(f"✅ Time window integration:")
        print(f"   - Windows created: {window_stats['total_windows']}")
        print(f"   - Coverage: {window_manager.validate_window_coverage()['coverage_percentage']:.1f}%")
        
        return {
            'forecast_integration': integration_stats,
            'schedule_weights': len(schedule_weights),
            'window_stats': window_stats
        }
        
    except Exception as e:
        print(f"❌ Integration demo failed: {e}")
        return None


def main():
    """메인 데모 실행 함수"""
    parser = argparse.ArgumentParser(description='Advanced Features Demo')
    parser.add_argument('--feature', choices=['forecasting', 'rolling', 'adaptive', 'integration', 'all'], 
                       default='all', help='Which feature to demo')
    parser.add_argument('--quick', action='store_true', help='Run quick demo with minimal output')
    
    args = parser.parse_args()
    
    print("🌟 Ocean Shipping GA - Advanced Features Demo")
    print("=" * 60)
    print(f"Selected feature: {args.feature}")
    print(f"Quick mode: {args.quick}")
    print("")
    
    # 데모 시작 시간
    demo_start_time = time.time()
    
    results = {}
    
    try:
        if args.feature in ['forecasting', 'all']:
            results['forecasting'] = demo_demand_forecasting()
        
        if args.feature in ['rolling', 'all']:
            results['rolling'] = demo_rolling_optimization()
        
        if args.feature in ['adaptive', 'all']:
            results['adaptive'] = demo_adaptive_ga()
        
        if args.feature in ['integration', 'all']:
            results['integration'] = demo_integration()
        
        # 전체 데모 결과 요약
        demo_duration = time.time() - demo_start_time
        
        print("\n" + "=" * 60)
        print("🎉 Demo Summary")
        print("=" * 60)
        print(f"Total demo time: {demo_duration:.1f} seconds")
        print(f"Features demonstrated: {len([k for k, v in results.items() if v is not None])}")
        
        for feature, result in results.items():
            status = "✅ Success" if result is not None else "❌ Failed"
            print(f"  - {feature.title()}: {status}")
        
        print("\n🌟 All advanced features are now available for production use!")
        print("   - Use shell scripts in scripts/ directory for full execution")
        print("   - Refer to CLAUDE.md for detailed usage instructions")
        print("   - Each feature can be used independently or in combination")
        
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)