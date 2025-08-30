#!/bin/bash

# 수요 예측 실행 스크립트
# LSTM 기반 해상 운송 수요 예측

echo "🔮 Ocean Shipping Demand Forecasting System"
echo "=========================================="

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_CMD="python3"

# 파라미터 설정
FORECAST_DAYS=30
TRAIN_EPOCHS=50
VALIDATION_SPLIT=0.2
ENABLE_ROUTE_SPECIFIC=true
SAVE_RESULTS=true

# 명령행 인수 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--days)
            FORECAST_DAYS="$2"
            shift 2
            ;;
        -e|--epochs)
            TRAIN_EPOCHS="$2"
            shift 2
            ;;
        -v|--validation)
            VALIDATION_SPLIT="$2"
            shift 2
            ;;
        --no-route-specific)
            ENABLE_ROUTE_SPECIFIC=false
            shift
            ;;
        --no-save)
            SAVE_RESULTS=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -d, --days DAYS              Forecast days (default: 30)"
            echo "  -e, --epochs EPOCHS          Training epochs (default: 50)"
            echo "  -v, --validation SPLIT       Validation split (default: 0.2)"
            echo "  --no-route-specific          Disable route-specific forecasting"
            echo "  --no-save                    Don't save results"
            echo "  -h, --help                   Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 환경 확인
cd "$PROJECT_ROOT"

echo "📋 Configuration:"
echo "  - Forecast days: $FORECAST_DAYS"
echo "  - Training epochs: $TRAIN_EPOCHS"
echo "  - Validation split: $VALIDATION_SPLIT"
echo "  - Route-specific forecasting: $ENABLE_ROUTE_SPECIFIC"
echo "  - Save results: $SAVE_RESULTS"
echo ""

# Python 스크립트 실행
$PYTHON_CMD -c "
import sys
import os
sys.path.append('$PROJECT_ROOT')

from datetime import datetime
import pandas as pd
import numpy as np
from data.data_loader import DataLoader
from advanced_features.forecasting import DemandForecaster, ForecastIntegrator
from models.parameters import GAParameters

print('🚀 Starting demand forecasting...')

try:
    # 데이터 로드
    print('📂 Loading data...')
    data_loader = DataLoader()
    
    # GA 파라미터 생성
    print('🔧 Initializing parameters...')
    ga_params = GAParameters(data_loader, version='quick')
    
    # Python boolean 변수로 변환
    enable_route_specific = '$ENABLE_ROUTE_SPECIFIC' == 'true'
    save_results = '$SAVE_RESULTS' == 'true'
    
    # 수요 예측기 생성
    forecaster = DemandForecaster(data_loader, forecast_days=$FORECAST_DAYS)
    
    # 과거 데이터 준비
    print('📊 Preparing historical data...')
    historical_demand = forecaster.prepare_historical_demand()
    
    # 전역 예측기 훈련
    print('🎯 Training global predictor...')
    global_training_result = forecaster.train_global_predictor()
    
    if global_training_result['status'] == 'success':
        print(f'   ✅ Global predictor trained successfully')
        if 'final_loss' in global_training_result:
            print(f'   📈 Final loss: {global_training_result[\"final_loss\"]:.6f}')
    else:
        print(f'   ⚠️ Global predictor training: {global_training_result[\"status\"]}')
    
    # 루트별 예측기 훈련 (옵션)
    if enable_route_specific:
        print('🛤️ Training route-specific predictors...')
        route_results = forecaster.train_route_predictors()
        print(f'   ✅ Trained {len(route_results)} route-specific predictors')
    
    # 미래 수요 예측
    print('🔮 Generating forecast...')
    forecast_results = forecaster.predict_future_demand()
    
    # 결과 출력
    print('')
    print('📊 Forecast Results:')
    global_forecast = forecast_results['global_forecast']
    print(f'   - Forecast period: {len(global_forecast)} days')
    print(f'   - Average daily demand: {global_forecast[\"predicted_demand_teu\"].mean():.1f} TEU')
    print(f'   - Peak demand: {global_forecast[\"predicted_demand_teu\"].max():.1f} TEU')
    print(f'   - Minimum demand: {global_forecast[\"predicted_demand_teu\"].min():.1f} TEU')
    
    if enable_route_specific and forecast_results['route_forecasts']:
        print(f'   - Route-specific forecasts: {len(forecast_results[\"route_forecasts\"])} routes')
    
    # GA 파라미터 통합 테스트
    print('')
    print('🔗 Testing GA integration...')
    integrator = ForecastIntegrator(ga_params, forecaster)
    
    # 예측 결과를 GA 파라미터에 통합
    integration_stats = integrator.update_demand_with_forecast(forecast_results, integration_weight=0.3)
    print(f'   ✅ Updated {integration_stats[\"total_routes\"]} routes')
    print(f'   📈 Average adjustment factor: {integration_stats[\"average_adjustment\"]:.3f}')
    
    # 동적 가중치 생성
    schedule_weights = integrator.create_dynamic_schedule_weights(forecast_results)
    print(f'   ⚖️ Created weights for {len(schedule_weights)} schedules')
    
    # 결과 리포트 생성
    print('')
    print('📋 Generating reports...')
    forecast_report = forecaster.generate_forecast_report(forecast_results)
    integration_report = integrator.generate_integration_report(
        integration_stats, schedule_weights, {}
    )
    
    # 결과 저장 (옵션)
    if save_results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 예측 결과 저장
        forecast_file = f'results/demand_forecast_{timestamp}.csv'
        os.makedirs('results', exist_ok=True)
        global_forecast.to_csv(forecast_file, index=False)
        print(f'   💾 Forecast saved to {forecast_file}')
        
        # 리포트 저장
        report_file = f'results/forecast_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(forecast_report)
            f.write('\n\n')
            f.write(integration_report)
        print(f'   📄 Report saved to {report_file}')
    
    # 성능 평가 (최근 데이터가 있는 경우)
    print('')
    print('📈 Evaluating prediction accuracy...')
    try:
        # 최근 14일에 대한 평가
        test_start = historical_demand.index.max() - pd.Timedelta(days=14)
        evaluation_result = forecaster.evaluate_predictions(test_start, test_days=7)
        
        if evaluation_result['status'] == 'success':
            print(f'   ✅ Evaluation completed:')
            print(f'      MAE: {evaluation_result[\"mae\"]:.2f} TEU')
            print(f'      RMSE: {evaluation_result[\"rmse\"]:.2f} TEU')
            print(f'      MAPE: {evaluation_result[\"mape\"]:.2f}%')
        else:
            print(f'   ⚠️ Evaluation: {evaluation_result[\"message\"]}')
    except Exception as e:
        print(f'   ⚠️ Evaluation failed: {e}')
    
    print('')
    print('✅ Demand forecasting completed successfully!')
    
    # 최종 리포트 출력
    print('')
    print(forecast_report)
    
except Exception as e:
    print(f'❌ Demand forecasting failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

echo ""
echo "🎉 Demand forecasting script completed!"