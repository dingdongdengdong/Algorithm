"""
GA 개체(Individual) 클래스 정의
"""

import numpy as np
from typing import Dict, Any


class Individual:
    """
    유전 알고리즘에서 사용되는 개체 클래스
    """
    
    def __init__(self, num_schedules: int, num_ports: int):
        """
        Parameters:
        -----------
        num_schedules : int
            스케줄 수
        num_ports : int
            항구 수
        """
        self.num_schedules = num_schedules
        self.num_ports = num_ports
        
        # 유전자 초기화
        self.xF = np.zeros(num_schedules)  # Full 컨테이너
        self.xE = np.zeros(num_schedules)  # Empty 컨테이너
        self.y = np.zeros((num_schedules, num_ports))  # 빈 컨테이너 재고
        
        self.fitness = float('-inf')
        
    def to_dict(self) -> Dict[str, Any]:
        """개체를 딕셔너리로 변환"""
        return {
            'xF': self.xF,
            'xE': self.xE,
            'y': self.y,
            'fitness': self.fitness
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Individual':
        """딕셔너리에서 개체 생성"""
        num_schedules = len(data['xF'])
        num_ports = data['y'].shape[1]
        
        individual = cls(num_schedules, num_ports)
        individual.xF = data['xF']
        individual.xE = data['xE']
        individual.y = data['y']
        individual.fitness = data['fitness']
        
        return individual
    
    def copy(self) -> 'Individual':
        """개체 복사본 생성"""
        individual = Individual(self.num_schedules, self.num_ports)
        individual.xF = self.xF.copy()
        individual.xE = self.xE.copy()
        individual.y = self.y.copy()
        individual.fitness = self.fitness
        
        return individual
    
    def reset_fitness(self):
        """적합도 초기화"""
        self.fitness = float('-inf')