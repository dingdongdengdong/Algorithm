#!/usr/bin/env python3
"""
고정값들이 실제 알고리즘에서 어떻게 사용되는지 테스트하는 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_loader import DataLoader
from models.parameters import GAParameters
import numpy as np

def test_parameter_usage():
    """고정값들의 실제 사용 예시 테스트"""
    print("=== 🧪 고정값 사용 예시 테스트 ===\n")
    
    try:
        # 데이터 로더 및 파라미터 생성
        data_loader = DataLoader()
        params = GAParameters(data_loader)
        
        print("1. 기본 고정값 확인:")
        print(f"   - CSHIP: ${params.CSHIP:,.0f}/TEU")
        print(f"   - CBAF: ${params.CBAF:,.0f}/TEU")
        print(f"   - CETA: ${params.CETA:,.0f}/일")
        print(f"   - KG_PER_TEU: {params.KG_PER_TEU:,.0f} KG")
        print(f"   - theta: {params.theta}")
        print(f"   - CEMPTY_SHIP: ${params.CEMPTY_SHIP:,.0f}/TEU")
        
        # 2. KG_PER_TEU 사용 예시
        print("\n2. KG_PER_TEU 사용 예시:")
        if params.D_ab:
            sample_route = list(params.D_ab.keys())[0]
            if sample_route in params.Q_r:
                kg_amount = params.Q_r[sample_route]
                teu_amount = params.D_ab[sample_route]
                calculated_teu = max(1, int(np.ceil(kg_amount / params.KG_PER_TEU)))
                
                print(f"   - 루트 {sample_route}:")
                print(f"     주문량: {kg_amount:,.0f} KG")
                print(f"     변환된 TEU: {teu_amount} TEU")
                print(f"     계산된 TEU: {calculated_teu} TEU")
                print(f"     계산 과정: {kg_amount:,.0f} ÷ {params.KG_PER_TEU:,.0f} = {kg_amount/params.KG_PER_TEU:.2f}")
                print(f"     반올림: {np.ceil(kg_amount/params.KG_PER_TEU):.0f}")
        
        # 3. theta 사용 예시
        print("\n3. theta (빈 컨테이너 비율) 사용 예시:")
        if params.CAP_v_r:
            sample_route = list(params.CAP_v_r.keys())[0]
            capacity = params.CAP_v_r[sample_route]
            expected_empty = params.theta * capacity
            
            print(f"   - 루트 {sample_route}:")
            print(f"     선박 용량: {capacity:,.0f} TEU")
            print(f"     theta: {params.theta}")
            print(f"     예상 빈 컨테이너: {expected_empty:.3f} TEU")
            print(f"     계산 과정: {capacity:,.0f} × {params.theta} = {expected_empty:.3f}")
            print(f"     비율: {params.theta * 100:.1f}%")
        
        # 4. 비용 계산 예시
        print("\n4. 비용 계산 예시:")
        sample_schedule_idx = 0
        sample_xF = 1000  # 1000 TEU
        sample_xE = 100   # 100 TEU
        sample_delay = 5  # 5일 지연
        
        # 기본 운송비
        shipping_cost = params.CSHIP * (sample_xF + sample_xE)
        baf_cost = params.CBAF * (sample_xF + sample_xE)
        eta_penalty = params.CETA * sample_delay * sample_xF
        empty_cost = params.CEMPTY_SHIP * sample_xE
        
        total_cost = shipping_cost + baf_cost + eta_penalty + empty_cost
        
        print(f"   - 샘플 스케줄 (1000 TEU Full, 100 TEU Empty, 5일 지연):")
        print(f"     기본 운송비: ${params.CSHIP:,.0f} × {sample_xF + sample_xE:,} = ${shipping_cost:,.0f}")
        print(f"     유류할증료: ${params.CBAF:,.0f} × {sample_xF + sample_xE:,} = ${baf_cost:,.0f}")
        print(f"     ETA 패널티: ${params.CETA:,.0f} × {sample_delay}일 × {sample_xF:,} = ${eta_penalty:,.0f}")
        print(f"     빈 컨테이너 비용: ${params.CEMPTY_SHIP:,.0f} × {sample_xE:,} = ${empty_cost:,.0f}")
        print(f"     총 비용: ${total_cost:,.0f}")
        
        # 5. 제약 조건 예시
        print("\n5. 제약 조건 예시:")
        if params.CAP_v_r:
            sample_route = list(params.CAP_v_r.keys())[0]
            capacity = params.CAP_v_r[sample_route]
            max_full = int(capacity * 0.8)  # 용량의 80%
            max_empty = int(params.theta * capacity)
            
            print(f"   - 루트 {sample_route} (용량: {capacity:,.0f} TEU):")
            print(f"     최대 Full 컨테이너: {max_full:,} TEU (용량의 80%)")
            print(f"     권장 Empty 컨테이너: {max_empty:.3f} TEU (theta × 용량)")
            print(f"     총 사용 가능: {max_full + max_empty:.3f} TEU")
            print(f"     여유 용량: {capacity - (max_full + max_empty):.3f} TEU")
        
        print("\n=== 🎯 테스트 완료 ===")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parameter_usage()
