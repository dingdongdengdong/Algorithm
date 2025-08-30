#!/usr/bin/env python3
"""
Empty Container 재배치 최적화 시스템 데모
과잉지역에서 부족지역으로의 최적 Empty Container 배분 전략 시연
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ga_optimizer import OceanShippingGA
from models.redistribution_optimizer import ContainerRedistributionOptimizer
from models.parameters import GAParameters
from data.data_loader import DataLoader


def create_sample_individual(params: GAParameters) -> dict:
    """테스트용 샘플 개체 생성"""
    print("🔧 테스트용 샘플 개체 생성 중...")
    
    # 기본 개체 구조
    individual = {
        'xF': np.zeros(params.num_schedules),  # Full 컨테이너
        'xE': np.zeros(params.num_schedules),  # Empty 컨테이너
        'y': np.zeros((params.num_schedules, params.num_ports))  # 빈 컨테이너 재고
    }
    
    # 랜덤 값으로 초기화 (현실적인 범위)
    for i in range(params.num_schedules):
        # Full 컨테이너: 100-1000 TEU
        individual['xF'][i] = np.random.randint(100, 1001)
        
        # Empty 컨테이너: 50-500 TEU
        individual['xE'][i] = np.random.randint(50, 501)
    
    # y 값 계산
    individual['y'] = params.calculate_empty_container_levels(individual)
    
    print(f"✅ 샘플 개체 생성 완료:")
    print(f"   - 스케줄 수: {params.num_schedules}")
    print(f"   - 항구 수: {params.num_ports}")
    print(f"   - 총 Full 컨테이너: {np.sum(individual['xF']):,} TEU")
    print(f"   - 총 Empty 컨테이너: {np.sum(individual['xE']):,} TEU")
    
    return individual


def demo_imbalance_detection(optimizer: ContainerRedistributionOptimizer, 
                           individual: dict):
    """불균형 감지 데모"""
    print("\n" + "="*60)
    print("🔍 1단계: 컨테이너 불균형 감지")
    print("="*60)
    
    # 불균형 항구 식별
    imbalance_info = optimizer.identify_imbalance_ports(individual)
    
    print(f"📊 불균형 분석 결과:")
    print(f"   과잉 항구: {imbalance_info['excess_ports']}")
    print(f"   부족 항구: {imbalance_info['shortage_ports']}")
    print(f"   균형 항구: {imbalance_info['balanced_ports']}")
    
    # 통계 정보
    stats = imbalance_info['statistics']
    print(f"\n📈 통계 정보:")
    print(f"   평균 재고 수준: {stats['mean']:.1f} TEU")
    print(f"   표준편차: {stats['std']:.1f} TEU")
    print(f"   과잉 임계값: {stats['excess_threshold']:.1f} TEU")
    print(f"   부족 임계값: {stats['shortage_threshold']:.1f} TEU")
    
    # 항구별 상세 정보
    print(f"\n🏠 항구별 재고 수준:")
    for port, level in imbalance_info['port_levels'].items():
        status = "과잉" if port in imbalance_info['excess_ports'] else \
                "부족" if port in imbalance_info['shortage_ports'] else "균형"
        print(f"   {port:12s}: {level:8.1f} TEU ({status})")
    
    return imbalance_info


def demo_cost_calculation(optimizer: ContainerRedistributionOptimizer,
                         imbalance_info: dict):
    """재배치 비용 계산 데모"""
    print("\n" + "="*60)
    print("💰 2단계: 재배치 비용 계산")
    print("="*60)
    
    excess_ports = imbalance_info['excess_ports']
    shortage_ports = imbalance_info['shortage_ports']
    
    if not excess_ports or not shortage_ports:
        print("⚠️ 과잉 항구 또는 부족 항구가 없어 재배치가 불가능합니다.")
        return 0.0
    
    # 재배치 비용 계산
    total_cost = optimizer.calculate_redistribution_cost(excess_ports, shortage_ports)
    
    print(f"📊 재배치 비용 분석:")
    print(f"   과잉 항구 수: {len(excess_ports)}")
    print(f"   부족 항구 수: {len(shortage_ports)}")
    print(f"   가능한 경로 수: {len(excess_ports) * len(shortage_ports)}")
    print(f"   총 재배치 비용: ${total_cost:,.2f}")
    
    # 경로별 상세 비용
    print(f"\n🛣️  경로별 비용 분석:")
    for excess_port in excess_ports:
        for shortage_port in shortage_ports:
            if excess_port != shortage_port:
                distance = optimizer.distance_matrix.get(excess_port, {}).get(shortage_port, float('inf'))
                if distance < float('inf'):
                    cost = distance * optimizer.cost_per_teu_km
                    print(f"   {excess_port:12s} → {shortage_port:12s}: "
                          f"{distance:6.0f} km, ${cost:6.1f}")
    
    return total_cost


def demo_path_optimization(optimizer: ContainerRedistributionOptimizer,
                          imbalance_info: dict):
    """경로 최적화 데모"""
    print("\n" + "="*60)
    print("🎯 3단계: 최적 재배치 경로 결정")
    print("="*60)
    
    excess_ports = imbalance_info['excess_ports']
    shortage_ports = imbalance_info['shortage_ports']
    
    if not excess_ports or not shortage_ports:
        print("⚠️ 과잉 항구 또는 부족 항구가 없어 경로 최적화가 불가능합니다.")
        return []
    
    # 최적 경로 결정
    optimal_paths = optimizer.optimize_redistribution_paths(excess_ports, shortage_ports)
    
    print(f"📊 경로 최적화 결과:")
    print(f"   생성된 경로 수: {len(optimal_paths)}")
    
    if optimal_paths:
        print(f"\n🏆 최적 경로 (우선순위 순):")
        for i, path in enumerate(optimal_paths, 1):
            print(f"   {i:2d}. {path.from_port:12s} → {path.to_port:12s}")
            print(f"       거리: {path.distance:6.0f} km")
            print(f"       비용: ${path.cost:6.1f}")
            print(f"       예상 소요시간: {path.estimated_time}일")
            print(f"       우선순위: {path.priority:.3f}")
            print(f"       추정 컨테이너 수: {path.container_count} TEU")
            print()
    
    return optimal_paths


def demo_complete_plan(optimizer: ContainerRedistributionOptimizer,
                      individual: dict):
    """전체 재배치 계획 데모"""
    print("\n" + "="*60)
    print("🚢 4단계: 전체 재배치 계획 생성")
    print("="*60)
    
    # 전체 재배치 계획 생성
    redistribution_plan = optimizer.generate_redistribution_plan(individual)
    
    # 계획 출력
    optimizer.print_redistribution_plan(redistribution_plan)
    
    return redistribution_plan


def demo_integration_with_ga():
    """GA 시스템과의 통합 데모"""
    print("\n" + "="*60)
    print("🔗 5단계: GA 시스템과의 통합 데모")
    print("="*60)
    
    # GA 시스템 초기화
    file_paths = {
        'schedule': 'data/스해물_스케줄data.xlsx',
        'delayed': 'data/스해물_딜레이스케줄data.xlsx',
        'vessel': 'data/스해물_선박data.xlsx',
        'port': 'data/스해물_항구위치data.xlsx',
        'fixed': 'data/스해물_고정값data.xlsx'
    }
    
    try:
        print("🔧 GA 시스템 초기화 중...")
        ga = OceanShippingGA(file_paths, version='quick')
        print("✅ GA 시스템 초기화 완료")
        
        # 샘플 개체 생성
        sample_individual = create_sample_individual(ga.params)
        
        # GA 시스템을 통한 불균형 분석
        print("\n📊 GA 시스템을 통한 불균형 분석:")
        imbalance_analysis = ga.analyze_container_imbalance(sample_individual)
        
        print(f"   분석 완료: {len(imbalance_analysis['imbalance_analysis']['excess_ports'])}개 과잉 항구, "
              f"{len(imbalance_analysis['imbalance_analysis']['shortage_ports'])}개 부족 항구")
        
        # GA 시스템을 통한 재배치 최적화
        print("\n🎯 GA 시스템을 통한 재배치 최적화:")
        redistribution_plan = ga.optimize_redistribution(sample_individual)
        
        print(f"   최적화 완료: {redistribution_plan['summary']['path_count']}개 경로, "
              f"{redistribution_plan['summary']['total_containers']:,} TEU 재배치")
        
        return ga, sample_individual
        
    except Exception as e:
        print(f"❌ GA 시스템 초기화 실패: {e}")
        print("   데이터 파일 경로를 확인해주세요.")
        return None, None


def main():
    """메인 데모 함수"""
    print("🚢 Empty Container 재배치 최적화 시스템 데모")
    print("="*80)
    print("이 데모는 과잉지역에서 부족지역으로의 Empty Container 재배치를")
    print("최적화하는 시스템의 기능을 단계별로 시연합니다.")
    print("="*80)
    
    # 1. 기본 재배치 최적화 시스템 테스트
    print("\n🔧 재배치 최적화 시스템 테스트")
    
    # 데이터 로더로 기본 파라미터 생성
    try:
        file_paths = {
            'schedule': 'data/스해물_스케줄data.xlsx',
            'delayed': 'data/스해물_딜레이스케줄data.xlsx',
            'vessel': 'data/스해물_선박data.xlsx',
            'port': 'data/스해물_항구위치data.xlsx',
            'fixed': 'data/스해물_고정값data.xlsx'
        }
        
        data_loader = DataLoader(file_paths)
        data_loader.load_all_data()
        
        params = GAParameters(data_loader, version='quick')
        optimizer = ContainerRedistributionOptimizer(params)
        
        print("✅ 재배치 최적화 시스템 초기화 완료")
        
        # 샘플 개체 생성
        sample_individual = create_sample_individual(params)
        
        # 단계별 데모 실행
        imbalance_info = demo_imbalance_detection(optimizer, sample_individual)
        cost = demo_cost_calculation(optimizer, imbalance_info)
        paths = demo_path_optimization(optimizer, imbalance_info)
        plan = demo_complete_plan(optimizer, sample_individual)
        
        # 2. GA 시스템과의 통합 테스트
        ga, ga_individual = demo_integration_with_ga()
        
        print("\n" + "="*80)
        print("🎉 데모 완료!")
        print("="*80)
        
        if ga:
            print("✅ GA 시스템과의 통합 성공")
            print("   이제 GA 최적화 실행 시 자동으로 재배치 계획이 생성됩니다.")
        else:
            print("⚠️ GA 시스템과의 통합 실패")
            print("   데이터 파일이 올바른 위치에 있는지 확인해주세요.")
        
        print("\n💡 다음 단계:")
        print("   1. GA 최적화 실행: python run.py")
        print("   2. 재배치 계획 확인: GA 결과 출력 시 자동 표시")
        print("   3. 수동 재배치 최적화: ga.optimize_redistribution()")
        
    except Exception as e:
        print(f"❌ 데모 실행 실패: {e}")
        print("   오류 상세 정보:")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
