# 🧪 테스트 패키지

이 폴더는 Ocean Shipping GA 시스템의 모든 테스트 파일들을 포함합니다.

## 📁 파일 구조

```
tests/
├── __init__.py                 # 테스트 패키지 초기화
├── README.md                   # 이 파일
├── run_all_tests.py           # 모든 테스트 실행 스크립트
├── test_config_system.py      # 설정 시스템 테스트
├── test_temporal_features.py  # 시간적 기능 테스트
├── quick_temporal_test.py     # 빠른 시간적 테스트
└── validate_constraints.py    # 제약 조건 검증 테스트
```

## 🚀 테스트 실행 방법

### 1. 전체 테스트 실행

```bash
# 프로젝트 루트에서 실행
python tests/run_all_tests.py

# 또는 tests 폴더에서 실행
cd tests
python run_all_tests.py
```

### 2. 개별 테스트 실행

```bash
# 설정 시스템 테스트만 실행
python tests/test_config_system.py

# 시간적 기능 테스트만 실행
python tests/test_temporal_features.py

# 빠른 시간적 테스트만 실행
python tests/quick_temporal_test.py

# 제약 조건 검증만 실행
python tests/validate_constraints.py
```

### 3. Python 모듈로 실행

```bash
# 프로젝트 루트에서
python -m tests.run_all_tests

# 개별 테스트
python -m tests.test_config_system
python -m tests.test_temporal_features
```

## 📋 테스트 종류

### 1. 설정 시스템 테스트 (`test_config_system.py`)
- **목적**: YAML 설정 파일 로드 및 관리 기능 검증
- **테스트 항목**:
  - 설정 파일 로드
  - 기본 값 조회
  - 설정 관리자 기능
  - 설정 유효성 검증
  - 런타임 설정 변경
  - 코드 통합 확인

### 2. 시간적 기능 테스트 (`test_temporal_features.py`)
- **목적**: 시간 기반 스케줄링 및 최적화 기능 검증
- **테스트 항목**:
  - 시간적 복잡성 처리
  - 스케줄 충돌 감지
  - 시간 기반 제약 조건

### 3. 빠른 시간적 테스트 (`quick_temporal_test.py`)
- **목적**: 시간적 기능의 빠른 검증
- **테스트 항목**:
  - 기본 시간적 기능
  - 성능 측정

### 4. 제약 조건 검증 (`validate_constraints.py`)
- **목적**: LP 모델 제약 조건 검증
- **테스트 항목**:
  - 제약 조건 유효성
  - 해의 타당성 검증

## 🔧 테스트 환경 설정

### 필수 요구사항
- Python 3.8+
- 프로젝트 루트에서 실행
- 필요한 의존성 패키지 설치

### 의존성 패키지
```bash
pip install numpy pandas matplotlib seaborn networkx scipy
```

## 📊 테스트 결과 해석

### 성공 케이스
```
🎉 모든 테스트 통과! 시스템이 정상적으로 작동합니다.
📈 전체 결과: 4/4 테스트 통과
⏱️ 실행 시간: 12.34초
```

### 실패 케이스
```
⚠️ 1개 테스트가 실패했습니다. 실패한 테스트를 확인해주세요.
📈 전체 결과: 3/4 테스트 통과
```

## 🐛 문제 해결

### 일반적인 문제들

#### 1. Import 오류
```bash
ModuleNotFoundError: No module named 'config'
```
**해결책**: 프로젝트 루트에서 실행하거나 `PYTHONPATH` 설정

#### 2. 경로 오류
```bash
FileNotFoundError: [Errno 2] No such file or directory
```
**해결책**: 올바른 작업 디렉토리에서 실행

#### 3. 의존성 오류
```bash
ImportError: No module named 'numpy'
```
**해결책**: 필요한 패키지 설치

### 디버깅 팁

1. **개별 테스트 실행**: 문제가 있는 테스트만 실행하여 격리
2. **로그 확인**: 상세한 오류 메시지 확인
3. **환경 검증**: Python 버전 및 패키지 설치 상태 확인

## 📝 새로운 테스트 추가

새로운 테스트를 추가할 때:

1. **테스트 파일 생성**: `test_[기능명].py` 형식으로 명명
2. **테스트 함수 작성**: 명확한 함수명과 문서화
3. **`__init__.py` 업데이트**: 새로운 테스트 함수 import
4. **`run_all_tests.py` 업데이트**: 새로운 테스트 실행 함수 추가
5. **README 업데이트**: 새로운 테스트 설명 추가

### 예시
```python
# test_new_feature.py
def test_new_feature():
    """새로운 기능 테스트"""
    try:
        # 테스트 로직
        result = some_function()
        assert result == expected_value
        print("✅ 새로운 기능 테스트 통과")
        return True
    except Exception as e:
        print(f"❌ 새로운 기능 테스트 실패: {e}")
        return False
```

## 🔄 지속적 통합 (CI/CD)

테스트는 다음 상황에서 자동으로 실행되어야 합니다:

- **코드 커밋**: 모든 변경사항에 대해 테스트 실행
- **Pull Request**: 병합 전 테스트 통과 확인
- **배포 전**: 프로덕션 배포 전 최종 테스트
- **정기 실행**: 일일/주간 자동 테스트

## 📞 지원

테스트 관련 문제가 있거나 새로운 테스트가 필요한 경우:

1. 이슈 트래커에 문제 보고
2. 개발팀과 논의
3. 테스트 코드 리뷰 요청

테스트는 시스템의 안정성과 신뢰성을 보장하는 중요한 요소입니다. 모든 테스트가 통과할 때까지 코드를 수정하고 개선해주세요.
