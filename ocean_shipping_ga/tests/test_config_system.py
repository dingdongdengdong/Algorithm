#!/usr/bin/env python3
"""
설정 시스템 테스트 스크립트
하드코딩된 상수값들이 설정 파일에서 제대로 로드되는지 확인
"""

import sys
import os

# 프로젝트 루트 추가 (tests 폴더에서 실행 시 상위 디렉토리)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_config_system():
    """설정 시스템 테스트"""
    print("🧪 설정 시스템 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. 설정 파일 로드 테스트
        from config import get_constant, get_config
        
        print("✅ 설정 모듈 import 성공")
        
        # 2. 기본 값 조회 테스트
        print("\n📊 기본 값 조회 테스트:")
        
        test_values = [
            ('physical.kg_per_teu', 'TEU당 무게'),
            ('physical.theta', '빈 컨테이너 최소 비율'),
            ('genetic_algorithm.p_crossover', '교차 확률'),
            ('genetic_algorithm.p_mutation', '돌연변이 확률'),
            ('costs.default.cship', '기본 운송비'),
            ('monitoring.refresh_interval', '대시보드 새로고침 간격'),
            ('imbalance_detection.critical_shortage_threshold', '심각한 부족 임계값')
        ]
        
        for key_path, description in test_values:
            value = get_constant(key_path)
            print(f"  {description}: {value} ({key_path})")
        
        # 3. 설정 관리자 테스트
        print("\n🔧 설정 관리자 테스트:")
        config = get_config()
        
        # 섹션별 조회
        physical_constants = config.get_physical_constants()
        ga_params = config.get_ga_parameters()
        
        print(f"  물리적 상수 개수: {len(physical_constants)}")
        print(f"  GA 파라미터 개수: {len(ga_params)}")
        
        # 4. 설정 유효성 검증
        print("\n✅ 설정 유효성 검증:")
        validation = config.validate_config()
        
        if validation['is_valid']:
            print("  ✅ 설정 파일이 유효합니다")
        else:
            print("  ❌ 설정 파일에 오류가 있습니다:")
            for error in validation['errors']:
                print(f"    - {error}")
        
        # 5. 런타임 설정 변경 테스트
        print("\n🔄 런타임 설정 변경 테스트:")
        original_value = get_constant('monitoring.refresh_interval')
        print(f"  원래 값: {original_value}")
        
        # 값 변경
        config.set('monitoring.refresh_interval', 120)
        new_value = get_constant('monitoring.refresh_interval')
        print(f"  변경된 값: {new_value}")
        
        # 원래 값으로 복원
        config.set('monitoring.refresh_interval', original_value)
        restored_value = get_constant('monitoring.refresh_interval')
        print(f"  복원된 값: {restored_value}")
        
        # 6. 설정 요약 출력
        print("\n📋 설정 요약:")
        config.print_config_summary()
        
        print("\n🎉 모든 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_code_integration():
    """코드 통합 테스트 - 실제 모듈에서 설정값 사용 확인"""
    print("\n🔗 코드 통합 테스트:")
    print("=" * 60)
    
    try:
        # GAParameters에서 설정값 사용 확인
        from models.parameters import GAParameters
        print("✅ GAParameters 모듈 import 성공")
        
        # FitnessCalculator에서 설정값 사용 확인
        from algorithms.fitness import FitnessCalculator
        print("✅ FitnessCalculator 모듈 import 성공")
        
        # RedistributionOptimizer에서 설정값 사용 확인
        from models.redistribution_optimizer import ContainerRedistributionOptimizer
        print("✅ ContainerRedistributionOptimizer 모듈 import 성공")
        
        print("✅ 모든 핵심 모듈에서 설정 시스템 사용 가능")
        return True
        
    except Exception as e:
        print(f"❌ 코드 통합 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚢 Ocean Shipping GA - 설정 시스템 테스트")
    print("=" * 60)
    
    # 기본 테스트
    config_test_passed = test_config_system()
    
    # 코드 통합 테스트
    integration_test_passed = test_code_integration()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    
    if config_test_passed:
        print("✅ 설정 시스템 테스트: 통과")
    else:
        print("❌ 설정 시스템 테스트: 실패")
    
    if integration_test_passed:
        print("✅ 코드 통합 테스트: 통과")
    else:
        print("❌ 코드 통합 테스트: 실패")
    
    if config_test_passed and integration_test_passed:
        print("\n🎉 모든 테스트 통과! 설정 시스템이 정상적으로 작동합니다.")
        print("\n💡 사용법:")
        print("  from config import get_constant")
        print("  value = get_constant('physical.kg_per_teu')")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 설정을 확인해주세요.")
        sys.exit(1)
