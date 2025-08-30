"""
유전 연산자 클래스
"""

import copy
import numpy as np
import random
from typing import List, Tuple, Dict, Any
from models.parameters import GAParameters
from .fitness import FitnessCalculator


class GeneticOperators:
    """
    유전 알고리즘의 연산자들을 구현한 클래스
    """
    
    def __init__(self, params: GAParameters):
        """
        Parameters:
        -----------
        params : GAParameters
            GA 및 LP 모델 파라미터
        """
        self.params = params
        self.fitness_calculator = FitnessCalculator(params)
        
    def selection(self, population: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """선택 연산"""
        # 적합도 계산
        for ind in population:
            if ind['fitness'] == float('-inf'):
                self.fitness_calculator.calculate_fitness(ind)
        
        # 적합도 순으로 정렬
        population.sort(key=lambda x: x['fitness'], reverse=True)
        
        # 엘리트 선택
        elite = copy.deepcopy(population[:self.params.num_elite])
        
        # 룰렛 휠 선택
        fitness_values = [ind['fitness'] for ind in population]
        min_fitness = min(fitness_values)
        adjusted_fitness = [f - min_fitness + 1 for f in fitness_values]
        
        total_fitness = sum(adjusted_fitness)
        if total_fitness > 0:
            probs = [f / total_fitness for f in adjusted_fitness]
        else:
            probs = [1/len(population)] * len(population)
        
        num_roulette = self.params.population_size - self.params.num_elite
        selected_indices = np.random.choice(
            len(population), num_roulette, p=probs, replace=True
        )
        
        roulette = [copy.deepcopy(population[i]) for i in selected_indices]
        
        return elite + roulette, population[0]
    
    def crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """교차 연산 - LP 모델에 맞게 수정"""
        if np.random.rand() < self.params.p_crossover:
            child1 = copy.deepcopy(parent1)
            child2 = copy.deepcopy(parent2)
            
            # 균일 교차 (xF와 xE만)
            for idx in range(self.params.num_schedules):
                if np.random.rand() < 0.5:
                    child1['xF'][idx], child2['xF'][idx] = child2['xF'][idx], child1['xF'][idx]
                if np.random.rand() < 0.5:
                    child1['xE'][idx], child2['xE'][idx] = child2['xE'][idx], child1['xE'][idx]
            
            # 교차 후 y 값을 새로 계산 (LP 제약 조건에 맞게)
            child1['y'] = self.params.calculate_empty_container_levels(child1)
            child2['y'] = self.params.calculate_empty_container_levels(child2)
            
            # 적합도 무효화
            child1['fitness'] = float('-inf')
            child2['fitness'] = float('-inf')
            
            return child1, child2
        else:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
    
    def mutation(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """개선된 돌연변이 연산"""
        mutated = False
        
        # xF 돌연변이
        for idx in range(self.params.num_schedules):
            if np.random.rand() < self.params.p_mutation * 0.5:
                current_val = individual['xF'][idx]
                mutation_strength = max(1, current_val * 0.2)
                individual['xF'][idx] = max(0, current_val + np.random.randn() * mutation_strength)
                mutated = True
        
        # xE 돌연변이
        for idx in range(self.params.num_schedules):
            if np.random.rand() < self.params.p_mutation * 0.5:
                current_val = individual['xE'][idx]
                mutation_strength = max(1, current_val * 0.3)
                individual['xE'][idx] = max(0, current_val + np.random.randn() * mutation_strength)
                mutated = True
        
        # y 값 재계산 (xF, xE 변경 시 항상 재계산)
        if mutated:
            individual['y'] = self.params.calculate_empty_container_levels(individual)
        
        # 큰 변이 (5% 확률로 전체 재초기화)
        if np.random.rand() < 0.05:
            num_reset = max(1, int(self.params.num_schedules * 0.1))
            reset_indices = np.random.choice(self.params.num_schedules, num_reset, replace=False)
            
            for idx in reset_indices:
                i = self.params.I[idx]
                route_data = self.params.schedule_data[self.params.schedule_data['스케줄 번호'] == i]
                
                if not route_data.empty:
                    r = route_data['루트번호'].iloc[0]
                    
                    # Full container 재초기화
                    if r in self.params.D_ab:
                        demand = self.params.D_ab[r]
                        individual['xF'][idx] = max(0, demand + np.random.randn() * 3)
                    
                    # Empty container 재초기화
                    if r in self.params.CAP_v_r:
                        capacity = self.params.CAP_v_r[r]
                        individual['xE'][idx] = max(0, self.params.theta * capacity + np.random.randn() * 1)
            
            # 큰 변이 후에도 y 값 재계산
            individual['y'] = self.params.calculate_empty_container_levels(individual)
            mutated = True
        
        # 적합도 무효화 (변이된 경우만)
        if mutated:
            individual['fitness'] = float('-inf')
        
        return individual
    
    def reproduction(self, parents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """재생산"""
        new_population = []
        
        # 엘리트 보존
        new_population.extend(parents[:self.params.num_elite])
        
        # 교차와 돌연변이
        while len(new_population) < self.params.population_size:
            # 부모 선택
            idx1, idx2 = np.random.choice(len(parents), 2, replace=False)
            parent1 = parents[idx1]
            parent2 = parents[idx2]
            
            # 교차
            child1, child2 = self.crossover(parent1, parent2)
            
            # 돌연변이
            child1 = self.mutation(child1)
            child2 = self.mutation(child2)
            
            new_population.extend([child1, child2])
        
        return new_population[:self.params.population_size]
    
    def adaptive_mutation_rate(self, generation: int, diversity: float) -> float:
        """적응적 돌연변이율 계산"""
        if not self.params.use_adaptive_mutation:
            return self.params.p_mutation
        
        base_rate = self.params.p_mutation
        
        # 다양성 정규화 (0-100 범위로 가정)
        normalized_diversity = min(diversity / 100.0, 1.0)
        
        # 다양성이 낮을 때 돌연변이율 증가
        if normalized_diversity < 0.3:  # 낮은 다양성
            diversity_factor = 1.5 + (0.3 - normalized_diversity) * 2.0
        else:  # 적당한 다양성 유지
            diversity_factor = 1.0
        
        # 세대 진행에 따른 조정
        generation_factor = 1.0 + 0.3 * (generation / self.params.max_generations)
        
        return min(0.5, base_rate * diversity_factor * generation_factor)