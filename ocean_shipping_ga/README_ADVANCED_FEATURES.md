# 🌟 Ocean Shipping GA - Advanced Features

해상 운송 최적화를 위한 고급 시계열 처리 기능들이 추가되었습니다.

## 🔮 1. 수요 예측 (LSTM 기반)

### 기능
- **LSTM 신경망** 기반 수요 예측
- **통계적 폴백** 모델 (TensorFlow 없을 시)
- **루트별 개별 예측** 지원
- **GA 파라미터 자동 통합**

### 사용법
```bash
# 기본 실행 (30일 예측)
./scripts/run_demand_forecasting.sh

# 사용자 정의 설정
./scripts/run_demand_forecasting.sh --days 60 --epochs 100 --validation 0.3

# 루트별 예측 비활성화
./scripts/run_demand_forecasting.sh --no-route-specific
```

### Python API
```python
from advanced_features.forecasting import DemandForecaster, ForecastIntegrator

# 예측기 생성
forecaster = DemandForecaster(data_loader, forecast_days=30)

# 모델 훈련
forecaster.train_global_predictor()

# 예측 수행
forecast_results = forecaster.predict_future_demand()

# GA 파라미터 통합
integrator = ForecastIntegrator(ga_params, forecaster)
integrator.update_demand_with_forecast(forecast_results)
```

## 🔄 2. 롤링 최적화

### 기능
- **시간 윈도우** 기반 분할 최적화
- **웜 스타트** 지원으로 연속성 보장
- **동적 스케줄 관리**
- **전역 해 통합**

### 사용법
```bash
# 기본 실행 (30일 윈도우, 7일 겹침)
./scripts/run_rolling_optimization.sh

# 사용자 정의 설정
./scripts/run_rolling_optimization.sh --window-size 45 --overlap 10 --generations 100

# 웜 스타트 비활성화
./scripts/run_rolling_optimization.sh --no-warm-start
```

### Python API
```python
from advanced_features.rolling_optimization import RollingOptimizer

# 롤링 최적화기 생성
rolling_optimizer = RollingOptimizer(
    ga_params,
    window_size_days=30,
    overlap_days=7,
    ga_generations=50
)

# 롤링 최적화 실행
summary = rolling_optimizer.run_rolling_optimization()
global_solution = summary['global_solution']
```

## 🧠 3. 실시간 적응형 GA

### 기능
- **실시간 모니터링** 시스템
- **자동 파라미터 조정**
- **성능 기반 학습**
- **4가지 적응 전략** (aggressive, balanced, conservative, reactive)

### 사용법
```bash
# 기본 실행 (1시간 동안)
./scripts/run_adaptive_ga.sh

# 사용자 정의 설정
./scripts/run_adaptive_ga.sh --duration 7200 --strategy aggressive --adaptation-interval 120

# 학습 기능 비활성화
./scripts/run_adaptive_ga.sh --no-learning
```

### Python API
```python
from advanced_features.adaptive_systems import AdaptiveGA

# 적응형 GA 생성
adaptive_ga = AdaptiveGA(
    ga_params,
    adaptation_interval=300,
    learning_enabled=True
)

# 적응형 모드 시작
adaptive_ga.start_adaptive_mode()

# 상태 확인
status = adaptive_ga.get_adaptation_status()

# 적응형 모드 중지
adaptive_ga.stop_adaptive_mode()
```

## 🌟 4. 통합 실행

### 전체 기능 순차 실행
```bash
# 모든 고급 기능 실행
./scripts/run_all_advanced_features.sh

# 선택적 실행
./scripts/run_all_advanced_features.sh --forecasting-only
./scripts/run_all_advanced_features.sh --no-adaptive

# 짧은 시간 테스트
./scripts/run_all_advanced_features.sh --duration 900
```

### 데모 실행
```python
# Python 데모 (모든 기능)
python scripts/demo_advanced_features.py

# 특정 기능만 데모
python scripts/demo_advanced_features.py --feature forecasting
python scripts/demo_advanced_features.py --feature adaptive --quick
```

## 📊 결과 분석

### 생성되는 파일들
```
results/
├── demand_forecast_YYYYMMDD_HHMMSS.csv     # 수요 예측 결과
├── forecast_report_YYYYMMDD_HHMMSS.txt     # 예측 리포트
├── rolling_summary_YYYYMMDD_HHMMSS.json    # 롤링 최적화 요약
├── rolling_solution_YYYYMMDD_HHMMSS.pkl    # 전역 해
├── adaptive_state_YYYYMMDD_HHMMSS.pkl      # 적응 상태
├── learning_state_YYYYMMDD_HHMMSS.pkl      # 학습 상태
└── monitoring_logs_YYYYMMDD_HHMMSS.json    # 모니터링 로그
```

### 성능 지표
- **수요 예측**: MAE, RMSE, MAPE
- **롤링 최적화**: 윈도우별 fitness, 수렴 속도
- **적응형 GA**: 적응 성공률, 성능 개선도

## 🔧 고급 설정

### 환경 변수
```bash
export OCEAN_GA_RESULTS_DIR="custom/results/path"
export OCEAN_GA_LOG_LEVEL="DEBUG"
export OCEAN_GA_CACHE_SIZE="1000"
```

### 의존성
```bash
# 선택적 의존성 (LSTM 예측용)
pip install tensorflow scikit-learn

# 시스템 모니터링용
pip install psutil
```

## 🚀 성능 최적화

### 권장 설정
- **개발/테스트**: `quick` 버전 (20세대, 50인구)
- **운영환경**: `standard` 버전 (100세대, 200인구)
- **고성능**: `full` 버전 (200세대, 300인구)

### 성능 최적화
- 벡터화된 연산 사용
- 메모리 효율적 윈도우 처리
- 병렬 처리 지원

## 📈 활용 예시

### 1. 단기 수요 급증 대응
```bash
# 수요 예측으로 급증 감지
./scripts/run_demand_forecasting.sh --days 14

# 적응형 GA로 실시간 대응
./scripts/run_adaptive_ga.sh --strategy reactive --duration 3600
```

### 2. 대용량 스케줄 처리
```bash
# 롤링 최적화로 분할 처리
./scripts/run_rolling_optimization.sh --window-size 21 --overlap 3 --generations 75
```

### 3. 통합 운영 시스템
```bash
# 전체 파이프라인 실행
./scripts/run_all_advanced_features.sh --duration 1800
```

## 🔍 문제 해결

### 공통 문제
- **메모리 부족**: 윈도우 크기나 인구 크기 감소
- **느린 수렴**: mutation rate 증가 또는 전략을 'aggressive'로 변경
- **예측 정확도 낮음**: 훈련 데이터 기간 확대 또는 epochs 증가

### 로그 확인
```bash
# 실행 로그 확인
tail -f results/advanced_suite_*/execution.log

# 오류 로그 확인
cat results/advanced_suite_*/errors.txt
```

## 📚 추가 문서
- [기본 GA 사용법](CLAUDE.md)
- [데이터 준비 가이드](data/README.md)
- [API 참조](docs/API_REFERENCE.md)
- [성능 튜닝 가이드](docs/PERFORMANCE_TUNING.md)

---

**🎯 이제 Ocean Shipping GA는 미래 수요 예측, 동적 최적화, 실시간 적응이 가능한 종합적인 해상 운송 최적화 솔루션이 되었습니다.**