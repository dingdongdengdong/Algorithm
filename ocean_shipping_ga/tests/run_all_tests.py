#!/usr/bin/env python3
"""
모든 테스트 실행 스크립트
Ocean Shipping GA 시스템의 모든 테스트를 순차적으로 실행
"""

import sys
import os
import time
from datetime import datetime

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def run_config_system_test():
    """설정 시스템 테스트 실행"""
    print("🧪 설정 시스템 테스트 실행 중...")
    try:
        from tests.test_config_system import test_config_system, test_code_integration
        
        config_test_passed = test_config_system()
        integration_test_passed = test_code_integration()
        
        return config_test_passed and integration_test_passed
        
    except Exception as e:
        print(f"❌ 설정 시스템 테스트 실패: {e}")
        return False

def run_temporal_features_test():
    """시간적 기능 테스트 실행"""
    print("⏰ 시간적 기능 테스트 실행 중...")
    try:
        from tests.test_temporal_features import test_temporal_features
        return test_temporal_features()
        
    except Exception as e:
        print(f"❌ 시간적 기능 테스트 실패: {e}")
        return False

def run_quick_temporal_test():
    """빠른 시간적 테스트 실행"""
    print("🚀 빠른 시간적 테스트 실행 중...")
    try:
        from tests.quick_temporal_test import test_temporal_features_quick
        return test_temporal_features_quick()
        
    except Exception as e:
        print(f"❌ 빠른 시간적 테스트 실패: {e}")
        return False

def run_constraints_validation():
    """제약 조건 검증 테스트 실행"""
    print("🔒 제약 조건 검증 테스트 실행 중...")
    try:
        from tests.validate_constraints import test_constraint_validation
        return test_constraint_validation()
        
    except Exception as e:
        print(f"❌ 제약 조건 검증 테스트 실패: {e}")
        return False

def main():
    """모든 테스트 실행"""
    print("🚢 Ocean Shipping GA - 전체 테스트 실행")
    print("=" * 60)
    print(f"📅 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    start_time = time.time()
    test_results = {}
    
    # 1. 설정 시스템 테스트
    print("\n1️⃣ 설정 시스템 테스트")
    test_results['config_system'] = run_config_system_test()
    
    # 2. 시간적 기능 테스트
    print("\n2️⃣ 시간적 기능 테스트")
    test_results['temporal_features'] = run_temporal_features_test()
    
    # 3. 빠른 시간적 테스트
    print("\n3️⃣ 빠른 시간적 테스트")
    test_results['quick_temporal'] = run_quick_temporal_test()
    
    # 4. 제약 조건 검증
    print("\n4️⃣ 제약 조건 검증")
    test_results['constraints'] = run_constraints_validation()
    
    # 결과 요약
    end_time = time.time()
    execution_time = end_time - start_time
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    failed_tests = total_tests - passed_tests
    
    for test_name, result in test_results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    print(f"\n📈 전체 결과: {passed_tests}/{total_tests} 테스트 통과")
    print(f"⏱️ 실행 시간: {execution_time:.2f}초")
    
    if failed_tests == 0:
        print("\n🎉 모든 테스트 통과! 시스템이 정상적으로 작동합니다.")
        return True
    else:
        print(f"\n⚠️ {failed_tests}개 테스트가 실패했습니다. 실패한 테스트를 확인해주세요.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
