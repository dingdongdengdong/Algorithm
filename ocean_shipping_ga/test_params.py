#!/usr/bin/env python3
"""
고정값 파라미터 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_loader import DataLoader
from models.parameters import GAParameters

def test_cost_parameters():
    """비용 파라미터 설정 테스트"""
    print("=== 🧪 고정값 파라미터 테스트 ===\n")
    
    try:
        # 데이터 로더 생성
        print("1. 데이터 로더 생성 중...")
        data_loader = DataLoader()
        print("   ✅ 데이터 로더 생성 완료")
        
        # 고정값 파라미터 확인
        print("\n2. 고정값 파라미터 확인...")
        fixed_params = data_loader.get_fixed_params()
        if fixed_params:
            print("   ✅ 고정값 파라미터 로드됨:")
            for key, value in fixed_params.items():
                print(f"     - {key}: {value}")
        else:
            print("   ⚠️ 고정값 파라미터 없음")
        
        # GA 파라미터 생성
        print("\n3. GA 파라미터 생성 중...")
        params = GAParameters(data_loader)
        print("   ✅ GA 파라미터 생성 완료")
        
        # 비용 파라미터 값 확인
        print("\n4. 설정된 비용 파라미터 값:")
        print(f"   - CSHIP (기본 운송비): ${params.CSHIP:,.0f}/TEU")
        print(f"   - CBAF (유류할증료): ${params.CBAF:,.0f}/TEU")
        print(f"   - CETA (ETA 패널티): ${params.CETA:,.0f}/일")
        print(f"   - KG_PER_TEU (컨테이너 용량): {params.KG_PER_TEU:,.0f} KG")
        print(f"   - CEMPTY_SHIP (빈 컨테이너 운송비): ${params.CEMPTY_SHIP:,.0f}/TEU")
        print(f"   - theta (빈 컨테이너 최소 비율): {params.theta}")
        
        # 예상값과 비교
        print("\n5. 예상값과 비교:")
        expected_values = {
            'CSHIP': 1000,
            'CBAF': 100,
            'CETA': 150,
            'KG_PER_TEU': 30000
        }
        
        actual_values = {
            'CSHIP': params.CSHIP,
            'CBAF': params.CBAF,
            'CETA': params.CETA,
            'KG_PER_TEU': params.KG_PER_TEU
        }
        
        for param, expected in expected_values.items():
            actual = actual_values[param]
            if abs(actual - expected) < 0.01:
                print(f"   ✅ {param}: {actual} (예상값: {expected}) - 일치")
            else:
                print(f"   ❌ {param}: {actual} (예상값: {expected}) - 불일치!")
        
        # KG_PER_TEU 사용 예시 확인
        print("\n6. KG_PER_TEU 사용 예시:")
        if hasattr(params, 'D_ab') and params.D_ab:
            sample_route = list(params.D_ab.keys())[0]
            if sample_route in params.Q_r:
                kg_amount = params.Q_r[sample_route]
                teu_amount = params.D_ab[sample_route]
                calculated_teu = max(1, int(kg_amount / params.KG_PER_TEU))
                print(f"   - 샘플 루트 {sample_route}:")
                print(f"     주문량: {kg_amount:,.0f} KG")
                print(f"     변환된 TEU: {teu_amount} TEU")
                print(f"     계산된 TEU: {calculated_teu} TEU")
                print(f"     KG_PER_TEU 적용: {kg_amount:,.0f} ÷ {params.KG_PER_TEU:,.0f} = {kg_amount/params.KG_PER_TEU:.2f}")
        
        print("\n=== 🎯 테스트 완료 ===")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cost_parameters()
