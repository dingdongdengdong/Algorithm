"""
적합도 계산 클래스
"""

import numpy as np
from typing import Dict, Any
from models.parameters import GAParameters
from config import get_constant


class FitnessCalculator:
    """
    LP 모델 기반 적합도 계산 클래스 (균형 최적화 목적함수 포함)
    """
    
    def __init__(self, params: GAParameters):
        """
        Parameters:
        -----------
        params : GAParameters
            GA 및 LP 모델 파라미터
        """
        self.params = params
        
        # 균형 최적화를 위한 가중치 설정 (설정 파일에서 로드)
        self.cost_weight = get_constant('genetic_algorithm.fitness.cost_weight', 0.7)      # 비용 최적화 가중치 (α)
        self.balance_weight = get_constant('genetic_algorithm.fitness.balance_weight', 0.3)   # 균형 최적화 가중치 (β)
        
        # 균형 목적함수 설정
        self.enable_balance_optimization = True
        self.imbalance_penalty_scale = get_constant('genetic_algorithm.fitness.imbalance_penalty_scale', 1000)  # 불균형 패널티 스케일
        
    def calculate_fitness(self, individual: Dict[str, Any]) -> float:
        """균형 최적화가 포함된 적합도 계산"""
        
        # 1. 기본 LP 목적함수 비용 계산
        total_cost = self._calculate_base_cost(individual)
        
        # 2. LP 제약 조건 패널티
        constraint_penalty = self.calculate_lp_constraint_penalties(individual)
        
        # 3. 균형 최적화 목적함수 계산
        if self.enable_balance_optimization:
            imbalance_penalty = self._calculate_imbalance_penalty(individual)
            
            # 가중 목적함수: minimize (α * 총비용 + β * 불균형패널티)
            weighted_objective = (self.cost_weight * total_cost + 
                                self.balance_weight * imbalance_penalty)
            
            # 적합도 = -(가중 목적함수 + 제약조건 패널티)
            fitness = -(weighted_objective + constraint_penalty)
        else:
            # 기존 방식: 비용만 최적화
            fitness = -(total_cost + constraint_penalty)
        
        individual['fitness'] = fitness
        return fitness
    
    def _calculate_base_cost(self, individual: Dict[str, Any]) -> float:
        """기본 LP 목적함수 비용 계산"""
        total_cost = 0
        
        # LP 목적함수: minimize Σ CSHIP*(xF+xE) + Σ CBAF*(xF+xE) + Σ CETA*DELAY*xF
        for idx, i in enumerate(self.params.I):
            # 1. 운송비 (Full + Empty)
            shipping_cost = self.params.CSHIP * (individual['xF'][idx] + individual['xE'][idx])
            
            # 2. 유류할증료 (Full + Empty)  
            baf_cost = self.params.CBAF * (individual['xF'][idx] + individual['xE'][idx])
            
            # 3. ETA 패널티 (Full 컨테이너만)
            eta_penalty = self.params.CETA * self.params.DELAY_i.get(i, 0) * individual['xF'][idx]
            
            total_cost += shipping_cost + baf_cost + eta_penalty
            
        return total_cost
    
    def set_balance_optimization_weights(self, cost_weight: float, balance_weight: float):
        """균형 최적화 가중치 설정
        
        Parameters:
        -----------
        cost_weight : float
            비용 최적화 가중치 (α)
        balance_weight : float  
            균형 최적화 가중치 (β)
        """
        if cost_weight + balance_weight != 1.0:
            raise ValueError("가중치의 합은 1.0이어야 합니다")
        
        self.cost_weight = cost_weight
        self.balance_weight = balance_weight
    
    def enable_balance_optimization_mode(self, enable: bool = True):
        """균형 최적화 모드 활성화/비활성화"""
        self.enable_balance_optimization = enable
    
    def set_imbalance_penalty_scale(self, scale: float):
        """불균형 패널티 스케일 설정"""
        self.imbalance_penalty_scale = max(0, scale)
    
    def get_detailed_fitness_breakdown(self, individual: Dict[str, Any]) -> Dict[str, float]:
        """상세한 적합도 구성 요소 분석"""
        base_cost = self._calculate_base_cost(individual)
        constraint_penalty = self.calculate_lp_constraint_penalties(individual)
        
        breakdown = {
            'base_cost': base_cost,
            'constraint_penalty': constraint_penalty,
            'imbalance_penalty': 0,
            'weighted_objective': base_cost,
            'final_fitness': -(base_cost + constraint_penalty)
        }
        
        if self.enable_balance_optimization:
            imbalance_penalty = self._calculate_imbalance_penalty(individual)
            weighted_objective = (self.cost_weight * base_cost + 
                                self.balance_weight * imbalance_penalty)
            
            breakdown.update({
                'imbalance_penalty': imbalance_penalty,
                'weighted_objective': weighted_objective,
                'final_fitness': -(weighted_objective + constraint_penalty)
            })
        
        return breakdown
    
    def _calculate_imbalance_penalty(self, individual: Dict[str, Any]) -> float:
        """불균형 패널티 계산 - 과잉지역과 부족지역 간 차이를 최소화"""
        
        # 1. 항구별 최종 컨테이너 수준 계산
        final_levels = self.params.calculate_empty_container_levels(individual)
        
        if final_levels is None or final_levels.size == 0:
            return 0
        
        # 2. 항구별 평균 재고 수준
        port_levels = []
        for p_idx in range(len(self.params.P)):
            # 각 항구의 최근 스케줄들의 평균 수준
            port_recent_levels = final_levels[-min(3, len(final_levels)):, p_idx]
            avg_level = np.mean(port_recent_levels) if len(port_recent_levels) > 0 else 0
            port_levels.append(max(0, avg_level))  # 음수 방지
        
        port_levels = np.array(port_levels)
        
        if len(port_levels) == 0 or np.sum(port_levels) == 0:
            return 0
        
        # 3. 불균형 지수 계산 방법들
        
        # 방법 1: 표준편차 기반 불균형 (변동성 최소화)
        mean_level = np.mean(port_levels)
        std_level = np.std(port_levels)
        variance_penalty = std_level ** 2  # 분산 패널티
        
        # 방법 2: 지니 계수 (불평등 측정)
        gini_coefficient = self._calculate_gini_coefficient(port_levels)
        gini_penalty = gini_coefficient * np.sum(port_levels)
        
        # 방법 3: 과잉-부족 불일치 패널티
        excess_shortage_penalty = self._calculate_excess_shortage_mismatch(port_levels, mean_level)
        
        # 방법 4: 항구별 임계값 위반 패널티
        threshold_penalty = self._calculate_threshold_violation_penalty(port_levels, mean_level)
        
        # 방법 5: 재배치 필요량 기반 패널티
        redistribution_penalty = self._calculate_redistribution_demand_penalty(port_levels)
        
        # 가중 합계로 최종 불균형 패널티 계산
        total_imbalance_penalty = (
            0.3 * variance_penalty +           # 30% - 전반적 변동성
            0.2 * gini_penalty +               # 20% - 불평등 수준  
            0.25 * excess_shortage_penalty +   # 25% - 과잉-부족 미스매치
            0.15 * threshold_penalty +         # 15% - 임계값 위반
            0.1 * redistribution_penalty       # 10% - 재배치 필요량
        )
        
        return total_imbalance_penalty * self.imbalance_penalty_scale
    
    def _calculate_gini_coefficient(self, levels: np.ndarray) -> float:
        """지니 계수 계산 (0: 완전균등, 1: 완전불평등)"""
        if len(levels) == 0 or np.sum(levels) == 0:
            return 0
        
        # 음수 제거 및 정렬
        levels = np.maximum(levels, 0)
        levels = np.sort(levels)
        
        n = len(levels)
        total = np.sum(levels)
        
        if total == 0:
            return 0
        
        # 지니 계수 계산
        cumsum = np.cumsum(levels)
        gini = (2 * np.sum((np.arange(1, n + 1) * levels))) / (n * total) - (n + 1) / n
        
        return max(0, min(1, gini))  # 0-1 범위로 제한
    
    def _calculate_excess_shortage_mismatch(self, port_levels: np.ndarray, mean_level: float) -> float:
        """과잉-부족 불일치 패널티"""
        if len(port_levels) == 0 or mean_level <= 0:
            return 0
        
        # 표준편차 기반 임계값 설정
        std_level = np.std(port_levels)
        excess_threshold = mean_level + 0.5 * std_level
        shortage_threshold = mean_level - 0.5 * std_level
        
        # 과잉량과 부족량 계산
        excess_amount = np.sum(np.maximum(port_levels - excess_threshold, 0))
        shortage_amount = np.sum(np.maximum(shortage_threshold - port_levels, 0))
        
        # 불일치량 (과잉량과 부족량이 균형을 이루지 못하는 정도)
        mismatch = abs(excess_amount - shortage_amount)
        
        # 전체 불균형 강도
        total_imbalance = excess_amount + shortage_amount
        
        return mismatch + 0.5 * total_imbalance
    
    def _calculate_threshold_violation_penalty(self, port_levels: np.ndarray, mean_level: float) -> float:
        """임계값 위반 패널티"""
        if len(port_levels) == 0 or mean_level <= 0:
            return 0
        
        penalty = 0
        
        # 동적 임계값 계산
        std_level = np.std(port_levels)
        
        # 심각한 부족 임계값 (평균의 20%)
        critical_shortage_threshold = mean_level * 0.2
        # 부족 임계값 (평균의 40%) 
        shortage_threshold = mean_level * 0.4
        # 과잉 임계값 (평균의 160%)
        excess_threshold = mean_level * 1.6
        # 심각한 과잉 임계값 (평균의 200%)
        critical_excess_threshold = mean_level * 2.0
        
        for level in port_levels:
            if level <= critical_shortage_threshold:
                penalty += (critical_shortage_threshold - level) * 5  # 5배 패널티
            elif level <= shortage_threshold:
                penalty += (shortage_threshold - level) * 2          # 2배 패널티
            elif level >= critical_excess_threshold:
                penalty += (level - critical_excess_threshold) * 3   # 3배 패널티
            elif level >= excess_threshold:
                penalty += (level - excess_threshold) * 1            # 1배 패널티
        
        return penalty
    
    def _calculate_redistribution_demand_penalty(self, port_levels: np.ndarray) -> float:
        """재배치 필요량 기반 패널티"""
        if len(port_levels) == 0:
            return 0
        
        # 중위수를 목표 수준으로 사용
        target_level = np.median(port_levels)
        
        # 각 항구에서 목표 수준까지의 재배치 필요량
        redistribution_needs = np.abs(port_levels - target_level)
        
        # 총 재배치 필요량 (TEU-km 단위로 근사)
        # 실제로는 거리 정보가 필요하지만, 여기서는 단순화
        total_redistribution_demand = np.sum(redistribution_needs)
        
        # 재배치 복잡도 (항구 간 차이의 제곱합)
        redistribution_complexity = np.sum(redistribution_needs ** 2)
        
        return total_redistribution_demand + 0.1 * redistribution_complexity
    
    def calculate_penalties(self, individual: Dict[str, Any]) -> float:
        """기본 제약 조건 위반 패널티 계산"""
        penalty = 0
        
        # 1. 수요 충족 제약
        for r in self.params.R:
            if r in self.params.D_ab:
                # 해당 루트의 스케줄 찾기
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = 0
                for i in route_schedules:
                    if i in self.params.I:
                        idx = self.params.I.index(i)
                        total_full += individual['xF'][idx]
                
                # 수요 미충족 시 패널티
                if total_full < self.params.D_ab[r]:
                    penalty += (self.params.D_ab[r] - total_full)
        
        # 2. 용량 제약
        for r in self.params.R:
            if r in self.params.CAP_v_r:
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_containers = 0
                for i in route_schedules:
                    if i in self.params.I:
                        idx = self.params.I.index(i)
                        total_containers += individual['xF'][idx] + individual['xE'][idx]
                
                # 용량 초과 시 패널티
                if total_containers > self.params.CAP_v_r[r]:
                    penalty += (total_containers - self.params.CAP_v_r[r])
        
        # 3. 비음 제약
        penalty += np.sum(np.abs(individual['xF'][individual['xF'] < 0]))
        penalty += np.sum(np.abs(individual['xE'][individual['xE'] < 0]))
        penalty += np.sum(np.abs(individual['y'][individual['y'] < 0]))
        
        return penalty
    
    def calculate_enhanced_penalties(self, individual: Dict[str, Any]) -> float:
        """개선된 제약 조건 위반 패널티 계산"""
        penalty = 0
        
        # 1. 수요 충족 제약 (높은 우선순위)
        demand_penalty = 0
        for r in self.params.R:
            if r in self.params.D_ab:
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = 0
                for i in route_schedules:
                    if i in self.params.I:
                        idx = self.params.I.index(i)
                        total_full += individual['xF'][idx]
                
                demand = self.params.D_ab[r]
                # LP 모델: xF_r = D_ab (정확히 일치해야 함)
                if abs(total_full - demand) > 0.1:  # 허용 오차 0.1 TEU
                    diff = abs(total_full - demand)
                    demand_penalty += diff * 500  # 강한 패널티
        
        # 2. 용량 제약 (중간 우선순위)
        capacity_penalty = 0
        for r in self.params.R:
            if r in self.params.CAP_v_r:
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_containers = 0
                for i in route_schedules:
                    if i in self.params.I:
                        idx = self.params.I.index(i)
                        total_containers += individual['xF'][idx] + individual['xE'][idx]
                
                capacity = self.params.CAP_v_r[r]
                if total_containers > capacity:
                    excess = total_containers - capacity
                    capacity_penalty += excess * 200
        
        # 3. 비음 제약 (기본 제약)
        non_negative_penalty = 0
        non_negative_penalty += np.sum(np.abs(individual['xF'][individual['xF'] < 0])) * 1000
        non_negative_penalty += np.sum(np.abs(individual['xE'][individual['xE'] < 0])) * 1000
        non_negative_penalty += np.sum(np.abs(individual['y'][individual['y'] < 0])) * 1000
        
        # 4. 빈 컨테이너 제약
        empty_constraint_penalty = 0
        for r in self.params.R:
            if r in self.params.CAP_v_r:
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                expected_empty = self.params.theta * self.params.CAP_v_r[r]
                
                for i in route_schedules:
                    if i in self.params.I:
                        idx = self.params.I.index(i)
                        actual_empty = individual['xE'][idx]
                        
                        if abs(actual_empty - expected_empty) > 0.1:  # 허용 오차
                            diff = abs(actual_empty - expected_empty)
                            empty_constraint_penalty += diff * 200
        
        # 5. 빈 컨테이너 과다 비율 패널티
        empty_excess_penalty = 0
        for r in self.params.R:
            route_schedules = self.params.schedule_data[
                self.params.schedule_data['루트번호'] == r
            ]['스케줄 번호'].unique()
            
            total_full = 0
            total_empty = 0
            for i in route_schedules:
                if i in self.params.I:
                    idx = self.params.I.index(i)
                    total_full += individual['xF'][idx]
                    total_empty += individual['xE'][idx]
            
            if total_full > 0:
                empty_to_full_ratio = total_empty / total_full
                if empty_to_full_ratio > 1.5:  # 150% 초과시 패널티
                    excess_ratio = empty_to_full_ratio - 1.5
                    empty_excess_penalty += excess_ratio * total_full * 50
        
        penalty = demand_penalty + capacity_penalty + non_negative_penalty + empty_constraint_penalty + empty_excess_penalty
        return penalty
    
    def calculate_lp_constraint_penalties(self, individual: Dict[str, Any]) -> float:
        """LP 명세에 따른 제약 조건 위반 패널티 계산"""
        
        # 1) 컨테이너 흐름 제약 - y_(i+1)p = y_ip + Σ(x^E + x^F) - Σ(x^E + x^F)
        container_flow_penalty = 0
        # 먼저 y 값을 올바르게 계산하고 실제 y와 비교
        expected_y = self.params.calculate_empty_container_levels(individual)
        container_flow_penalty += np.sum(np.abs(individual['y'] - expected_y)) * 1000
        
        # 2) 주문에 대한 수요 충족 - Σx_r^F = D_ab, ∀r∈R
        demand_penalty = 0
        for r in self.params.R:
            if r in self.params.D_ab:
                # 루트 r에 속한 모든 스케줄의 Full 컨테이너 합계
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = 0
                for i in route_schedules:
                    if i in self.params.I:
                        idx = self.params.I.index(i)
                        total_full += individual['xF'][idx]
                
                demand = self.params.D_ab[r]
                if abs(total_full - demand) > 0.01:  # 허용 오차
                    demand_penalty += abs(total_full - demand) * 2000  # 높은 패널티
        
        # 3) 싣는 빈 컨테이너 수 - x_i^E = θ * CAP_r, ∀i∈I, r∈R
        empty_constraint_penalty = 0
        for idx, i in enumerate(self.params.I):
            schedule_info = self.params.schedule_data[self.params.schedule_data['스케줄 번호'] == i]
            if not schedule_info.empty:
                r = schedule_info['루트번호'].iloc[0]
                if r in self.params.CAP_v_r:
                    expected_empty = self.params.theta * self.params.CAP_v_r[r]
                    actual_empty = individual['xE'][idx]
                    if abs(actual_empty - expected_empty) > 0.01:
                        empty_constraint_penalty += abs(actual_empty - expected_empty) * 1000
        
        # 4) 용량 제약 - x_r^F + x_r^E ≤ CAP_r, ∀r∈R
        capacity_penalty = 0
        for r in self.params.R:
            if r in self.params.CAP_v_r:
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_containers = 0
                for i in route_schedules:
                    if i in self.params.I:
                        idx = self.params.I.index(i)
                        total_containers += individual['xF'][idx] + individual['xE'][idx]
                
                capacity = self.params.CAP_v_r[r]
                if total_containers > capacity:
                    capacity_penalty += (total_containers - capacity) * 1500
        
        # 5) 비음 조건 - x_i^F, x_i^E, y_ip ≥ 0
        non_negative_penalty = 0
        non_negative_penalty += np.sum(np.abs(individual['xF'][individual['xF'] < 0])) * 5000
        non_negative_penalty += np.sum(np.abs(individual['xE'][individual['xE'] < 0])) * 5000
        non_negative_penalty += np.sum(np.abs(individual['y'][individual['y'] < 0])) * 5000
        
        total_penalty = (container_flow_penalty + demand_penalty + empty_constraint_penalty + 
                        capacity_penalty + non_negative_penalty)
        
        return total_penalty
    
    def calculate_total_cost(self, individual: Dict[str, Any]) -> float:
        """총 비용 계산"""
        total_cost = 0
        
        for idx, i in enumerate(self.params.I):
            # 운송 비용
            base_cost = self.params.CSHIP + self.params.CBAF
            delay_penalty = self.params.CETA * self.params.DELAY_i.get(i, 0)
            total_cost += (base_cost + delay_penalty) * individual['xF'][idx]
            total_cost += self.params.CEMPTY_SHIP * individual['xE'][idx]
        
        return total_cost