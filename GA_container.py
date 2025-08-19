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
    
    이 클래스는 해상 컨테이너 운송의 비용을 최소화하기 위해
    유전 알고리즘을 사용하여 최적의 컨테이너 할당을 찾습니다.
    
    주요 기능:
    - Full 컨테이너와 Empty 컨테이너 할당 최적화
    - 다양한 제약 조건 고려 (수요, 용량, 지연 등)
    - 운송비, 연료비, 지연 패널티, 재고비 등 총 비용 최소화
    """
    def __init__(self, file_paths):
        """
        해상 운송 최적화 GA 초기화
        
        Parameters:
        -----------
        file_paths : dict
            필요한 엑셀 파일 경로를 담은 딕셔너리
            - 'schedule': 스케줄 데이터 파일 경로
            - 'delayed': 딜레이 스케줄 데이터 파일 경로
            - 'vessel': 선박 데이터 파일 경로
            - 'port': 항구 데이터 파일 경로
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
        
        Parameters:
        -----------
        file_paths : dict
            각 데이터 파일의 경로를 담은 딕셔너리
        
        로드되는 데이터:
        - schedule_data: 운송 스케줄 정보 (출발지, 도착지, 루트, 선박 등)
        - delayed_schedule_data: 지연된 스케줄 정보 (실제 도착 시간)
        - vessel_data: 선박 정보 (용량, 속도 등)
        - port_data: 항구 정보 (위치, 시설 등)
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
        Linear Programming 모델에서 사용할 파라미터들을 설정하는 메서드
        
        설정되는 파라미터들:
        1. 비용 상수들 (운송비, 연료비, 패널티 등)
        2. 집합 정의 (항구, 스케줄, 루트, 선박)
        3. 루트별 파라미터 (출발지, 도착지, 수요량 등)
        4. 선박 용량 파라미터
        5. 지연 관련 파라미터
        6. 초기 재고 설정
        """
        # 비용 관련 상수 정의 (모든 단위는 USD)
        self.KG_PER_TEU = 30000      # TEU(Twenty-foot Equivalent Unit)당 무게 (kg)
        self.CSHIP = 1000            # 기본 운송비 (USD/TEU)
        self.CBAF = 100              # BAF(Bunker Adjustment Factor) 유류할증료 (USD/TEU)
        self.CETA = 150              # ETA 지연에 따른 패널티 비용 (USD/일)
        self.CHOLD = 10              # 재고 보유 비용 (USD/TEU/일)
        self.CEMPTY_SHIP = self.CSHIP + self.CBAF  # 빈 컨테이너 운송 총비용
        self.theta = 0.001           # 빈 컨테이너 최소 비율 (전체 용량 대비)
        
        # 집합(Sets) 정의 - 최적화 모델에서 사용할 인덱스들
        self.P = self.port_data['항구명'].unique().tolist()        # P: 모든 항구들의 집합
        self.I = self.schedule_data['스케줄 번호'].unique().tolist()  # I: 모든 스케줄들의 집합
        self.R = self.schedule_data['루트번호'].unique().tolist()    # R: 모든 루트들의 집합
        self.V = self.vessel_data['선박명'].unique().tolist()       # V: 모든 선박들의 집합
        
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
        
        설정되는 파라미터들:
        - O_i: 스케줄 i의 출발항구
        - D_i: 스케줄 i의 도착항구  
        - V_r: 루트 r에 할당된 선박
        - Q_r: 루트 r의 주문량 (kg 단위)
        - D_ab: 루트 r의 수요량 (TEU 단위로 변환)
        
        주문량 데이터는 다양한 형태로 입력될 수 있어서
        문자열에서 숫자를 추출하는 안전한 파싱 로직을 포함합니다.
        """
        self.O_i = self.schedule_data.set_index('스케줄 번호')['출발항'].to_dict()
        self.D_i = self.schedule_data.set_index('스케줄 번호')['도착항'].to_dict()
        self.V_r = self.schedule_data.set_index('루트번호')['선박명'].to_dict()
        
        # 주문량 처리 - 데이터 품질이 일정하지 않을 수 있어서 안전한 숫자 변환 로직 적용
        Q_r_raw = self.schedule_data.groupby('루트번호')['주문량(KG)'].first()
        self.Q_r = {}  # 루트별 주문량을 저장할 딕셔너리
        
        for r, q in Q_r_raw.items():
            try:
                if pd.isna(q):  # NaN 값인 경우
                    self.Q_r[r] = 10000  # 기본값 설정
                elif isinstance(q, str):  # 문자열인 경우
                    # 정규식을 사용해서 문자열에서 숫자만 추출 (예: "10,000kg" -> "10000")
                    import re
                    numbers = re.findall(r'\d+\.?\d*', str(q))
                    if numbers:
                        self.Q_r[r] = float(numbers[0])
                    else:
                        self.Q_r[r] = 10000  # 숫자가 없으면 기본값
                else:
                    self.Q_r[r] = float(q)  # 이미 숫자인 경우 직접 변환
            except (ValueError, IndexError):
                print(f"Warning: Could not parse order quantity for route {r}: {q}")
                self.Q_r[r] = 10000  # 변환 실패시 기본값
        
        # 주문량을 KG에서 TEU 단위로 변환 (컨테이너 개수로 환산)
        self.D_ab = {}  # 루트별 수요량 (TEU 단위)
        for r in self.R:
            if r in self.Q_r:
                # 올림 함수를 사용해서 필요한 컨테이너 개수 계산 (부분 컨테이너는 전체로 계산)
                self.D_ab[r] = max(1, int(np.ceil(self.Q_r[r] / self.KG_PER_TEU)))
            else:
                self.D_ab[r] = 1  # 데이터가 없는 경우 최소 1 TEU로 설정
                
    def setup_capacity_parameters(self):
        """
        선박 용량 관련 파라미터를 설정하는 메서드
        
        각 선박의 최대 적재 용량을 TEU 단위로 설정하고,
        루트에 할당된 선박의 용량 제약을 정의합니다.
        
        설정되는 파라미터들:
        - CAP_v: 선박별 용량 (TEU)
        - CAP_v_r: 루트별 선박 용량 (TEU)
        """
        self.CAP_v = self.vessel_data.set_index('선박명')['용량(TEU)'].to_dict()
        
        # 루트별 선박 용량 매핑
        self.CAP_v_r = {}  # 루트별 선박 용량을 저장할 딕셔너리
        for r in self.V_r:
            vessel_name = self.V_r[r]  # 해당 루트에 할당된 선박명
            if vessel_name in self.CAP_v:
                self.CAP_v_r[r] = self.CAP_v[vessel_name]  # 선박의 실제 용량 사용
            else:
                self.CAP_v_r[r] = 10000  # 선박 정보가 없는 경우 기본 용량 설정
                
    def setup_delay_parameters(self):
        """지연 관련 파라미터 설정"""
        self.ETA_i = pd.to_datetime(
            self.schedule_data.set_index('스케줄 번호')['ETA']
        ).to_dict()
        
        # 딜레이 데이터 처리 - 컬럼명 정규화
        delay_col = None
        for col in self.delayed_schedule_data.columns:
            col_clean = str(col).strip()
            if 'ETA' in col_clean and ('딜레이' in col_clean or 'delay' in col_clean.lower()):
                delay_col = col
                break
        
        if delay_col is None:
            print("Warning: Delay ETA column not found in delayed schedule data")
            print(f"Available columns: {list(self.delayed_schedule_data.columns)}")
            
        if delay_col:
            self.RETA_i = pd.to_datetime(
                self.delayed_schedule_data.set_index('스케줄 번호')[delay_col]
            ).to_dict()
        else:
            self.RETA_i = {}
        
        # 지연일수 계산
        self.DELAY_i = {}
        for i in self.I:
            if i in self.RETA_i and i in self.ETA_i:
                delay = (self.RETA_i[i] - self.ETA_i[i]).days
                self.DELAY_i[i] = max(0, delay)
            else:
                self.DELAY_i[i] = 0
                
    def setup_initial_inventory(self):
        """초기 재고 설정"""
        self.I0_p = {p: 0 for p in self.P}
        
        # 주요 항구 초기 재고 설정
        port_inventory = {
            'BUSAN': 50000,
            'LONG BEACH': 30000,
            'NEW YORK': 100000,
            'SAVANNAH': 20000,
            'HOUSTON': 10000,
            'MOBILE': 10000,
            'SEATTLE': 10000
        }
        
        for port, inventory in port_inventory.items():
            if port in self.P:
                self.I0_p[port] = inventory
                
    def setup_ga_parameters(self):
        """GA 파라미터 설정"""
        self.population_size = 100
        self.num_elite = 20
        self.p_crossover = 0.7
        self.p_mutation = 0.3
        self.max_generations = 500
        self.target_fitness = -10000
        
    def initialize_population(self):
        """초기 개체군 생성"""
        population = []
        
        for _ in range(self.population_size):
            # 개체 생성 (xF, xE, y)
            individual = {
                'xF': np.zeros(self.num_schedules),
                'xE': np.zeros(self.num_schedules),
                'y': np.zeros((self.num_schedules, self.num_ports)),
                'fitness': float('-inf')
            }
            
            # 스케줄별로 컨테이너 할당
            for idx, i in enumerate(self.I):
                # 해당 스케줄의 루트 찾기
                route_data = self.schedule_data[
                    self.schedule_data['스케줄 번호'] == i
                ]
                
                if not route_data.empty:
                    r = route_data['루트번호'].iloc[0]
                    
                    # Full container 초기화 (수요 기반)
                    if r in self.D_ab:
                        demand = self.D_ab[r]
                        individual['xF'][idx] = max(0, demand + np.random.randn() * 5)
                    else:
                        individual['xF'][idx] = max(0, np.random.uniform(1, 50))
                    
                    # Empty container 초기화
                    if r in self.CAP_v_r:
                        capacity = self.CAP_v_r[r]
                        individual['xE'][idx] = max(0, self.theta * capacity + np.random.randn() * 2)
                    else:
                        individual['xE'][idx] = max(0, np.random.uniform(1, 10))
            
            # 재고 초기화
            for i_idx in range(self.num_schedules):
                for p_idx in range(self.num_ports):
                    individual['y'][i_idx, p_idx] = max(0, np.random.uniform(0, 500))
            
            population.append(individual)
        
        return population
    
    def calculate_fitness(self, individual):
        """적합도 계산"""
        total_cost = 0
        penalty = 0
        
        # 1. 운송 비용
        for idx, i in enumerate(self.I):
            # Full container 비용
            base_cost = self.CSHIP + self.CBAF
            delay_penalty = self.CETA * self.DELAY_i.get(i, 0)
            total_cost += (base_cost + delay_penalty) * individual['xF'][idx]
            
            # Empty container 비용
            total_cost += self.CEMPTY_SHIP * individual['xE'][idx]
        
        # 2. 재고 보유 비용
        total_cost += self.CHOLD * np.sum(individual['y'])
        
        # 3. 제약 조건 패널티
        penalty = self.calculate_penalties(individual)
        
        # 적합도 = -(비용 + 패널티)
        fitness = -(total_cost + penalty * 10000)
        individual['fitness'] = fitness
        
        return fitness
    
    def calculate_penalties(self, individual):
        """제약 조건 위반 패널티 계산"""
        penalty = 0
        
        # 1. 수요 충족 제약
        for r in self.R:
            if r in self.D_ab:
                # 해당 루트의 스케줄 찾기
                route_schedules = self.schedule_data[
                    self.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = 0
                for i in route_schedules:
                    if i in self.I:
                        idx = self.I.index(i)
                        total_full += individual['xF'][idx]
                
                # 수요 미충족 시 패널티
                if total_full < self.D_ab[r]:
                    penalty += (self.D_ab[r] - total_full)
        
        # 2. 용량 제약
        for r in self.R:
            if r in self.CAP_v_r:
                route_schedules = self.schedule_data[
                    self.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_containers = 0
                for i in route_schedules:
                    if i in self.I:
                        idx = self.I.index(i)
                        total_containers += individual['xF'][idx] + individual['xE'][idx]
                
                # 용량 초과 시 패널티
                if total_containers > self.CAP_v_r[r]:
                    penalty += (total_containers - self.CAP_v_r[r])
        
        # 3. 비음 제약
        penalty += np.sum(np.abs(individual['xF'][individual['xF'] < 0]))
        penalty += np.sum(np.abs(individual['xE'][individual['xE'] < 0]))
        penalty += np.sum(np.abs(individual['y'][individual['y'] < 0]))
        
        return penalty
    
    def selection(self, population):
        """선택 연산"""
        # 적합도 계산
        for ind in population:
            if ind['fitness'] == float('-inf'):
                self.calculate_fitness(ind)
        
        # 적합도 순으로 정렬
        population.sort(key=lambda x: x['fitness'], reverse=True)
        
        # 엘리트 선택
        elite = copy.deepcopy(population[:self.num_elite])
        
        # 룰렛 휠 선택
        fitness_values = [ind['fitness'] for ind in population]
        min_fitness = min(fitness_values)
        adjusted_fitness = [f - min_fitness + 1 for f in fitness_values]
        
        total_fitness = sum(adjusted_fitness)
        if total_fitness > 0:
            probs = [f / total_fitness for f in adjusted_fitness]
        else:
            probs = [1/len(population)] * len(population)
        
        num_roulette = self.population_size - self.num_elite
        selected_indices = np.random.choice(
            len(population), num_roulette, p=probs, replace=True
        )
        
        roulette = [copy.deepcopy(population[i]) for i in selected_indices]
        
        return elite + roulette, population[0]
    
    def crossover(self, parent1, parent2):
        """교차 연산"""
        if np.random.rand() < self.p_crossover:
            child1 = copy.deepcopy(parent1)
            child2 = copy.deepcopy(parent2)
            
            # 균일 교차
            for idx in range(self.num_schedules):
                if np.random.rand() < 0.5:
                    child1['xF'][idx], child2['xF'][idx] = child2['xF'][idx], child1['xF'][idx]
                if np.random.rand() < 0.5:
                    child1['xE'][idx], child2['xE'][idx] = child2['xE'][idx], child1['xE'][idx]
            
            return child1, child2
        else:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
    
    def mutation(self, individual):
        """돌연변이 연산"""
        if np.random.rand() < self.p_mutation:
            # xF 돌연변이
            for idx in range(self.num_schedules):
                if np.random.rand() < 0.1:
                    individual['xF'][idx] = max(0, individual['xF'][idx] + np.random.randn() * 5)
            
            # xE 돌연변이
            for idx in range(self.num_schedules):
                if np.random.rand() < 0.1:
                    individual['xE'][idx] = max(0, individual['xE'][idx] + np.random.randn() * 2)
            
            # y 돌연변이
            mask = np.random.rand(self.num_schedules, self.num_ports) < 0.05
            individual['y'][mask] += np.random.randn(np.sum(mask)) * 10
            individual['y'] = np.maximum(0, individual['y'])
        
        return individual
    
    def reproduction(self, parents):
        """재생산"""
        new_population = []
        
        # 엘리트 보존
        new_population.extend(parents[:self.num_elite])
        
        # 교차와 돌연변이
        while len(new_population) < self.population_size:
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
        
        return new_population[:self.population_size]
    
    def run(self):
        """GA 실행"""
        print("\n🧬 유전 알고리즘 시작")
        print("=" * 50)
        
        # 초기화
        population = self.initialize_population()
        best_fitness_history = []
        best_individual = None
        
        # 진화 과정
        for generation in range(self.max_generations):
            # 선택
            parents, best = self.selection(population)
            
            # 최고 개체 업데이트
            if best_individual is None or best['fitness'] > best_individual['fitness']:
                best_individual = copy.deepcopy(best)
            
            best_fitness_history.append(best['fitness'])
            
            # 진행 상황 출력
            if generation % 10 == 0:
                print(f"세대 {generation:3d}: 최고 적합도 = {best['fitness']:.2f}")
                
                # 비용 정보 출력
                if generation % 50 == 0:
                    total_cost = self.calculate_total_cost(best)
                    penalty = self.calculate_penalties(best)
                    print(f"  └─ 총 비용: ${total_cost:,.0f}, 패널티: {penalty:.0f}")
            
            # 목표 달성 확인
            if best['fitness'] >= self.target_fitness:
                print(f"\n✅ 목표 적합도 달성! (세대 {generation})")
                break
            
            # 재생산
            population = self.reproduction(parents)
        
        print("\n" + "=" * 50)
        print("🎯 최적화 완료!")
        
        return best_individual, best_fitness_history
    
    def calculate_total_cost(self, individual):
        """총 비용 계산"""
        total_cost = 0
        
        for idx, i in enumerate(self.I):
            # 운송 비용
            base_cost = self.CSHIP + self.CBAF
            delay_penalty = self.CETA * self.DELAY_i.get(i, 0)
            total_cost += (base_cost + delay_penalty) * individual['xF'][idx]
            total_cost += self.CEMPTY_SHIP * individual['xE'][idx]
        
        # 재고 비용
        total_cost += self.CHOLD * np.sum(individual['y'])
        
        return total_cost
    
    def print_solution(self, best_individual):
        """최적해 출력"""
        print("\n" + "=" * 60)
        print("📊 최적 솔루션 요약")
        print("=" * 60)
        
        total_cost = self.calculate_total_cost(best_individual)
        penalty = self.calculate_penalties(best_individual)
        
        print(f"\n💰 비용 분석:")
        print(f"  • 총 비용: ${total_cost:,.2f}")
        print(f"  • 패널티: {penalty:.2f}")
        print(f"  • 적합도: {best_individual['fitness']:.2f}")
        
        print(f"\n📦 컨테이너 할당:")
        print(f"  • Full 컨테이너: {np.sum(best_individual['xF']):,.0f} TEU")
        print(f"  • Empty 컨테이너: {np.sum(best_individual['xE']):,.0f} TEU")
        print(f"  • 평균 재고: {np.mean(best_individual['y']):,.0f} TEU")
        
        # 루트별 수요 충족률
        print(f"\n🚢 주요 루트 상태 (상위 5개):")
        for r in self.R[:5]:
            if r in self.D_ab:
                route_schedules = self.schedule_data[
                    self.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = sum(
                    best_individual['xF'][self.I.index(i)]
                    for i in route_schedules if i in self.I
                )
                
                demand = self.D_ab[r]
                fulfillment = (total_full / demand * 100) if demand > 0 else 0
                
                vessel = self.V_r.get(r, "Unknown")[:20]  # 선박명 20자로 제한
                print(f"  루트 {r:3d}: {total_full:5.0f}/{demand:5.0f} TEU "
                      f"({fulfillment:5.1f}%) - {vessel}")
    
    def visualize_results(self, best_individual, fitness_history):
        """결과 시각화"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 적합도 진화
        axes[0, 0].plot(fitness_history, 'b-', linewidth=2)
        axes[0, 0].set_xlabel('세대')
        axes[0, 0].set_ylabel('적합도')
        axes[0, 0].set_title('적합도 진화 과정')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 컨테이너 분포 (상위 20개 스케줄)
        n_display = min(20, self.num_schedules)
        x_pos = np.arange(n_display)
        
        axes[0, 1].bar(x_pos, best_individual['xF'][:n_display], 
                      alpha=0.7, label='Full', color='blue')
        axes[0, 1].bar(x_pos, best_individual['xE'][:n_display], 
                      alpha=0.7, label='Empty', color='orange', 
                      bottom=best_individual['xF'][:n_display])
        axes[0, 1].set_xlabel('스케줄 번호')
        axes[0, 1].set_ylabel('컨테이너 수 (TEU)')
        axes[0, 1].set_title('스케줄별 컨테이너 할당 (상위 20개)')
        axes[0, 1].legend()
        axes[0, 1].set_xticks(x_pos[::2])
        axes[0, 1].set_xticklabels(self.I[:n_display:2])
        
        # 3. 항구별 평균 재고
        avg_inventory = np.mean(best_individual['y'], axis=0)
        ports = self.P[:min(10, len(self.P))]  # 최대 10개 항구만 표시
        
        axes[1, 0].barh(range(len(ports)), avg_inventory[:len(ports)], color='green', alpha=0.7)
        axes[1, 0].set_yticks(range(len(ports)))
        axes[1, 0].set_yticklabels(ports)
        axes[1, 0].set_xlabel('평균 재고 (TEU)')
        axes[1, 0].set_title('항구별 평균 Empty 컨테이너 재고')
        axes[1, 0].grid(True, alpha=0.3, axis='x')
        
        # 4. 비용 구성
        total_cost = self.calculate_total_cost(best_individual)
        
        transport_cost = sum(
            (self.CSHIP + self.CBAF) * best_individual['xF'][i]
            for i in range(self.num_schedules)
        )
        delay_cost = sum(
            self.CETA * self.DELAY_i.get(self.I[i], 0) * best_individual['xF'][i]
            for i in range(self.num_schedules)
        )
        empty_cost = self.CEMPTY_SHIP * np.sum(best_individual['xE'])
        holding_cost = self.CHOLD * np.sum(best_individual['y'])
        
        costs = [transport_cost, delay_cost, empty_cost, holding_cost]
        labels = ['운송비', '지연 패널티', 'Empty 운송', '재고 보유']
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        
        _, texts, autotexts = axes[1, 1].pie(
            costs, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        
        axes[1, 1].set_title(f'비용 구성 (총: ${total_cost:,.0f})')        
        # 폰트 크기 조정
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color('white')
            autotext.set_weight('bold')
        
        plt.tight_layout()
        plt.show()
        
        return fig

# 메인 실행 함수
def run_ocean_shipping_ga(file_paths):
    """
    해상 운송 GA 최적화 실행
    
    Parameters:
    -----------
    file_paths : dict
        데이터 파일 경로 딕셔너리
    
    Returns:
    --------
    best_solution : dict
        최적 솔루션
    fitness_history : list
        적합도 변화 이력
    """
    # GA 인스턴스 생성
    ga = OceanShippingGA(file_paths)
    
    # 최적화 실행
    best_solution, fitness_history = ga.run()
    
    # 결과 출력
    ga.print_solution(best_solution)
    
    # 시각화
    ga.visualize_results(best_solution, fitness_history)
    
    return best_solution, fitness_history

# 사용 예제
if __name__ == "__main__":
    import os
    
    # 파일 경로 설정 (절대 경로 사용)
    base_path = '/Users/dong/Downloads/ocean'
    file_paths = {
        'schedule': f'{base_path}/스해물_스케줄 data.xlsx',
        'delayed': f'{base_path}/스해물_딜레이 스케줄 data.xlsx',
        'vessel': f'{base_path}/스해물_선박 data.xlsx',
        'port': f'{base_path}/스해물_항구 위치 data.xlsx'
    }
    
    # 파일 존재 확인
    all_files_exist = True
    for name, path in file_paths.items():
        if not os.path.exists(path):
            print(f"⚠️ 파일을 찾을 수 없습니다: {path}")
            all_files_exist = False
    
    if all_files_exist:
        # 랜덤 시드 설정 (재현가능한 결과를 위해)
        np.random.seed(42)
        
        # GA 실행
        best_solution, fitness_history = run_ocean_shipping_ga(file_paths)
        
        # 추가 분석 (선택사항)
        print("\n" + "=" * 60)
        print("📈 추가 분석")
        print("=" * 60)
        
        # 수렴 속도 분석
        convergence_gen = -1
        threshold = 0.01  # 1% 개선
        for i in range(10, len(fitness_history)):
            improvement = abs(fitness_history[i] - fitness_history[i-10]) / abs(fitness_history[i-10])
            if improvement < threshold:
                convergence_gen = i
                break
        
        if convergence_gen > 0:
            print(f"수렴 세대: {convergence_gen}")
        else:
            print("아직 수렴하지 않음")
        
        # 최종 개선율
        if len(fitness_history) > 1:
            total_improvement = (fitness_history[-1] - fitness_history[0]) / abs(fitness_history[0]) * 100
            print(f"총 개선율: {total_improvement:.2f}%")
    else:
        print("\n❌ 필요한 데이터 파일이 없어 실행할 수 없습니다.")
        print("파일 경로를 확인해주세요.")