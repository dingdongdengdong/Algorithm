# 설정 파일 관리 시스템

이 디렉토리는 Ocean Shipping GA 시스템에서 사용되는 모든 상수값들을 중앙에서 관리하는 설정 시스템을 포함합니다.

## 📁 파일 구조

```
config/
├── __init__.py              # 패키지 초기화
├── config_manager.py        # 설정 관리자 클래스
├── constants.yaml           # 상수값 정의 파일
└── README.md               # 이 파일
```

## 🚀 빠른 시작

### 1. 기본 사용법

```python
from config import get_constant

# 개별 값 조회
kg_per_teu = get_constant('physical.kg_per_teu')  # 30000
crossover_rate = get_constant('genetic_algorithm.p_crossover')  # 0.85

# 기본값과 함께 조회
value = get_constant('some.key', default_value=100)
```

### 2. 설정 관리자 직접 사용

```python
from config import get_config

config = get_config()

# 섹션별로 모든 값 조회
physical_constants = config.get_physical_constants()
ga_params = config.get_ga_parameters()

# 설정 유효성 검증
validation = config.validate_config()
if validation['is_valid']:
    print("✅ 설정 파일이 유효합니다")
else:
    print("❌ 설정 오류:", validation['errors'])
```

## 📋 설정 파일 구조

### 물리적 상수 (`physical`)
```yaml
physical:
  kg_per_teu: 30000          # TEU당 무게 (kg)
  theta: 0.25                # 빈 컨테이너 최소 비율
  max_redistribution_distance: 10000  # 최대 재배치 거리 (km)
```

### 비용 파라미터 (`costs`)
```yaml
costs:
  default:
    cship: 1000              # 기본 운송비 (USD/TEU)
    cbaf: 100                # 기본 유류할증료 (USD/TEU)
    ceta: 150                # 기본 ETA 패널티 (USD/일)
  redistribution:
    cost_per_teu_km: 0.1     # TEU당 km당 비용
```

### 유전 알고리즘 (`genetic_algorithm`)
```yaml
genetic_algorithm:
  p_crossover: 0.85          # 교차 확률
  p_mutation: 0.25           # 기본 돌연변이 확률
  target_fitness: -3000      # 목표 적합도
  convergence_threshold: 0.0005  # 수렴 임계값
  fitness:
    cost_weight: 0.7         # 비용 최적화 가중치
    balance_weight: 0.3      # 균형 최적화 가중치
```

### 모니터링 (`monitoring`)
```yaml
monitoring:
  refresh_interval: 30       # 대시보드 새로고침 간격 (초)
  monitoring_interval: 60    # 모니터링 간격 (초)
  alert_thresholds:
    performance_degradation: 0.2   # 성능 저하 임계값
    data_anomaly_score: 0.8       # 데이터 이상치 임계값
```

### 불균형 감지 (`imbalance_detection`)
```yaml
imbalance_detection:
  critical_shortage_threshold: 0.2   # 심각한 부족 임계값
  shortage_threshold: 0.4            # 부족 임계값
  excess_threshold: 1.6              # 과잉 임계값
  prediction_horizon: 30             # 예측 기간 (일)
```

### 자동 재배치 (`auto_redistribution`)
```yaml
auto_redistribution:
  trigger_rules:
    critical_shortage:
      threshold: 0.15                # 임계값
      priority: 5                    # 우선순위
      cooldown_hours: 2             # 쿨다운 시간
      max_daily_triggers: 6         # 일일 최대 트리거 수
```

## 🔧 설정 관리자 기능

### 주요 메서드

#### 1. 값 조회
```python
# 점(.)으로 구분된 키 경로로 값 조회
value = config.get('physical.kg_per_teu')

# 기본값과 함께 조회
value = config.get('some.key', default_value=100)
```

#### 2. 섹션별 조회
```python
# 물리적 상수 전체 조회
physical = config.get_physical_constants()

# 유전 알고리즘 파라미터 전체 조회
ga_params = config.get_ga_parameters()

# 모든 파라미터 조회
all_params = config.get_all_parameters()
```

#### 3. 설정 유효성 검증
```python
validation = config.validate_config()

if validation['is_valid']:
    print("✅ 설정이 유효합니다")
else:
    print("❌ 설정 오류:")
    for error in validation['errors']:
        print(f"  - {error}")
    
    print("⚠️ 누락된 섹션:")
    for section in validation['missing_sections']:
        print(f"  - {section}")
```

#### 4. 런타임 설정 변경
```python
# 런타임에 값 설정 (파일에는 저장되지 않음)
config.set('monitoring.refresh_interval', 60)

# 설정 파일 재로드
config.reload_config()
```

## 📊 설정 요약 출력

```python
# 설정 파일의 전체 요약을 콘솔에 출력
config.print_config_summary()
```

출력 예시:
```
============================================================
📋 설정 파일 요약
============================================================

🔧 물리적 상수:
  kg_per_teu: 30000
  theta: 0.25
  max_redistribution_distance: 10000

🔧 비용 파라미터:
  default:
    cship: 1000
    cbaf: 100
    ceta: 150
...
```

## 🔄 설정 파일 업데이트

### 1. YAML 파일 직접 편집
`constants.yaml` 파일을 직접 편집하여 값을 변경할 수 있습니다.

### 2. 코드에서 동적 변경
```python
from config import get_config

config = get_config()

# 런타임에 값 변경
config.set('monitoring.refresh_interval', 120)

# 변경된 값 확인
new_interval = config.get('monitoring.refresh_interval')
print(f"새로운 새로고침 간격: {new_interval}초")
```

## ⚠️ 주의사항

1. **기본값 제공**: `get_constant()` 함수 사용 시 항상 적절한 기본값을 제공하세요.
2. **키 경로 정확성**: 점(.)으로 구분된 키 경로가 정확해야 합니다.
3. **타입 일치**: YAML 파일의 값 타입이 코드에서 기대하는 타입과 일치해야 합니다.
4. **런타임 변경**: `config.set()`으로 변경한 값은 프로그램 재시작 시 사라집니다.

## 🧪 테스트

설정 시스템이 제대로 작동하는지 테스트하려면:

```bash
# 설정 요약 출력
python -c "from config.config_manager import ConfigManager; ConfigManager().print_config_summary()"

# 개별 값 테스트
python -c "from config import get_constant; print('TEU당 무게:', get_constant('physical.kg_per_teu'))"
```

## 📝 기여 가이드

새로운 상수값을 추가할 때:

1. `constants.yaml`에 적절한 섹션과 값 추가
2. 관련 코드에서 `get_constant()` 함수 사용
3. 기본값 제공
4. 문서 업데이트

이렇게 하면 시스템의 모든 상수값을 중앙에서 관리할 수 있어 유지보수성이 크게 향상됩니다.
