#!/usr/bin/env python3
"""
Empty Container 재배치 최적화 시스템
과잉지역에서 부족지역으로의 최적 Empty Container 배분 전략
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import heapq
from scipy.optimize import linear_sum_assignment
import warnings
warnings.filterwarnings('ignore')


@dataclass
class RedistributionPath:
    """재배치 경로 정보"""
    from_port: str
    to_port: str
    container_count: int
    distance: float
    cost: float
    estimated_time: int  # 일 단위
    priority: float  # 우선순위 (높을수록 중요)


class ContainerRedistributionOptimizer:
    """
    과잉지역에서 부족지역으로의 Empty Container 재배치 최적화
    """
    
    def __init__(self, params):
        """
        Parameters:
        -----------
        params : GAParameters
            GA 파라미터
        """
        self.params = params
        self.distance_matrix = self._initialize_distance_matrix()
        self.cost_per_teu_km = 0.1  # TEU당 km당 비용 (기본값)
        self.max_redistribution_distance = 10000  # 최대 재배치 거리 (km)
        
        # 재배치 비용 가중치
        self.distance_weight = 0.4
        self.urgency_weight = 0.3
        self.capacity_weight = 0.3
        
    def _initialize_distance_matrix(self) -> Dict[str, Dict[str, float]]:
        """항구간 거리 행렬 초기화"""
        # 실제 구현에서는 항구 좌표를 기반으로 계산
        # 여기서는 예시 데이터 사용
        
        # 주요 항구들의 대략적인 거리 (km)
        distances = {
            'BUSAN': {
                'LONG BEACH': 9500,
                'NEW YORK': 11000,
                'SAVANNAH': 12000,
                'HOUSTON': 11500,
                'MOBILE': 11800,
                'SEATTLE': 7500
            },
            'LONG BEACH': {
                'BUSAN': 9500,
                'NEW YORK': 4200,
                'SAVANNAH': 3800,
                'HOUSTON': 2200,
                'MOBILE': 2800,
                'SEATTLE': 1800
            },
            'NEW YORK': {
                'BUSAN': 11000,
                'LONG BEACH': 4200,
                'SAVANNAH': 1200,
                'HOUSTON': 2100,
                'MOBILE': 1800,
                'SEATTLE': 4000
            },
            'SAVANNAH': {
                'BUSAN': 12000,
                'LONG BEACH': 3800,
                'NEW YORK': 1200,
                'HOUSTON': 1400,
                'MOBILE': 800,
                'SEATTLE': 4200
            },
            'HOUSTON': {
                'BUSAN': 11500,
                'LONG BEACH': 2200,
                'NEW YORK': 2100,
                'SAVANNAH': 1400,
                'MOBILE': 600,
                'SEATTLE': 3200
            },
            'MOBILE': {
                'BUSAN': 11800,
                'LONG BEACH': 2800,
                'NEW YORK': 1800,
                'SAVANNAH': 800,
                'HOUSTON': 600,
                'SEATTLE': 3800
            },
            'SEATTLE': {
                'BUSAN': 7500,
                'LONG BEACH': 1800,
                'NEW YORK': 4000,
                'SAVANNAH': 4200,
                'HOUSTON': 3200,
                'MOBILE': 3800
            }
        }
        
        # 대각선 요소 (자기 자신)는 0
        for port in distances:
            distances[port][port] = 0.0
            
        return distances
    
    def identify_imbalance_ports(self, individual: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        과잉지역과 부족지역 항구 식별
        
        Parameters:
        -----------
        individual : Dict[str, Any]
            GA 개체
            
        Returns:
        --------
        Dict[str, List[str]]
            과잉/부족/균형 항구 목록
        """
        # 최종 컨테이너 수준 계산
        final_levels = self.params.calculate_empty_container_levels(individual)
        
        # 항구별 평균 재고 수준 계산
        port_averages = {}
        for p_idx, port in enumerate(self.params.P):
            port_averages[port] = np.mean(final_levels[:, p_idx])
        
        # 평균과 표준편차 계산
        all_levels = list(port_averages.values())
        mean_level = np.mean(all_levels)
        std_level = np.std(all_levels)
        
        # 임계값 설정
        excess_threshold = mean_level + 0.5 * std_level
        shortage_threshold = mean_level - 0.5 * std_level
        
        # 과잉/부족/균형 항구 분류
        excess_ports = []
        shortage_ports = []
        balanced_ports = []
        
        for port, level in port_averages.items():
            if level > excess_threshold:
                excess_ports.append(port)
            elif level < shortage_threshold:
                shortage_ports.append(port)
            else:
                balanced_ports.append(port)
        
        return {
            'excess_ports': excess_ports,
            'shortage_ports': shortage_ports,
            'balanced_ports': balanced_ports,
            'port_levels': port_averages,
            'statistics': {
                'mean': mean_level,
                'std': std_level,
                'excess_threshold': excess_threshold,
                'shortage_threshold': shortage_threshold
            }
        }
    
    def calculate_redistribution_cost(self, excess_ports: List[str], 
                                   shortage_ports: List[str]) -> float:
        """
        재배치 비용 계산
        
        Parameters:
        -----------
        excess_ports : List[str]
            과잉 항구 목록
        shortage_ports : List[str]
            부족 항구 목록
            
        Returns:
        --------
        float
            총 재배치 비용
        """
        total_cost = 0.0
        
        for excess_port in excess_ports:
            for shortage_port in shortage_ports:
                if excess_port != shortage_port:
                    distance = self.distance_matrix.get(excess_port, {}).get(shortage_port, float('inf'))
                    if distance < float('inf'):
                        # 기본 거리 비용
                        distance_cost = distance * self.cost_per_teu_km
                        
                        # 추가 비용 요소들
                        urgency_cost = self._calculate_urgency_cost(shortage_port)
                        capacity_cost = self._calculate_capacity_cost(excess_port, shortage_port)
                        
                        # 가중 평균 비용
                        total_path_cost = (
                            self.distance_weight * distance_cost +
                            self.urgency_weight * urgency_cost +
                            self.capacity_weight * capacity_cost
                        )
                        
                        total_cost += total_path_cost
        
        return total_cost
    
    def _calculate_urgency_cost(self, shortage_port: str) -> float:
        """부족 항구의 긴급도 비용 계산"""
        # 실제 구현에서는 수요 예측, 재고 수준 등을 고려
        # 여기서는 기본값 사용
        return 100.0  # 기본 긴급도 비용
    
    def _calculate_capacity_cost(self, excess_port: str, shortage_port: str) -> float:
        """용량 관련 비용 계산"""
        # 실제 구현에서는 항구 처리 능력, 혼잡도 등을 고려
        # 여기서는 기본값 사용
        return 50.0  # 기본 용량 비용
    
    def optimize_redistribution_paths(self, excess_ports: List[str], 
                                    shortage_ports: List[str],
                                    max_containers_per_path: int = 1000) -> List[RedistributionPath]:
        """
        최적 재배치 경로 결정
        
        Parameters:
        -----------
        excess_ports : List[str]
            과잉 항구 목록
        shortage_ports : List[str]
            부족 항구 목록
        max_containers_per_path : int
            경로당 최대 컨테이너 수
            
        Returns:
        --------
        List[RedistributionPath]
            최적 재배치 경로 목록
        """
        if not excess_ports or not shortage_ports:
            return []
        
        # 1. 모든 가능한 경로 생성
        all_paths = []
        for excess_port in excess_ports:
            for shortage_port in shortage_ports:
                if excess_port != shortage_port:
                    distance = self.distance_matrix.get(excess_port, {}).get(shortage_port, float('inf'))
                    if distance < float('inf') and distance <= self.max_redistribution_distance:
                        # 우선순위 계산
                        priority = self._calculate_path_priority(excess_port, shortage_port, distance)
                        
                        path = RedistributionPath(
                            from_port=excess_port,
                            to_port=shortage_port,
                            container_count=0,  # 나중에 결정
                            distance=distance,
                            cost=distance * self.cost_per_teu_km,
                            estimated_time=int(distance / 500),  # 500km/일 속도 가정
                            priority=priority
                        )
                        all_paths.append(path)
        
        # 2. 우선순위별 정렬
        all_paths.sort(key=lambda x: x.priority, reverse=True)
        
        # 3. 헝가리안 알고리즘을 사용한 최적 매칭
        optimal_paths = self._hungarian_matching(all_paths, max_containers_per_path)
        
        return optimal_paths
    
    def _calculate_path_priority(self, excess_port: str, shortage_port: str, distance: float) -> float:
        """경로 우선순위 계산"""
        # 거리가 가까울수록 높은 우선순위
        distance_score = 1.0 / (1.0 + distance / 1000)
        
        # 항구 중요도 (실제 구현에서는 경제적 중요도 등 고려)
        port_importance = {
            'BUSAN': 0.9,
            'LONG BEACH': 0.8,
            'NEW YORK': 0.9,
            'SAVANNAH': 0.7,
            'HOUSTON': 0.8,
            'MOBILE': 0.6,
            'SEATTLE': 0.7
        }
        
        importance_score = (
            port_importance.get(excess_port, 0.5) +
            port_importance.get(shortage_port, 0.5)
        ) / 2
        
        # 최종 우선순위
        priority = 0.6 * distance_score + 0.4 * importance_score
        return priority
    
    def _hungarian_matching(self, paths: List[RedistributionPath], 
                          max_containers: int) -> List[RedistributionPath]:
        """
        헝가리안 알고리즘을 사용한 최적 매칭
        """
        if not paths:
            return []
        
        # 비용 행렬 생성
        excess_ports = list(set(p.from_port for p in paths))
        shortage_ports = list(set(p.to_port for p in paths))
        
        cost_matrix = np.full((len(excess_ports), len(shortage_ports)), float('inf'))
        
        for i, excess_port in enumerate(excess_ports):
            for j, shortage_port in enumerate(shortage_ports):
                # 해당 경로 찾기
                path = next((p for p in paths 
                           if p.from_port == excess_port and p.to_port == shortage_port), None)
                if path:
                    cost_matrix[i, j] = path.cost
        
        # 무한대 값 처리
        max_cost = np.max(cost_matrix[cost_matrix < float('inf')])
        cost_matrix[cost_matrix == float('inf')] = max_cost * 2
        
        # 헝가리안 알고리즘 실행
        try:
            row_indices, col_indices = linear_sum_assignment(cost_matrix)
            
            # 최적 경로 선택
            optimal_paths = []
            for row_idx, col_idx in zip(row_indices, col_indices):
                excess_port = excess_ports[row_idx]
                shortage_port = shortage_ports[col_idx]
                
                # 해당 경로 찾기
                path = next((p for p in paths 
                           if p.from_port == excess_port and p.to_port == shortage_port), None)
                if path:
                    # 컨테이너 수 결정
                    path.container_count = min(max_containers, 
                                            self._estimate_redistribution_amount(excess_port, shortage_port))
                    optimal_paths.append(path)
            
            return optimal_paths
            
        except Exception as e:
            print(f"헝가리안 알고리즘 실행 실패: {e}")
            # 폴백: 우선순위 기반 선택
            return paths[:min(len(paths), len(excess_ports))]
    
    def _estimate_redistribution_amount(self, excess_port: str, shortage_port: str) -> int:
        """재배치 컨테이너 수 추정"""
        # 실제 구현에서는 과잉량과 부족량을 정확히 계산
        # 여기서는 기본값 사용
        base_amount = 500  # 기본 재배치량
        
        # 거리에 따른 조정
        distance = self.distance_matrix.get(excess_port, {}).get(shortage_port, 1000)
        if distance > 5000:
            base_amount = int(base_amount * 0.7)  # 장거리는 감소
        elif distance < 1000:
            base_amount = int(base_amount * 1.3)  # 단거리는 증가
        
        return max(100, base_amount)  # 최소 100 TEU
    
    def generate_redistribution_plan(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """
        전체 재배치 계획 생성
        
        Parameters:
        -----------
        individual : Dict[str, Any]
            GA 개체
            
        Returns:
        --------
        Dict[str, Any]
            재배치 계획 및 분석 결과
        """
        # 1. 불균형 항구 식별
        imbalance_info = self.identify_imbalance_ports(individual)
        
        # 2. 재배치 비용 계산
        redistribution_cost = self.calculate_redistribution_cost(
            imbalance_info['excess_ports'], 
            imbalance_info['shortage_ports']
        )
        
        # 3. 최적 경로 결정
        optimal_paths = self.optimize_redistribution_paths(
            imbalance_info['excess_ports'], 
            imbalance_info['shortage_ports']
        )
        
        # 4. 계획 요약
        total_containers = sum(path.container_count for path in optimal_paths)
        total_distance = sum(path.distance * path.container_count for path in optimal_paths)
        total_cost = sum(path.cost * path.container_count for path in optimal_paths)
        
        # 5. 결과 반환
        return {
            'imbalance_analysis': imbalance_info,
            'redistribution_paths': optimal_paths,
            'summary': {
                'total_containers': total_containers,
                'total_distance': total_distance,
                'total_cost': total_cost,
                'path_count': len(optimal_paths),
                'excess_port_count': len(imbalance_info['excess_ports']),
                'shortage_port_count': len(imbalance_info['shortage_ports'])
            },
            'recommendations': self._generate_recommendations(imbalance_info, optimal_paths)
        }
    
    def _generate_recommendations(self, imbalance_info: Dict[str, Any], 
                                paths: List[RedistributionPath]) -> List[str]:
        """재배치 권장사항 생성"""
        recommendations = []
        
        # 1. 과잉 항구 권장사항
        if imbalance_info['excess_ports']:
            excess_ports_str = ', '.join(imbalance_info['excess_ports'])
            recommendations.append(f"과잉 항구 ({excess_ports_str})에서 Empty Container를 적극적으로 활용하거나 재배치하세요.")
        
        # 2. 부족 항구 권장사항
        if imbalance_info['shortage_ports']:
            shortage_ports_str = ', '.join(imbalance_info['shortage_ports'])
            recommendations.append(f"부족 항구 ({shortage_ports_str})에 대한 Empty Container 공급을 우선적으로 고려하세요.")
        
        # 3. 비용 최적화 권장사항
        if paths:
            avg_cost = np.mean([path.cost for path in paths])
            recommendations.append(f"평균 재배치 비용: ${avg_cost:.2f}/TEU. 비용 효율적인 경로를 우선 선택하세요.")
        
        # 4. 시간적 고려사항
        if paths:
            avg_time = np.mean([path.estimated_time for path in paths])
            recommendations.append(f"평균 재배치 소요시간: {avg_time:.1f}일. 긴급한 경우 단거리 경로를 우선 고려하세요.")
        
        return recommendations
    
    def print_redistribution_plan(self, plan: Dict[str, Any]):
        """재배치 계획 출력"""
        print("\n" + "="*80)
        print("🚢 EMPTY CONTAINER 재배치 계획")
        print("="*80)
        
        # 불균형 분석 결과
        imbalance = plan['imbalance_analysis']
        print(f"\n📊 불균형 분석 결과:")
        print(f"   과잉 항구: {imbalance['excess_ports']}")
        print(f"   부족 항구: {imbalance['shortage_ports']}")
        print(f"   균형 항구: {imbalance['balanced_ports']}")
        
        # 재배치 경로
        print(f"\n🛣️  재배치 경로 ({len(plan['redistribution_paths'])}개):")
        for i, path in enumerate(plan['redistribution_paths'], 1):
            print(f"   {i:2d}. {path.from_port:12s} → {path.to_port:12s} | "
                  f"{path.container_count:5d} TEU | "
                  f"{path.distance:6.0f} km | ${path.cost:6.1f}")
        
        # 요약 정보
        summary = plan['summary']
        print(f"\n📈 계획 요약:")
        print(f"   총 재배치량: {summary['total_containers']:,} TEU")
        print(f"   총 거리: {summary['total_distance']:,.0f} km")
        print(f"   총 비용: ${summary['total_cost']:,.0f}")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        for i, rec in enumerate(plan['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        print("="*80)
