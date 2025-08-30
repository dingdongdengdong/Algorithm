#!/usr/bin/env python3
"""
데이터 품질 테스트 스크립트
Usage: python test_data_quality.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_loader import DataLoader

def test_data_quality():
    """데이터 품질 테스트 수행"""
    print("🧪 Ocean Shipping GA - 데이터 품질 테스트")
    print("=" * 50)
    
    try:
        # DataLoader 인스턴스 생성 (자동으로 데이터 파일 찾기)
        loader = DataLoader()
        
        # 데이터 로드 및 정제 (자동으로 품질 검사 포함)
        data = loader.load_all_data()
        
        print("\n" + "=" * 50)
        print("🎉 데이터 품질 테스트 완료!")
        
        # 요약 통계
        print(f"\n📈 데이터 요약:")
        print(f"  - 스케줄: {len(data['schedule'])}개")
        print(f"  - 딜레이: {len(data['delayed'])}개")
        print(f"  - 선박: {len(data['vessel'])}개")
        print(f"  - 항구: {len(data['port'])}개")
        
        # 고정값 파라미터 확인
        fixed_params = loader.get_fixed_params()
        if fixed_params:
            print(f"  - 고정값 파라미터: {len(fixed_params)}개 성공적으로 파싱")
        
        print(f"\n✅ 모든 데이터가 GA 최적화에 사용할 준비가 완료되었습니다!")
        return True
        
    except Exception as e:
        print(f"\n❌ 데이터 품질 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_quality()
    sys.exit(0 if success else 1)