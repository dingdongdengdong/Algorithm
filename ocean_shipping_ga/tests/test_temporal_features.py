#!/usr/bin/env python3
"""
시간적 복잡성 반영 기능 테스트 스크립트
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.parameters import GAParameters
from data.data_loader import DataLoader


def test_temporal_features():
    """시간적 복잡성 반영 기능 테스트"""
    print("🧪 시간적 복잡성 반영 기능 테스트 시작")
    print("=" * 60)
    
    try:
        # 1. 데이터 로더 테스트
        print("\n1️⃣ 데이터 로더 테스트")
        data_loader = DataLoader()
        print("✅ 데이터 로더 생성 성공")
        
        # 2. GA 파라미터 초기화 테스트
        print("\n2️⃣ GA 파라미터 초기화 테스트")
        params = GAParameters(data_loader, version='quick')
        print("✅ GA 파라미터 초기화 성공")
        
        # 3. 시간 기반 스케줄 정렬 테스트
        print("\n3️⃣ 시간 기반 스케줄 정렬 테스트")
        print(f"   - 총 스케줄 수: {len(params.I)}")
        print(f"   - 시간 범위: {params.time_horizon_start} ~ {params.time_horizon_end}")
        print(f"   - 시간 인덱스 매핑: {len(params.time_index_mapping)}개")
        
        # 시간 순서 확인
        first_schedule = params.I[0]
        last_schedule = params.I[-1]
        print(f"   - 첫 번째 스케줄: {first_schedule} (ETD: {params.ETD_i[first_schedule]})")
        print(f"   - 마지막 스케줄: {last_schedule} (ETD: {params.ETD_i[last_schedule]})")
        
        # 시간 순서 검증
        if params.ETD_i[first_schedule] <= params.ETD_i[last_schedule]:
            print("✅ 시간 순서 정렬 성공")
        else:
            print("❌ 시간 순서 정렬 실패")
            
        # 4. 시간별 스케줄 그룹화 테스트
        print("\n4️⃣ 시간별 스케줄 그룹화 테스트")
        print(f"   - 일별 스케줄: {len(params.daily_schedules)}일")
        print(f"   - 주별 스케줄: {len(params.weekly_schedules)}주")
        print(f"   - 월별 스케줄: {len(params.monthly_schedules)}개월")
        
        # 샘플 일별 스케줄 확인
        sample_date = list(params.daily_schedules.keys())[0]
        print(f"   - 샘플 날짜 {sample_date}: {len(params.daily_schedules[sample_date])}개 스케줄")
        
        # 5. 선박별 타임라인 테스트
        print("\n5️⃣ 선박별 타임라인 테스트")
        print(f"   - 총 선박 수: {len(params.vessel_timeline)}")
        
        # 샘플 선박 정보 확인
        sample_vessel = list(params.vessel_timeline.keys())[0]
        vessel_info = params.vessel_timeline[sample_vessel]
        print(f"   - 샘플 선박 '{sample_vessel}':")
        print(f"     * 스케줄 수: {len(vessel_info['schedules'])}")
        print(f"     * 재사용 가능: {vessel_info['reuse_possibility']['reusable']}")
        print(f"     * 평균 간격: {vessel_info['reuse_possibility']['avg_gap']:.1f}일")
        
        # 6. 항구별 타임라인 테스트
        print("\n6️⃣ 항구별 타임라인 테스트")
        print(f"   - 총 항구 수: {len(params.port_timeline)}")
        
        # 샘플 항구 정보 확인
        sample_port = list(params.port_timeline.keys())[0]
        port_info = params.port_timeline[sample_port]
        print(f"   - 샘플 항구 '{sample_port}':")
        print(f"     * 출발 스케줄: {len(port_info['departures'])}개")
        print(f"     * 도착 스케줄: {len(port_info['arrivals'])}개")
        print(f"     * 최대 일일 작업: {port_info['capacity_analysis']['max_daily_operations']}개")
        
        # 7. 시간 의존적 컨테이너 흐름 테스트
        print("\n7️⃣ 시간 의존적 컨테이너 흐름 테스트")
        
        # 테스트용 개체 생성
        test_individual = {
            'xF': np.random.uniform(100, 1000, len(params.I)),
            'xE': np.random.uniform(10, 100, len(params.I)),
            'y': np.zeros((len(params.I), len(params.P)))
        }
        
        # 컨테이너 흐름 계산
        y_result = params.calculate_empty_container_levels(test_individual)
        print(f"   - 컨테이너 흐름 계산 결과: {y_result.shape}")
        print(f"   - 평균 재고: {np.mean(y_result):.1f} TEU")
        
        # 8. 스케줄 충돌 검사 테스트
        print("\n8️⃣ 스케줄 충돌 검사 테스트")
        conflicts = params.get_schedule_conflicts(test_individual)
        print(f"   - 선박 충돌: {len(conflicts['vessel_conflicts'])}개")
        print(f"   - 항구 용량 초과: {len(conflicts['port_conflicts'])}개")
        print(f"   - 시간적 제약 위반: {len(conflicts['temporal_constraints'])}개")
        
        # 9. 시간적 실행 가능성 검증 테스트
        print("\n9️⃣ 시간적 실행 가능성 검증 테스트")
        validation = params.validate_temporal_feasibility(test_individual)
        print(f"   - 실행 가능: {validation['is_feasible']}")
        print(f"   - 패널티 점수: {validation['penalty_score']:.2f}")
        
        if not validation['is_feasible']:
            print("   - 개선 권장사항:")
            for rec in validation['recommendations']:
                print(f"     * {rec}")
        
        # 10. 특정 시점 컨테이너 흐름 테스트
        print("\n🔟 특정 시점 컨테이너 흐름 테스트")
        target_time = params.time_horizon_start + timedelta(days=30)
        flow_at_time = params.get_container_flow_at_time(test_individual, target_time)
        print(f"   - 타겟 시점: {target_time}")
        print(f"   - 항구별 재고:")
        for port, inventory in list(flow_at_time.items())[:3]:  # 처음 3개 항구만
            print(f"     * {port}: {inventory:.1f} TEU")
        
        print("\n✅ 모든 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """성능 테스트"""
    print("\n🚀 성능 테스트 시작")
    print("=" * 60)
    
    try:
        data_loader = DataLoader()
        params = GAParameters(data_loader, version='quick')
        
        # 테스트용 개체 생성
        test_individual = {
            'xF': np.random.uniform(100, 1000, len(params.I)),
            'xE': np.random.uniform(10, 100, len(params.I)),
            'y': np.zeros((len(params.I), len(params.P)))
        }
        
        import time
        
        # 컨테이너 흐름 계산 성능
        start_time = time.time()
        for _ in range(100):
            y_result = params.calculate_empty_container_levels(test_individual)
        flow_time = time.time() - start_time
        print(f"컨테이너 흐름 계산 (100회): {flow_time:.3f}초")
        
        # 충돌 검사 성능
        start_time = time.time()
        for _ in range(100):
            conflicts = params.get_schedule_conflicts(test_individual)
        conflict_time = time.time() - start_time
        print(f"충돌 검사 (100회): {conflict_time:.3f}초")
        
        # 실행 가능성 검증 성능
        start_time = time.time()
        for _ in range(100):
            validation = params.validate_temporal_feasibility(test_individual)
        validation_time = time.time() - start_time
        print(f"실행 가능성 검증 (100회): {validation_time:.3f}초")
        
        print("✅ 성능 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    print("🧬 해상 운송 GA - 시간적 복잡성 반영 기능 테스트")
    print("=" * 80)
    
    # 기본 기능 테스트
    success = test_temporal_features()
    
    if success:
        # 성능 테스트
        test_performance()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("�� 일부 테스트가 실패했습니다.")
