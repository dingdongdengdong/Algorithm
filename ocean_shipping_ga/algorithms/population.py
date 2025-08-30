"""
Population 관리 클래스
"""

import numpy as np
from typing import List, Dict, Any
from models.parameters import GAParameters


class PopulationManager:
    """
    개체군 초기화 및 관리 클래스
    """
    
    def __init__(self, params: GAParameters):
        """
        Parameters:
        -----------
        params : GAParameters
            GA 및 LP 모델 파라미터
        """
        self.params = params
        
    def initialize_population(self) -> List[Dict[str, Any]]:
        """초기 개체군 생성"""
        population = []
        
        for _ in range(self.params.population_size):
            # 개체 생성 (xF, xE, y)
            individual = {
                'xF': np.zeros(self.params.num_schedules),
                'xE': np.zeros(self.params.num_schedules),
                'y': np.zeros((self.params.num_schedules, self.params.num_ports)),
                'fitness': float('-inf')
            }
            
            # 스케줄별로 컨테이너 할당
            for idx, i in enumerate(self.params.I):
                # 해당 스케줄의 루트 찾기
                route_data = self.params.schedule_data[
                    self.params.schedule_data['스케줄 번호'] == i
                ]
                
                if not route_data.empty:
                    r = route_data['루트번호'].iloc[0]
                    
                    # Full container 초기화
                    if r in self.params.D_ab:
                        demand = self.params.D_ab[r]
                        # 초기값은 수요에 가깝게 설정 (약간의 노이즈 추가)
                        individual['xF'][idx] = max(0, demand + np.random.randn() * 0.5)
                    else:
                        individual['xF'][idx] = max(0, np.random.uniform(1, 10))
                    
                    # Empty container 초기화
                    if r in self.params.CAP_v_r:
                        capacity = self.params.CAP_v_r[r]
                        expected_empty = self.params.theta * capacity
                        # 초기값은 예상값에 가깝게 설정
                        individual['xE'][idx] = max(0, expected_empty + np.random.randn() * 0.5)
                    else:
                        individual['xE'][idx] = max(0, np.random.uniform(1, 5))
            
            # y 값 계산 (xF, xE에 기반하여 빈 컨테이너 수 계산)
            individual['y'] = self.params.calculate_empty_container_levels(individual)
            
            population.append(individual)
        
        return population
    
    def calculate_population_diversity(self, population: List[Dict[str, Any]]) -> float:
        """개체군의 다양성 계산"""
        if len(population) < 2:
            return 0.0
        
        diversities = []
        for i in range(len(population)):
            for j in range(i + 1, len(population)):
                # 유클리드 거리 계산
                diff_xF = np.sum((population[i]['xF'] - population[j]['xF'])**2)
                diff_xE = np.sum((population[i]['xE'] - population[j]['xE'])**2)
                diversity = np.sqrt(diff_xF + diff_xE)
                diversities.append(diversity)
        
        return np.mean(diversities) if diversities else 0.0