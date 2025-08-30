# Ocean Shipping GA - 프로그램 구동 가이드

## 📋 개요

Ocean Shipping GA는 해상 운송 컨테이너 할당을 최적화하는 유전 알고리즘 시스템입니다. 이 문서는 프로그램의 설치부터 실행까지의 전체 과정을 설명합니다.

## 🛠️ 시스템 요구사항



### Python 패키지 의존성
```bash
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.4.0
openpyxl>=3.0.0
```

## 📁 디렉토리 구조

```
ocean_shipping_ga/
├── __init__.py                    # 패키지 초기화
├── USAGE_GUIDE.md                 # 이 문서
├── CLAUDE.md                      # 프로젝트 설명서
├── data/                          # 데이터 파일 및 로더
│   ├── data_loader.py
│   ├── test_data_quality.py       # 데이터 품질 테스트
│   ├── 스해물_스케줄data.xlsx      # 스케줄 데이터
│   ├── 스해물_딜레이스케줄data.xlsx # 딜레이 데이터
│   ├── 스해물_선박data.xlsx        # 선박 데이터
│   ├── 스해물_항구위치data.xlsx    # 항구 데이터
│   └── 스해물_고정값data.xlsx      # 비용 파라미터
├── models/                        # 핵심 모델
│   ├── ga_optimizer.py           # 메인 GA 클래스
│   ├── parameters.py             # 파라미터 설정
│   └── individual.py             # 개체 정의
├── algorithms/                    # GA 알고리즘
│   ├── fitness.py                # 적합도 계산
│   ├── genetic_operators.py      # 유전 연산자
│   └── population.py             # 개체군 관리
├── utils/                        # 유틸리티
│   └── runner.py                 # 실행 함수
└── visualization/                # 시각화
    └── plotter.py                # 결과 시각화
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 1. 디렉토리로 이동
cd /Users/dong/Downloads/ocean/ocean_shipping_ga

# 2. Python 환경 확인
python --version  # Python 3.8+ 확인

# 3. 필요한 패키지 설치
pip install numpy pandas matplotlib openpyxl
```

### 2. 데이터 품질 검증

```python
# 데이터 품질 테스트 실행
python data/test_data_quality.py
```

**예상 출력:**
```
🧪 Ocean Shipping GA - 데이터 품질 테스트
==================================================
📂 데이터 로딩 중...
✅ 스케줄 데이터: 215개 로드
✅ 딜레이 데이터: 62개 로드
✅ 선박 데이터: 215개 로드
✅ 항구 데이터: 9개 로드
✅ 고정값 데이터: 4개 로드

🔧 데이터 정제 중...
✅ schedule.ETA: object → datetime64
✅ delayed.딜레이 ETA: object → datetime64
🚢 선박명: 정리할 항목 없음
💰 고정값 파라미터 재구성: 4개 항목

🔍 데이터 무결성 검증:
✅ 선박명 일치: 모든 스케줄 선박이 선박 데이터에 존재
✅ 딜레이 스케줄 일치: 모든 딜레이가 유효한 스케줄
✅ 항구명 일치: 모든 스케줄 항구가 항구 데이터에 존재
✅ 날짜 순서: ETA > ETD 조건 만족
✅ 데이터 정제 완료

🎉 데이터 품질 테스트 완료!
```

### 3. 기본 실행

```python
# Python 대화형 모드에서 실행
python

>>> from ocean_shipping_ga import run_ocean_shipping_ga
>>> 
>>> # 기본 실행 (자동 데이터 파일 감지)
>>> best_solution, fitness_history = run_ocean_shipping_ga(
...     file_paths=None,    # 자동 감지
...     version='quick',    # 빠른 테스트
...     show_plot=True      # 결과 시각화
... )
```

## 📊 실행 버전별 상세 가이드

### 버전 종류

| 버전 | 세대수 | 개체수 | 소요시간 | 용도 |
|------|---------|---------|----------|------|
| `quick` | 20 | 50 | ~30초 | 빠른 테스트 |
| `medium` | 50 | 100 | ~2분 | 개발/디버깅 |
| `standard` | 100 | 200 | ~5분 | 일반적 최적화 |
| `full` | 200 | 300 | ~15분 | 최고 품질 최적화 |

### 1. 빠른 테스트 (Quick)

```python
# 30초 내외로 빠른 결과 확인
best_solution, fitness_history = run_ocean_shipping_ga(
    file_paths=None,
    version='quick',
    show_plot=True
)
```

**용도**: 
- 시스템 동작 확인
- 데이터 오류 체크  
- 알고리즘 테스트

### 2. 개발용 테스트 (Medium)

```python
# 2분 내외로 중간 품질 결과
best_solution, fitness_history = run_ocean_shipping_ga(
    file_paths=None,
    version='medium',
    show_plot=True
)
```

**용도**:
- 파라미터 튜닝
- 알고리즘 개선 테스트
- 중간 품질 결과 확인

### 3. 표준 최적화 (Standard) - 권장

```python
# 5분 내외로 실용적 품질 결과
best_solution, fitness_history = run_ocean_shipping_ga(
    file_paths=None,
    version='standard',
    show_plot=True
)
```

**용도**:
- 실제 운영 환경
- 실용적 최적화 결과
- 균형잡힌 품질/시간

### 4. 최고 품질 최적화 (Full)

```python
# 15분 내외로 최고 품질 결과
best_solution, fitness_history = run_ocean_shipping_ga(
    file_paths=None,
    version='full',
    show_plot=True
)
```

**용도**:
- 최종 의사결정용
- 최고 품질 솔루션
- 연구/분석용

## 🎯 고급 사용법

### 1. 사용자 정의 데이터 파일 경로

```python
# 커스텀 데이터 파일 경로 지정
custom_paths = {
    'schedule': '/path/to/your/스케줄data.xlsx',
    'delayed': '/path/to/your/딜레이스케줄data.xlsx', 
    'vessel': '/path/to/your/선박data.xlsx',
    'port': '/path/to/your/항구위치data.xlsx',
    'fixed': '/path/to/your/고정값data.xlsx'
}

best_solution, fitness_history = run_ocean_shipping_ga(
    file_paths=custom_paths,
    version='standard',
    show_plot=True
)
```

### 2. 직접 GA 클래스 사용

```python
from ocean_shipping_ga.models.ga_optimizer import OceanShippingGA

# GA 인스턴스 생성
ga = OceanShippingGA(file_paths=None, version='standard')

# 최적화 실행
best_solution, fitness_history = ga.run()

# 상세 결과 출력
ga.print_solution(best_solution)

# 시각화
ga.visualize_results(best_solution, fitness_history)

# 통계 정보 접근
print(f"최종 비용: ${ga.fitness_calculator.calculate_total_cost(best_solution):,.2f}")
print(f"제약 조건 위반: {ga.fitness_calculator.calculate_lp_constraint_penalties(best_solution)}")
```

### 3. 배치 실행 스크립트

```python
# batch_run.py
from ocean_shipping_ga import run_ocean_shipping_ga
import time

versions = ['quick', 'medium', 'standard']
results = {}

for version in versions:
    print(f"\n=== {version.upper()} 버전 실행 중 ===")
    start_time = time.time()
    
    best_solution, fitness_history = run_ocean_shipping_ga(
        file_paths=None,
        version=version,
        show_plot=False  # 배치 실행 시 시각화 생략
    )
    
    execution_time = time.time() - start_time
    results[version] = {
        'solution': best_solution,
        'fitness': best_solution['fitness'],
        'time': execution_time
    }
    
    print(f"실행 시간: {execution_time:.2f}초")
    print(f"최종 적합도: {best_solution['fitness']:.2f}")

# 결과 비교
print("\n=== 버전별 결과 비교 ===")
for version, result in results.items():
    print(f"{version:10} | 적합도: {result['fitness']:10.2f} | 시간: {result['time']:6.2f}초")
```

## 📈 결과 해석 가이드

### 1. 콘솔 출력 예시

```
🧬 유전 알고리즘 시작 (M1 Mac 최적화)
============================================================
📊 모델 파라미터:
  - 스케줄 수: 215
  - 항구 수: 9
  - 루트 수: 186
  - 선박 수: 215
✅ 고정값 데이터에서 비용 파라미터 로드:
  - 운송비(CSHIP): $1000/TEU
  - 유류할증료(CBAF): $100/TEU
  - ETA 패널티(CETA): $150/일

🏗️  초기 개체군 생성 중...
✅ 100개 개체 생성 완료

🔄 최적화 진행 중...
세대   1: 최고=-2847293.21 | 평균=-3024184.35 | 다양성=1247.8 | 변이율=0.25
세대  10: 최고=-2634521.45 | 평균=-2741287.23 | 다양성=1156.3 | 변이율=0.28  
세대  20: 최고=-2523147.89 | 평균=-2587422.11 | 다양성=1023.7 | 변이율=0.32
...
세대 100: 최고=-2387456.12 | 평균=-2421334.67 | 다양성=892.4 | 변이율=0.38

🎯 최적화 완료! (총 소요시간: 287.4초)

📊 최적 솔루션:
총 비용: $2,387,456.12
제약 조건 위반: 0.00 (완전 만족)

🚢 스케줄별 컨테이너 할당:
스케줄 1: Full=45 TEU, Empty=12 TEU
스케줄 2: Full=78 TEU, Empty=18 TEU
...

🏭 항구별 최종 빈 컨테이너 수:
BUSAN: 12,450 TEU
LONG BEACH: 8,230 TEU
NEW YORK: 15,670 TEU
...
```

### 2. 적합도 지표 의미

- **최고 적합도**: 현재 세대 최고 개체의 성능 (음수, 0에 가까울수록 좋음)
- **평균 적합도**: 전체 개체군 평균 성능
- **다양성**: 개체군 다양성 (높을수록 탐색 능력 좋음)
- **변이율**: 적응적 변이 비율

### 3. 솔루션 품질 평가

```python
# 솔루션 품질 평가
def evaluate_solution_quality(best_solution, ga):
    """솔루션 품질 평가"""
    
    # 1. 비용 분석
    total_cost = ga.fitness_calculator.calculate_total_cost(best_solution)
    
    # 2. 제약 조건 위반 체크
    penalties = ga.fitness_calculator.calculate_lp_constraint_penalties(best_solution)
    
    # 3. 용량 활용률 계산
    total_containers = sum(best_solution['xF']) + sum(best_solution['xE'])
    total_capacity = sum(ga.params.CAP_v_r.values())
    utilization = (total_containers / total_capacity) * 100
    
    print(f"=== 솔루션 품질 평가 ===")
    print(f"총 운송 비용: ${total_cost:,.2f}")
    print(f"제약 조건 위반: {penalties:.2f} (0이면 완전 만족)")
    print(f"선박 용량 활용률: {utilization:.1f}%")
    print(f"적합도 점수: {best_solution['fitness']:.2f}")
    
    # 품질 등급 판정
    if penalties == 0 and utilization > 70:
        quality = "우수"
    elif penalties < 1000 and utilization > 50:
        quality = "양호"
    else:
        quality = "개선 필요"
    
    print(f"종합 품질: {quality}")

# 사용 예시
evaluate_solution_quality(best_solution, ga)
```

## 🔧 문제 해결 (Troubleshooting)

### 1. 일반적 오류

#### 📁 **데이터 파일을 찾을 수 없음**
```
FileNotFoundError: Required data file not found: /path/to/file.xlsx
```

**해결책**:
```bash
# 1. 파일 존재 확인
ls -la data/스해물_*.xlsx

# 2. 파일 이름 확인
python data/test_data_quality.py

# 3. 절대 경로로 지정
file_paths = {
    'schedule': '/full/path/to/스해물_스케줄data.xlsx',
    ...
}
```

#### 📊 **메모리 부족 오류**
```
MemoryError: Unable to allocate array
```

**해결책**:
```python
# 1. 더 작은 버전 사용
run_ocean_shipping_ga(version='quick')  # 대신 medium/standard

# 2. 개체군 크기 직접 조정
ga = OceanShippingGA(file_paths=None, version='custom')
ga.params.population_size = 50  # 기본값보다 작게
ga.params.max_generations = 50
```

#### 🐍 **Python 패키지 오류**
```
ModuleNotFoundError: No module named 'numpy'
```

**해결책**:
```bash
# 패키지 설치
pip install numpy pandas matplotlib openpyxl

# 또는 requirements.txt 생성 후
pip install -r requirements.txt
```

### 2. 성능 관련 문제

#### ⏱️ **실행 속도가 너무 느림**

**원인 및 해결책**:
1. **큰 개체군 크기**: `version='quick'` 사용
2. **M1 Mac 최적화 미사용**: numpy가 M1 최적화되어 있는지 확인
3. **백그라운드 프로세스**: 다른 무거운 앱 종료

```python
# 성능 모니터링
import time
import psutil

def monitor_performance():
    """성능 모니터링"""
    print(f"CPU 사용률: {psutil.cpu_percent()}%")
    print(f"메모리 사용률: {psutil.virtual_memory().percent}%")
    print(f"사용 가능 메모리: {psutil.virtual_memory().available / 1024**3:.1f} GB")

monitor_performance()
```

#### 📈 **수렴이 너무 느림**

```python
# 수렴 속도 개선
ga = OceanShippingGA(file_paths=None, version='standard')

# 파라미터 조정
ga.params.p_mutation = 0.3        # 변이율 증가
ga.params.num_elite = 40          # 엘리트 개체 수 증가  
ga.params.convergence_patience = 30  # 조기 종료 조건 완화
```

### 3. 데이터 관련 문제

#### 📋 **데이터 형식 오류**

```python
# 데이터 검증 및 정제
from ocean_shipping_ga.data.data_loader import DataLoader

loader = DataLoader()
try:
    data = loader.load_all_data()
    print("✅ 데이터 로드 성공")
except Exception as e:
    print(f"❌ 데이터 오류: {e}")
    # 상세 오류 분석 실행
```

#### 💰 **비용 파라미터 인식 안됨**

```
⚠️ 고정값 데이터 없음, 기본값 사용
```

**해결책**:
```python
# 1. 고정값 파일 확인
import pandas as pd
df = pd.read_excel('data/스해물_고정값data.xlsx')
print(df.head())
print(df.columns.tolist())

# 2. 수동으로 비용 파라미터 설정
ga.params.CSHIP = 1000  # USD/TEU
ga.params.CBAF = 100    # USD/TEU
ga.params.CETA = 150    # USD/day
```

### 4. 결과 해석 문제

#### 📊 **음수 적합도 값의 의미**

GA에서는 **최소화 문제를 최대화로 변환**하기 때문에 적합도가 음수로 나타납니다:
- `fitness = -(total_cost + penalties)`
- **더 높은 음수 값** = 더 좋은 솔루션
- 예: -2,000,000이 -3,000,000보다 좋음

#### 🚫 **제약 조건 위반이 계속 발생**

```python
# 제약 조건 분석
penalties = ga.fitness_calculator.calculate_lp_constraint_penalties(best_solution)
if penalties > 0:
    print("제약 조건 위반 발생!")
    
    # 세부 분석 (fitness.py의 메소드 활용)
    # 1. 수요 충족 확인
    # 2. 용량 제약 확인  
    # 3. 빈 컨테이너 제약 확인
```

## 🎯 최적화 팁

### 1. 성능 최적화

```python
# M1 Mac 최적화 설정
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# 병렬 처리 활용 (대용량 데이터용)
ga.params.use_adaptive_mutation = True
```

### 2. 파라미터 튜닝

```python
# 고급 파라미터 조정
ga.params.p_crossover = 0.9      # 교차율 증가
ga.params.p_mutation = 0.15      # 변이율 감소
ga.params.convergence_threshold = 0.001  # 수렴 임계값
```

### 3. 결과 저장

```python
import pickle
import json
from datetime import datetime

# 결과 저장
result_data = {
    'timestamp': datetime.now().isoformat(),
    'version': 'standard',
    'best_solution': best_solution,
    'fitness_history': fitness_history,
    'parameters': {
        'population_size': ga.params.population_size,
        'max_generations': ga.params.max_generations,
        'p_crossover': ga.params.p_crossover,
        'p_mutation': ga.params.p_mutation
    }
}

# JSON 저장 (사람이 읽기 쉬운 형태)
with open(f'results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
    # numpy 배열을 리스트로 변환
    json_data = result_data.copy()
    json_data['best_solution']['xF'] = best_solution['xF'].tolist()
    json_data['best_solution']['xE'] = best_solution['xE'].tolist() 
    json_data['best_solution']['y'] = best_solution['y'].tolist()
    
    json.dump(json_data, f, indent=2, ensure_ascii=False)

print("결과가 성공적으로 저장되었습니다!")
```

## 📞 지원 및 문의

### 추가 문서
- `CLAUDE.md`: 프로젝트 전체 개요
- `data/DATA_INTEGRATION_ANALYSIS.md`: 데이터 구조 상세 분석
- `Ocean_Shipping_GA_Technical_Specification.md`: 기술 명세서

### 개발자 모드
```python
# 디버그 모드 활성화
import logging
logging.basicConfig(level=logging.DEBUG)

# 상세 로그 출력
ga.params.verbose = True
```

**성공적인 해상 운송 최적화를 위해 이 가이드를 활용하세요!** 🚢⚙️