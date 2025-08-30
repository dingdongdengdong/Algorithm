"""
적합도 계산 클래스
"""

import numpy as np
from typing import Dict, Any
from models.parameters import GAParameters


class FitnessCalculator:
    """
    LP 모델 기반 적합도 계산 클래스
    """
    
    def __init__(self, params: GAParameters):
        """
        Parameters:
        -----------
        params : GAParameters
            GA 및 LP 모델 파라미터
        """
        self.params = params
        
    def calculate_fitness(self, individual: Dict[str, Any]) -> float:
        """LP 모델 기반 적합도 계산 - LP 명세에 따른 정확한 구현"""
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
        
        # 4. LP 제약 조건 패널티
        penalty = self.calculate_lp_constraint_penalties(individual)
        
        # 적합도 = -(총 비용 + 패널티)
        fitness = -(total_cost + penalty)
        individual['fitness'] = fitness
        
        return fitness
    
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