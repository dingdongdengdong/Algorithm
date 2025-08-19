# 필요한 라이브러리들을 import
import numpy as np          # 수치 계산을 위한 라이브러리
import pandas as pd         # 데이터 조작 및 분석을 위한 라이브러리
import copy                 # 객체 복사를 위한 라이브러리
import matplotlib.pyplot as plt  # 데이터 시각화를 위한 라이브러리
from datetime import datetime    # 날짜 및 시간 처리를 위한 라이브러리
import warnings             # 경고 메시지 제어
warnings.filterwarnings('ignore')  # 모든 경고 메시지 무시

class OceanShippingGA:
    """
    해상 운송 최적화를 위한 유전 알고리즘 클래스
    """
    def __init__(self, file_paths):
        """
        해상 운송 최적화 GA 초기화
        """
        # 데이터 로드
        self.load_data(file_paths)
        
        # 파라미터 초기화
        self.setup_parameters()
        
        # GA 파라미터 설정
        self.setup_ga_parameters()
        
    def load_data(self, file_paths):
        """
        엑셀 파일에서 필요한 데이터를 로드하는 메서드
        """
        print("📂 데이터 로딩 중...")
        
        self.schedule_data = pd.read_excel(file_paths['schedule'])
        self.delayed_schedule_data = pd.read_excel(file_paths['delayed'])
        self.vessel_data = pd.read_excel(file_paths['vessel'])
        self.port_data = pd.read_excel(file_paths['port'])
        
        print(f"✅ 스케줄 데이터: {len(self.schedule_data)}개 로드")
        print(f"✅ 딜레이 데이터: {len(self.delayed_schedule_data)}개 로드")
        print(f"✅ 선박 데이터: {len(self.vessel_data)}개 로드")
        print(f"✅ 항구 데이터: {len(self.port_data)}개 로드")
        
    def setup_parameters(self):
        """
        모델에서 사용할 파라미터들을 설정하는 메서드
        """
        # 현실적인 값으로 설정된 비용 상수
        self.KG_PER_TEU = 10000
        self.CSHIP = 2500
        self.CBAF = 500
        self.CETA = 150
        self.CHOLD = 25
        self.CEMPTY_SHIP = (self.CSHIP + self.CBAF) * 0.75
        self.theta = 0.05
        
        # 집합(Sets) 정의
        self.P = self.port_data['항구명'].unique().tolist()
        self.I = self.schedule_data['스케줄 번호'].unique().tolist()
        self.R = self.schedule_data['루트번호'].unique().tolist()
        self.V = self.vessel_data['선박명'].unique().tolist()
        
        self.num_schedules = len(self.I)
        self.num_ports = len(self.P)
        
        print(f"\n📊 모델 파라미터:")
        print(f"  - 스케줄 수: {self.num_schedules}")
        print(f"  - 항구 수: {self.num_ports}")
        print(f"  - 루트 수: {len(self.R)}")
        print(f"  - 선박 수: {len(self.V)}")
        
        # Parameters 설정
        self.setup_route_parameters()
        self.setup_capacity_parameters()
        self.setup_delay_parameters()
        self.setup_initial_inventory()
        
    def setup_route_parameters(self):
        """
        루트 관련 파라미터들을 설정하는 메서드
        """
        self.O_i = self.schedule_data.set_index('스케줄 번호')['출발항'].to_dict()
        self.D_i = self.schedule_data.set_index('스케줄 번호')['도착항'].to_dict()
        self.V_r = self.schedule_data.set_index('루트번호')['선박명'].to_dict()
        
        Q_r_raw = self.schedule_data.groupby('루트번호')['주문량(KG)'].first()
        self.Q_r = {}
        
        for r, q in Q_r_raw.items():
            try:
                if pd.isna(q):
                    self.Q_r[r] = 10000
                elif isinstance(q, str):
                    import re
                    numbers = re.findall(r'\d+\.?\d*', str(q))
                    self.Q_r[r] = float(numbers[0]) if numbers else 10000
                else:
                    self.Q_r[r] = float(q)
            except (ValueError, IndexError):
                self.Q_r[r] = 10000
        
        self.D_ab = {r: max(1, int(np.ceil(self.Q_r.get(r, self.KG_PER_TEU) / self.KG_PER_TEU))) for r in self.R}
                
    def setup_capacity_parameters(self):
        """
        선박 용량 관련 파라미터를 설정하는 메서드
        """
        self.CAP_v = self.vessel_data.set_index('선박명')['용량(TEU)'].to_dict()
        self.CAP_v_r = {r: self.CAP_v.get(v_name, 10000) for r, v_name in self.V_r.items()}
                
    def setup_delay_parameters(self):
        """지연 관련 파라미터 설정"""
        self.ETA_i = pd.to_datetime(self.schedule_data.set_index('스케줄 번호')['ETA']).to_dict()
        
        delay_col = next((col for col in self.delayed_schedule_data.columns if 'ETA' in str(col) and ('딜레이' in str(col) or 'delay' in str(col).lower())), None)
        
        if delay_col:
            self.RETA_i = pd.to_datetime(self.delayed_schedule_data.set_index('스케줄 번호')[delay_col]).to_dict()
        else:
            self.RETA_i = {}
            print("Warning: Delay ETA column not found.")
        
        self.DELAY_i = {i: max(0, (self.RETA_i.get(i, self.ETA_i.get(i)) - self.ETA_i.get(i)).days) for i in self.I if i in self.ETA_i}
                
    def setup_initial_inventory(self):
        """초기 재고 설정"""
        self.I0_p = {p: 0 for p in self.P}
        port_inventory = {'BUSAN': 20000, 'LONG BEACH': 15000, 'NEW YORK': 10000, 'SAVANNAH': 8000, 'HOUSTON': 5000, 'MOBILE': 3000, 'SEATTLE': 7000}
        self.I0_p.update({port: inv for port, inv in port_inventory.items() if port in self.I0_p})
                
    def setup_ga_parameters(self):
        """GA 파라미터 설정 """
        self.population_size = 500
        self.num_elite = 50
        self.p_crossover = 0.8
        
        # --- 개선 사항 1: 다양성 확보를 위한 파라미터 조정 ---
        self.p_mutation = 0.2 # 돌연변이 확률 증가 (0.1 -> 0.2)
        self.convergence_patience = 100 # 수렴 대기 세대 증가 (50 -> 100)
        # ----------------------------------------------------

        self.max_generations = 1000
        self.target_fitness = -1000000
        self.convergence_threshold = 0.001
        self.stagnation_counter = 0
        self.best_ever_fitness = float('-inf')
        self.use_adaptive_mutation = False # 예측 가능성을 위해 적응적 돌연변이 비활성화
        
    def initialize_population(self):
        """초기 개체군 생성"""
        population = []
        for _ in range(self.population_size):
            individual = {'xF': np.zeros(self.num_schedules), 'xE': np.zeros(self.num_schedules), 'y': np.zeros((self.num_schedules, self.num_ports)), 'fitness': float('-inf')}
            for idx, i in enumerate(self.I):
                route_data = self.schedule_data[self.schedule_data['스케줄 번호'] == i]
                if not route_data.empty:
                    r = route_data['루트번호'].iloc[0]
                    demand = self.D_ab.get(r, 1)
                    individual['xF'][idx] = max(0, demand + np.random.randint(-5, 6))
                    capacity = self.CAP_v_r.get(r, 10000)
                    individual['xE'][idx] = max(0, self.theta * capacity + np.random.randint(-2, 3))
            individual['y'] = np.random.uniform(0, 100, size=(self.num_schedules, self.num_ports))
            population.append(individual)
        return population
    
    def calculate_fitness(self, individual):
        """적합도 계산"""
        total_cost = self.calculate_total_cost(individual)
        penalty = self.calculate_penalties(individual)
        fitness = -(total_cost + penalty)
        individual['fitness'] = fitness
        return fitness
    
    def calculate_penalties(self, individual):
        """제약 조건 위반 패널티 계산"""
        penalty = 0
        
        # 1. 수요 충족 제약
        demand_penalty_weight = 5000
        for r in self.R:
            route_schedules = self.schedule_data[self.schedule_data['루트번호'] == r]['스케줄 번호'].unique()
            total_full = sum(individual['xF'][self.I.index(i)] for i in route_schedules if i in self.I)
            demand = self.D_ab.get(r, 0)
            if total_full < demand:
                penalty += (demand - total_full) * demand_penalty_weight
        
        # 2. 용량 제약
        capacity_penalty_weight = 3000
        for r in self.R:
            route_schedules = self.schedule_data[self.schedule_data['루트번호'] == r]['스케줄 번호'].unique()
            total_containers = sum(individual['xF'][self.I.index(i)] + individual['xE'][self.I.index(i)] for i in route_schedules if i in self.I)
            capacity = self.CAP_v_r.get(r, float('inf'))
            if total_containers > capacity:
                penalty += (total_containers - capacity) * capacity_penalty_weight
        
        # 3. 비음 제약
        non_negative_penalty_weight = 100000
        penalty += np.sum(np.abs(individual['xF'][individual['xF'] < 0])) * non_negative_penalty_weight
        penalty += np.sum(np.abs(individual['xE'][individual['xE'] < 0])) * non_negative_penalty_weight
        penalty += np.sum(np.abs(individual['y'][individual['y'] < 0])) * non_negative_penalty_weight

        # --- 개선 사항 2: Empty 컨테이너 비율 패널티 추가 ---
        empty_ratio_penalty_weight = 1000 # Empty 컨테이너 1 TEU당 추가 패널티
        total_empty = np.sum(individual['xE'])
        total_full = np.sum(individual['xF'])

        # Full 컨테이너가 있을 때만 비율 패널티 계산
        if total_full > 0:
            # Empty 컨테이너가 Full 컨테이너의 150%를 초과하면 패널티 부과
            if (total_empty / total_full) > 1.5:
                excess_empty = total_empty - (total_full * 1.5)
                penalty += excess_empty * empty_ratio_penalty_weight
        # ----------------------------------------------------

        return penalty

    def selection(self, population):
        """선택 연산"""
        for ind in population:
            if ind['fitness'] == float('-inf'):
                self.calculate_fitness(ind)
        
        population.sort(key=lambda x: x['fitness'], reverse=True)
        elite = copy.deepcopy(population[:self.num_elite])
        
        fitness_values = [ind['fitness'] for ind in population]
        min_fitness = min(fitness_values) if fitness_values else 0
        adjusted_fitness = [f - min_fitness + 1 for f in fitness_values]
        
        total_fitness = sum(adjusted_fitness)
        probs = [f / total_fitness for f in adjusted_fitness] if total_fitness > 0 else [1/len(population)] * len(population)
        
        num_roulette = self.population_size - self.num_elite
        selected_indices = np.random.choice(len(population), num_roulette, p=probs, replace=True)
        roulette = [copy.deepcopy(population[i]) for i in selected_indices]
        
        return elite + roulette, population[0]
    
    def crossover(self, parent1, parent2):
        """교차 연산"""
        if np.random.rand() < self.p_crossover:
            child1, child2 = copy.deepcopy(parent1), copy.deepcopy(parent2)
            for key in ['xF', 'xE']:
                mask = np.random.rand(self.num_schedules) < 0.5
                child1[key][mask], child2[key][mask] = child2[key][mask], child1[key][mask]
            return child1, child2
        return copy.deepcopy(parent1), copy.deepcopy(parent2)
    
    def mutation(self, individual):
        """돌연변이 연산"""
        if np.random.rand() < self.p_mutation:
            idx = np.random.randint(self.num_schedules)
            if np.random.rand() < 0.5:
                individual['xF'][idx] = max(0, individual['xF'][idx] + np.random.randn() * 5)
            else:
                individual['xE'][idx] = max(0, individual['xE'][idx] + np.random.randn() * 2)
        return individual
    
    def reproduction(self, parents):
        """재생산"""
        new_population = parents[:self.num_elite]
        while len(new_population) < self.population_size:
            idx1, idx2 = np.random.choice(len(parents), 2, replace=False)
            child1, child2 = self.crossover(parents[idx1], parents[idx2])
            new_population.extend([self.mutation(child1), self.mutation(child2)])
        return new_population[:self.population_size]
    
    def run(self):
        """GA 실행"""
        print("\n🧬 유전 알고리즘 시작 (개선 버전)")
        print("=" * 60)
        
        start_time = datetime.now()
        population = self.initialize_population()
        best_fitness_history = []
        best_individual = None
        
        for generation in range(self.max_generations):
            parents, best = self.selection(population)
            
            if best_individual is None or best['fitness'] > best_individual['fitness']:
                improvement_rate = 0
                if best_individual and abs(best_individual['fitness']) > 0:
                    improvement_rate = (best['fitness'] - best_individual['fitness']) / abs(best_individual['fitness'])
                
                self.stagnation_counter = 0 if improvement_rate > self.convergence_threshold else self.stagnation_counter + 1
                best_individual = copy.deepcopy(best)
            else:
                self.stagnation_counter += 1
            
            best_fitness_history.append(best['fitness'])
            
            if generation % 20 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"세대 {generation:4d}: 적합도={best['fitness']:12.2f} | 정체={self.stagnation_counter:3d} | {elapsed:.1f}s")
            
            if best['fitness'] >= self.target_fitness or self.stagnation_counter >= self.convergence_patience:
                if best['fitness'] >= self.target_fitness: print(f"\n✅ 목표 적합도 달성!")
                else: print(f"\n⏹️ 수렴 감지로 조기 종료")
                break
            
            population = self.reproduction(parents)
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 60)
        print("🎯 최적화 완료!")
        print(f"⏱️ 총 실행 시간: {elapsed_time:.2f}초")
        print(f"🏆 최종 적합도: {best_individual['fitness']:.2f}")
        print(f"� 총 진화 세대: {generation + 1}")
        print("=" * 60)
        
        return best_individual, best_fitness_history
    
    def calculate_total_cost(self, individual):
        """총 비용 계산"""
        transport_cost = np.sum([(self.CSHIP + self.CBAF + self.CETA * self.DELAY_i.get(i, 0)) * individual['xF'][idx] for idx, i in enumerate(self.I)])
        empty_transport_cost = np.sum(self.CEMPTY_SHIP * individual['xE'])
        holding_cost = np.sum(self.CHOLD * individual['y'])
        return transport_cost + empty_transport_cost + holding_cost
    
    def print_solution(self, best_individual):
        """최적해 출력"""
        print("\n" + "=" * 60)
        print("📊 최적 솔루션 요약")
        print("=" * 60)
        
        total_cost = self.calculate_total_cost(best_individual)
        penalty = self.calculate_penalties(best_individual)
        
        total_full = np.sum(best_individual['xF'])
        total_empty = np.sum(best_individual['xE'])
        empty_ratio = (total_empty / total_full * 100) if total_full > 0 else 0

        print(f"\n💰 비용 분석:")
        print(f"  • 총 비용: ${total_cost:,.2f}")
        print(f"  • 패널티: ${penalty:,.2f}")
        
        print(f"\n📦 컨테이너 할당:")
        print(f"  • Full 컨테이너: {total_full:,.0f} TEU")
        print(f"  • Empty 컨테이너: {total_empty:,.0f} TEU (Full 대비 {empty_ratio:.1f}%)")
        
        print(f"\n🚢 주요 루트 수요 충족률 (상위 5개):")
        for r in self.R[:5]:
            route_schedules = self.schedule_data[self.schedule_data['루트번호'] == r]['스케줄 번호'].unique()
            total_full_route = sum(best_individual['xF'][self.I.index(i)] for i in route_schedules if i in self.I)
            demand = self.D_ab.get(r, 0)
            fulfillment = (total_full_route / demand * 100) if demand > 0 else 0
            print(f"  루트 {r:3d}: 수요 {demand:5.0f} TEU -> 공급 {total_full_route:5.0f} TEU ({fulfillment:5.1f}%)")

    def visualize_results(self, best_individual, fitness_history):
        """결과 시각화"""
        try:
            plt.rcParams['font.family'] = 'AppleGothic'
            plt.rcParams['axes.unicode_minus'] = False
        except:
            print("Matplotlib 한글 폰트(AppleGothic)를 찾을 수 없습니다. 영문으로 표시됩니다.")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        axes[0, 0].plot(fitness_history, 'b-', linewidth=2)
        axes[0, 0].set_title('Fitness Evolution')
        axes[0, 0].set_xlabel('Generation')
        axes[0, 0].set_ylabel('Fitness')
        
        # ... (시각화 코드의 나머지 부분은 이전과 동일하게 유지)
        
        plt.tight_layout()
        plt.show()

# 메인 실행 함수
def run_ocean_shipping_ga(file_paths):
    ga = OceanShippingGA(file_paths)
    best_solution, fitness_history = ga.run()
    if best_solution:
        ga.print_solution(best_solution)
        ga.visualize_results(best_solution, fitness_history)
    return best_solution, fitness_history

if __name__ == "__main__":
    import os
    base_path = '.' 
    file_paths = {
        'schedule': os.path.join(base_path, '스해물_스케줄 data.xlsx'),
        'delayed': os.path.join(base_path, '스해물_딜레이 스케줄 data.xlsx'),
        'vessel': os.path.join(base_path, '스해물_선박 data.xlsx'),
        'port': os.path.join(base_path, '스해물_항구 위치 data.xlsx')
    }
    
    if all(os.path.exists(p) for p in file_paths.values()):
        np.random.seed(42)
        run_ocean_shipping_ga(file_paths)
    else:
        print("\n❌ 필요한 데이터 파일이 없어 실행할 수 없습니다.")
