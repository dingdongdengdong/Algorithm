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
    def __init__(self, file_paths, version='default'):
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
        version : str
            실행 버전 ('quick', 'medium', 'standard', 'full', 'default')
        """
        # 데이터 로드
        self.load_data(file_paths)
        
        # 파라미터 초기화
        self.setup_parameters()
        
        # GA 파라미터 설정 (버전별)
        self.setup_ga_parameters(version)
        
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
                
    def setup_ga_parameters(self, version='default'):
        """GA 파라미터 설정 - 버전별 설정 지원"""
        
        # 버전별 파라미터 설정
        version_configs = {
            'quick': {  # 20세대 빠른 테스트
                'population_size': 50,
                'max_generations': 20,
                'num_elite': 10,
                'convergence_patience': 10,
                'description': '빠른 테스트 (20세대)'
            },
            'medium': {  # 50세대 중간 테스트
                'population_size': 100,
                'max_generations': 50,
                'num_elite': 20,
                'convergence_patience': 25,
                'description': '중간 테스트 (50세대)'
            },
            'standard': {  # 100세대 표준
                'population_size': 200,
                'max_generations': 100,
                'num_elite': 40,
                'convergence_patience': 50,
                'description': '표준 실행 (100세대)'
            },
            'full': {  # 전체 실행
                'population_size': 1000,
                'max_generations': 2000,
                'num_elite': 200,
                'convergence_patience': 200,
                'description': '전체 실행 (2000세대)'
            },
            'default': {  # 기본값
                'population_size': 100,
                'max_generations': 100,
                'num_elite': 20,
                'convergence_patience': 50,
                'description': '기본 설정 (100세대)'
            }
        }
        
        # 선택된 버전의 설정 적용
        config = version_configs.get(version, version_configs['default'])
        
        self.version = version
        self.version_description = config['description']
        self.population_size = config['population_size']
        self.num_elite = config['num_elite']
        self.max_generations = config['max_generations']
        self.convergence_patience = config['convergence_patience']
        
        # 공통 파라미터
        self.p_crossover = 0.85         # 높은 교차율로 다양성 증가
        self.p_mutation = 0.25          # 높은 돌연변이율로 다양성 확보
        self.target_fitness = -3000     # 더 엄격한 목표
        
        # 수렴 감지 및 조기 종료 파라미터
        self.convergence_threshold = 0.0005  # 0.05% 개선
        self.stagnation_counter = 0
        
        # 성능 추적 파라미터
        self.best_ever_fitness = float('-inf')
        self.generation_stats = []
        self.diversity_history = []
        
        # M1 최적화: 병렬 처리 및 벡터화 강화
        self.use_adaptive_mutation = True  # 적응적 돌연변이율
        
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
                    
                    # Full container 초기화 (LP 모델: 수요와 정확히 일치)
                    if r in self.D_ab:
                        demand = self.D_ab[r]
                        # 초기값은 수요에 가깝게 설정 (약간의 노이즈 추가)
                        individual['xF'][idx] = max(0, demand + np.random.randn() * 0.5)
                    else:
                        individual['xF'][idx] = max(0, np.random.uniform(1, 10))
                    
                    # Empty container 초기화 (LP 모델: θ * CAP_r)
                    if r in self.CAP_v_r:
                        capacity = self.CAP_v_r[r]
                        expected_empty = self.theta * capacity
                        # 초기값은 예상값에 가깝게 설정
                        individual['xE'][idx] = max(0, expected_empty + np.random.randn() * 0.5)
                    else:
                        individual['xE'][idx] = max(0, np.random.uniform(1, 5))
            
            # 재고 초기화
            for i_idx in range(self.num_schedules):
                for p_idx in range(self.num_ports):
                    individual['y'][i_idx, p_idx] = max(0, np.random.uniform(0, 500))
            
            population.append(individual)
        
        return population
    
    def calculate_fitness(self, individual):
        """LP 모델 기반 적합도 계산"""
        total_cost = 0
        
        # LP 목적함수: minimize Σ(CSHIP*(xF+xE) + CBAF*(xF+xE) + CETA*DELAY*xF) + CHOLD*y
        for idx, i in enumerate(self.I):
            # 1. 운송비 + 유류할증료 (Full + Empty)
            transport_cost = (self.CSHIP + self.CBAF) * (individual['xF'][idx] + individual['xE'][idx])
            
            # 2. ETA 패널티 (Full 컨테이너만, PDF 명시)
            eta_penalty = self.CETA * self.DELAY_i.get(i, 0) * individual['xF'][idx]
            
            total_cost += transport_cost + eta_penalty
        
        # 3. 재고 보유 비용 (LP 모델에 명시)
        inventory_cost = self.CHOLD * np.sum(individual['y'])
        total_cost += inventory_cost
        
        # 4. 제약 조건 패널티
        penalty = self.calculate_enhanced_penalties(individual)
        
        # 적합도 = -(총 비용 + 패널티)
        fitness = -(total_cost + penalty)
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
    
    def calculate_enhanced_penalties(self, individual):
        """개선된 제약 조건 위반 패널티 계산 - 계층적 패널티 시스템"""
        penalty = 0
        
        # 1. 수요 충족 제약 (높은 우선순위)
        demand_penalty = 0
        for r in self.R:
            if r in self.D_ab:
                route_schedules = self.schedule_data[
                    self.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = 0
                for i in route_schedules:
                    if i in self.I:
                        idx = self.I.index(i)
                        total_full += individual['xF'][idx]
                
                demand = self.D_ab[r]
                # LP 모델: xF_r = D_ab (정확히 일치해야 함)
                if abs(total_full - demand) > 0.1:  # 허용 오차 0.1 TEU
                    diff = abs(total_full - demand)
                    demand_penalty += diff * 500  # 강한 패널티
        
        # 2. 용량 제약 (중간 우선순위)
        capacity_penalty = 0
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
                
                capacity = self.CAP_v_r[r]
                if total_containers > capacity:
                    excess = total_containers - capacity
                    # 적당한 초과 패널티
                    capacity_penalty += excess * 200
        
        # 3. 비음 제약 (기본 제약) - 패널티 완화
        non_negative_penalty = 0
        non_negative_penalty += np.sum(np.abs(individual['xF'][individual['xF'] < 0])) * 1000
        non_negative_penalty += np.sum(np.abs(individual['xE'][individual['xE'] < 0])) * 1000
        non_negative_penalty += np.sum(np.abs(individual['y'][individual['y'] < 0])) * 1000
        
        # 4. 빈 컨테이너 제약 (LP 모델: xE_i = θ * CAP_r)
        empty_constraint_penalty = 0
        for r in self.R:
            if r in self.CAP_v_r:
                route_schedules = self.schedule_data[
                    self.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                expected_empty = self.theta * self.CAP_v_r[r]
                
                for i in route_schedules:
                    if i in self.I:
                        idx = self.I.index(i)
                        actual_empty = individual['xE'][idx]
                        
                        # LP 모델: xE_i = θ * CAP_r (정확히 일치)
                        if abs(actual_empty - expected_empty) > 0.1:  # 허용 오차
                            diff = abs(actual_empty - expected_empty)
                            empty_constraint_penalty += diff * 200
        
        # 5. 빈 컨테이너 과다 비율 패널티 (Full 컨테이너 대비 150% 초과시)
        empty_excess_penalty = 0
        for r in self.R:
            route_schedules = self.schedule_data[
                self.schedule_data['루트번호'] == r
            ]['스케줄 번호'].unique()
            
            total_full = 0
            total_empty = 0
            for i in route_schedules:
                if i in self.I:
                    idx = self.I.index(i)
                    total_full += individual['xF'][idx]
                    total_empty += individual['xE'][idx]
            
            if total_full > 0:
                empty_to_full_ratio = total_empty / total_full
                if empty_to_full_ratio > 1.5:  # 150% 초과시 패널티
                    excess_ratio = empty_to_full_ratio - 1.5
                    empty_excess_penalty += excess_ratio * total_full * 50  # 적당한 패널티
        
        penalty = demand_penalty + capacity_penalty + non_negative_penalty + empty_constraint_penalty + empty_excess_penalty
        return penalty
    
    def calculate_service_bonus(self, individual):
        """서비스 품질 보너스 계산"""
        bonus = 0
        
        # 수요 초과 충족에 대한 보너스
        for r in self.R:
            if r in self.D_ab:
                route_schedules = self.schedule_data[
                    self.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = 0
                for i in route_schedules:
                    if i in self.I:
                        idx = self.I.index(i)
                        total_full += individual['xF'][idx]
                
                demand = self.D_ab[r]
                if total_full > demand:
                    excess = total_full - demand
                    # 적당한 초과 공급에 대해 보너스 (과도한 초과는 보너스 감소)
                    if excess <= demand * 0.1:  # 10% 이하 초과
                        bonus += excess * 50
                    else:
                        bonus += demand * 0.1 * 50 - (excess - demand * 0.1) * 10
        
        return max(0, bonus)
    
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
        """개선된 돌연변이 연산 - 더 효과적인 변이"""
        mutated = False
        
        # xF 돌연변이 (더 높은 확률과 적응적 강도)
        for idx in range(self.num_schedules):
            if np.random.rand() < self.p_mutation * 0.5:  # 50% 확률
                # 현재 값에 기반한 적응적 변이
                current_val = individual['xF'][idx]
                mutation_strength = max(1, current_val * 0.2)  # 20% 변동
                individual['xF'][idx] = max(0, current_val + np.random.randn() * mutation_strength)
                mutated = True
        
        # xE 돌연변이 (더 강한 변이)
        for idx in range(self.num_schedules):
            if np.random.rand() < self.p_mutation * 0.5:  # 50% 확률
                current_val = individual['xE'][idx]
                mutation_strength = max(1, current_val * 0.3)  # 30% 변동
                individual['xE'][idx] = max(0, current_val + np.random.randn() * mutation_strength)
                mutated = True
        
        # y 돌연변이 (재고 변이)
        if np.random.rand() < self.p_mutation:
            mask = np.random.rand(self.num_schedules, self.num_ports) < 0.2  # 20% 확률
            if np.sum(mask) > 0:
                individual['y'][mask] += np.random.randn(np.sum(mask)) * 50
                individual['y'] = np.maximum(0, individual['y'])
                mutated = True
        
        # 큰 변이 (5% 확률로 전체 재초기화)
        if np.random.rand() < 0.05:
            # 일부 스케줄을 완전히 재초기화
            num_reset = max(1, int(self.num_schedules * 0.1))  # 10% 스케줄 재설정
            reset_indices = np.random.choice(self.num_schedules, num_reset, replace=False)
            
            for idx in reset_indices:
                i = self.I[idx]
                route_data = self.schedule_data[self.schedule_data['스케줄 번호'] == i]
                
                if not route_data.empty:
                    r = route_data['루트번호'].iloc[0]
                    
                    # Full container 재초기화
                    if r in self.D_ab:
                        demand = self.D_ab[r]
                        individual['xF'][idx] = max(0, demand + np.random.randn() * 3)
                    
                    # Empty container 재초기화
                    if r in self.CAP_v_r:
                        capacity = self.CAP_v_r[r]
                        individual['xE'][idx] = max(0, self.theta * capacity + np.random.randn() * 1)
            
            mutated = True
        
        # 적합도 무효화 (변이된 경우만)
        if mutated:
            individual['fitness'] = float('-inf')
        
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
    
    def calculate_population_diversity(self, population):
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

    def adaptive_mutation_rate(self, generation, diversity):
        """적응적 돌연변이율 계산"""
        if not self.use_adaptive_mutation:
            return self.p_mutation
        
        # 다양성이 낮으면 돌연변이율 증가 (개선된 공식)
        base_rate = self.p_mutation
        
        # 다양성 정규화 (0-100 범위로 가정)
        normalized_diversity = min(diversity / 100.0, 1.0)
        
        # 다양성이 낮을 때 돌연변이율 증가
        if normalized_diversity < 0.3:  # 낮은 다양성
            diversity_factor = 1.5 + (0.3 - normalized_diversity) * 2.0
        else:  # 적당한 다양성 유지
            diversity_factor = 1.0
        
        # 세대 진행에 따른 조정
        generation_factor = 1.0 + 0.3 * (generation / self.max_generations)
        
        return min(0.5, base_rate * diversity_factor * generation_factor)

    def run(self):
        """GA 실행 - M1 최적화된 고성능 버전"""
        print("\n🧬 유전 알고리즘 시작 (M1 Mac 최적화)")
        print("=" * 60)
        print(f"🏷️ 실행 버전: {self.version_description}")
        print(f"📊 설정: Population={self.population_size}, Generations={self.max_generations}")
        print(f"🎯 목표: 적합도 >= {self.target_fitness}")
        print(f"⏰ 수렴 대기: {self.convergence_patience}세대")
        print("=" * 60)
        
        # 초기화
        start_time = datetime.now()
        population = self.initialize_population()
        best_fitness_history = []
        best_individual = None
        self.stagnation_counter = 0
        
        # 진화 과정
        for generation in range(self.max_generations):
            # 선택
            parents, best = self.selection(population)
            
            # 최고 개체 업데이트 및 수렴 체크
            improvement = False
            if best_individual is None or best['fitness'] > best_individual['fitness']:
                if best_individual is not None:
                    improvement_rate = (best['fitness'] - best_individual['fitness']) / abs(best_individual['fitness'])
                    if improvement_rate > self.convergence_threshold:
                        improvement = True
                        self.stagnation_counter = 0
                    else:
                        self.stagnation_counter += 1
                else:
                    improvement = True
                    self.stagnation_counter = 0
                best_individual = copy.deepcopy(best)
                self.best_ever_fitness = best['fitness']
            else:
                self.stagnation_counter += 1
            
            best_fitness_history.append(best['fitness'])
            
            # 다양성 계산
            diversity = self.calculate_population_diversity(population[:50])  # 샘플링으로 속도 개선
            self.diversity_history.append(diversity)
            
            # 적응적 돌연변이율 적용
            current_mutation_rate = self.adaptive_mutation_rate(generation, diversity)
            self.p_mutation = current_mutation_rate
            
            # 세대 통계 저장
            generation_stat = {
                'generation': generation,
                'best_fitness': best['fitness'],
                'diversity': diversity,
                'mutation_rate': current_mutation_rate,
                'improvement': improvement
            }
            self.generation_stats.append(generation_stat)
            
            # 진행 상황 출력 (더 상세한 정보)
            if generation % 20 == 0 or improvement:
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"세대 {generation:4d}: 적합도={best['fitness']:8.2f} | "
                      f"다양성={diversity:6.2f} | 변이율={current_mutation_rate:.3f} | "
                      f"정체={self.stagnation_counter:3d} | {elapsed:.1f}s")
                
                # 상세 비용 정보 출력
                if generation % 100 == 0:
                    total_cost = self.calculate_total_cost(best)
                    penalty = self.calculate_penalties(best)
                    print(f"  ├─ 총 비용: ${total_cost:,.0f}")
                    print(f"  ├─ 패널티: {penalty:.0f}")
                    print(f"  └─ Full/Empty: {np.sum(best['xF']):.0f}/{np.sum(best['xE']):.0f} TEU")
            
            # 목표 달성 확인
            if best['fitness'] >= self.target_fitness:
                print(f"\n✅ 목표 적합도 달성! (세대 {generation})")
                break
            
            # 조기 종료 확인 (수렴 감지)
            if self.stagnation_counter >= self.convergence_patience:
                print(f"\n⏹️ 수렴 감지로 조기 종료 (세대 {generation})")
                print(f"   {self.convergence_patience}세대 동안 {self.convergence_threshold*100:.2f}% 이상 개선 없음")
                break
            
            # 재생산
            population = self.reproduction(parents)
        
        # 최종 결과
        elapsed_time = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 60)
        print("🎯 최적화 완료!")
        print(f"⏱️ 총 실행 시간: {elapsed_time:.2f}초")
        print(f"🏆 최종 적합도: {best_individual['fitness']:.2f}")
        print(f"📈 총 진화 세대: {generation + 1}")
        print("=" * 60)
        
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
        axes[0, 0].set_xlabel('Generation')
        axes[0, 0].set_ylabel('Fitness')
        axes[0, 0].set_title('Fitness Evolution Process')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 컨테이너 분포 (상위 20개 스케줄)
        n_display = min(20, self.num_schedules)
        x_pos = np.arange(n_display)
        
        axes[0, 1].bar(x_pos, best_individual['xF'][:n_display], 
                      alpha=0.7, label='Full', color='blue')
        axes[0, 1].bar(x_pos, best_individual['xE'][:n_display], 
                      alpha=0.7, label='Empty', color='orange', 
                      bottom=best_individual['xF'][:n_display])
        axes[0, 1].set_xlabel('Schedule Number')
        axes[0, 1].set_ylabel('Container Count (TEU)')
        axes[0, 1].set_title('Container Allocation by Schedule (Top 20)')
        axes[0, 1].legend()
        axes[0, 1].set_xticks(x_pos[::2])
        axes[0, 1].set_xticklabels(self.I[:n_display:2])
        
        # 3. 항구별 평균 재고
        avg_inventory = np.mean(best_individual['y'], axis=0)
        ports = self.P[:min(10, len(self.P))]  # 최대 10개 항구만 표시
        
        axes[1, 0].barh(range(len(ports)), avg_inventory[:len(ports)], color='green', alpha=0.7)
        axes[1, 0].set_yticks(range(len(ports)))
        axes[1, 0].set_yticklabels(ports)
        axes[1, 0].set_xlabel('Average Inventory (TEU)')
        axes[1, 0].set_title('Average Empty Container Inventory by Port')
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
        labels = ['Transport Cost', 'Delay Penalty', 'Empty Transport', 'Holding Cost']
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        
        _, texts, autotexts = axes[1, 1].pie(
            costs, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        
        axes[1, 1].set_title(f'Cost Breakdown (Total: ${total_cost:,.0f})')        
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
def run_ocean_shipping_ga(file_paths, version='default', show_plot=True):
    """
    해상 운송 GA 최적화 실행
    
    Parameters:
    -----------
    file_paths : dict
        데이터 파일 경로 딕셔너리
    version : str
        실행 버전 ('quick', 'medium', 'standard', 'full', 'default')
    show_plot : bool
        시각화 표시 여부
    
    Returns:
    --------
    best_solution : dict
        최적 솔루션
    fitness_history : list
        적합도 변화 이력
    """
    # GA 인스턴스 생성 (버전 포함)
    ga = OceanShippingGA(file_paths, version)
    
    # 최적화 실행
    best_solution, fitness_history = ga.run()
    
    # 결과 출력
    ga.print_solution(best_solution)
    
    # 시각화 (옵션)
    if show_plot:
        ga.visualize_results(best_solution, fitness_history)
    
    return best_solution, fitness_history

# 명령행 인자 처리 및 메인 실행
if __name__ == "__main__":
    import os
    import sys
    import argparse
    
    # 명령행 인자 파서 설정
    parser = argparse.ArgumentParser(
        description='해상 운송 최적화 유전 알고리즘',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예제:
  python GA_container.py --version quick     # 20세대 빠른 테스트
  python GA_container.py --version medium    # 50세대 중간 테스트  
  python GA_container.py --version standard  # 100세대 표준 실행
  python GA_container.py --version full      # 2000세대 전체 실행
  python GA_container.py                     # 기본 설정 (100세대)

버전별 설정:
  quick    : 인구 50,  최대 20세대   (빠른 테스트용)
  medium   : 인구 100, 최대 50세대   (중간 테스트용)
  standard : 인구 200, 최대 100세대  (표준 실행)
  full     : 인구 1000, 최대 2000세대 (완전 실행)
        """
    )
    
    parser.add_argument(
        '--version', 
        choices=['quick', 'medium', 'standard', 'full', 'default'],
        default='default',
        help='실행 버전 선택 (기본값: default)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='랜덤 시드 (기본값: 42)'
    )
    
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='시각화 비활성화 (속도 향상)'
    )
    
    args = parser.parse_args()
    
    # 버전 정보 출력
    version_info = {
        'quick': '빠른 테스트 (20세대)',
        'medium': '중간 테스트 (50세대)',
        'standard': '표준 실행 (100세대)', 
        'full': '전체 실행 (2000세대)',
        'default': '기본 설정 (100세대)'
    }
    
    print(f"\n🚀 해상 운송 GA 최적화 시작")
    print(f"📋 선택된 버전: {args.version} - {version_info[args.version]}")
    
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
        np.random.seed(args.seed)
        print(f"🌱 랜덤 시드: {args.seed}")
        
        # GA 실행 (버전 및 시각화 옵션 포함)
        best_solution, fitness_history = run_ocean_shipping_ga(
            file_paths, args.version, show_plot=not args.no_plot
        )
        
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