네, 제공하신 xlsx 파일들을 참고하여 GA 코드를 수정하고, 상세한 설명서를 작성하겠습니다.

## 해상 운송 컨테이너 최적화 GA (Genetic Algorithm) 구현

### 📋 목차
1. [개요](#개요)
2. [데이터 구조](#데이터-구조)
3. [GA 구현 코드](#ga-구현-코드)
4. [사용 방법](#사용-방법)
5. [파라미터 조정 가이드](#파라미터-조정-가이드)

---

## 개요

본 프로그램은 해상 운송 컨테이너 할당 문제를 유전 알고리즘(GA)으로 해결합니다. 기존 Linear Programming(LP) 방식을 GA로 변환하여 구현했습니다.

### 주요 목적
- **비용 최소화**: 운송비, 유류할증료, 지연 패널티, 재고 보유비
- **제약 충족**: 수요 충족, 선박 용량, 컨테이너 흐름 균형

---

## 데이터 구조

### 입력 파일 구조

#### 1. `스해물_스케줄 data.xlsx`
| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| 루트번호 | 항로 식별번호 | 1, 2, 3... |
| 출발항 | 출발 항구명 | BUSAN |
| 도착항 | 도착 항구명 | SAVANNAH |
| 선박명 | 선박 이름 | EVER FULL 1224E' |
| 주문량(KG) | 화물 주문량 | 9353.45 |
| ETD | 예정 출발일 | 2025-08-07 |
| ETA | 예정 도착일 | 2025-08-30 |
| 스케줄 번호 | 스케줄 ID | 1, 2, 3... |

#### 2. `스해물_딜레이 스케줄 data.xlsx`
| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| 루트번호 | 항로 식별번호 | 3 |
| 출발항 | 출발 항구명 | BUSAN |
| 도착항 | 도착 항구명 | SAVANNAH |
| 선박명 | 선박 이름 | COSCO SHIPPING SAKURA 031E' |
| 딜레이 ETA | 실제 도착일 | 2025-09-10 |
| 스케줄 번호 | 스케줄 ID | 1 |

#### 3. `스해물_선박 data.xlsx`
| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| 선박명 | 선박 이름 | EVER FULL 1224E' |
| 용량(TEU) | 선박 용량 | 11888 |

#### 4. `스해물_항구 위치 data.xlsx`
| 컬럼명 | 설명 | 예시 |
|--------|------|------|
| 항구명 | 항구 이름 | BUSAN |
| 위치_위도 | 위도 | 35.10160 |
| 위치_경도 | 경도 | 129.0403 |

---

## GA 구현 코드

```python
import numpy as np
import pandas as pd
import copy
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class OceanShippingGA:
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
        """엑셀 파일에서 데이터 로드"""
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
        """LP 모델 파라미터 설정"""
        # 상수 정의
        self.KG_PER_TEU = 30000  # TEU당 kg
        self.CSHIP = 1000        # 운송비 (USD/TEU)
        self.CBAF = 100          # 유류할증료 (USD/TEU)
        self.CETA = 150          # ETA 패널티 (USD/일)
        self.CHOLD = 10          # 재고 보유비 (USD/TEU)
        self.CEMPTY_SHIP = self.CSHIP + self.CBAF  # 빈 컨테이너 운송비
        self.theta = 0.001       # 빈 컨테이너 비율
        
        # Sets 정의
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
        """루트 관련 파라미터 설정"""
        self.O_i = self.schedule_data.set_index('스케줄 번호')['출발항'].to_dict()
        self.D_i = self.schedule_data.set_index('스케줄 번호')['도착항'].to_dict()
        self.V_r = self.schedule_data.set_index('루트번호')['선박명'].to_dict()
        
        # 주문량 처리 - 문자열 처리 개선
        Q_r_raw = self.schedule_data.groupby('루트번호')['주문량(KG)'].first()
        self.Q_r = {}
        for r, q in Q_r_raw.items():
            if isinstance(q, str):
                # 반복된 숫자 문자열 처리 (예: '23.888.9623.888.9623.888.96')
                try:
                    # 첫 번째 유효한 숫자만 추출
                    q_clean = q.split('.')[0] + '.' + q.split('.')[1][:2]
                    self.Q_r[r] = float(q_clean)
                except:
                    self.Q_r[r] = 10000  # 기본값
            else:
                self.Q_r[r] = float(q)
        
        # TEU 단위로 변환
        self.D_ab = {}
        for r in self.R:
            if r in self.Q_r:
                self.D_ab[r] = max(1, int(np.ceil(self.Q_r[r] / self.KG_PER_TEU)))
            else:
                self.D_ab[r] = 1  # 최소 1 TEU
                
    def setup_capacity_parameters(self):
        """선박 용량 파라미터 설정"""
        self.CAP_v = self.vessel_data.set_index('선박명')['용량(TEU)'].to_dict()
        
        # 루트별 선박 용량
        self.CAP_v_r = {}
        for r in self.V_r:
            vessel_name = self.V_r[r]
            if vessel_name in self.CAP_v:
                self.CAP_v_r[r] = self.CAP_v[vessel_name]
            else:
                self.CAP_v_r[r] = 10000  # 기본 용량
                
    def setup_delay_parameters(self):
        """지연 관련 파라미터 설정"""
        self.ETA_i = pd.to_datetime(
            self.schedule_data.set_index('스케줄 번호')['ETA']
        ).to_dict()
        
        # 딜레이 데이터 처리
        if '딜레이 ETA' in self.delayed_schedule_data.columns:
            delay_col = '딜레이 ETA'
        elif ' 딜레이 ETA' in self.delayed_schedule_data.columns:
            delay_col = ' 딜레이 ETA'
        else:
            delay_col = None
            
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
        
        wedges, texts, autotexts = axes[1, 1].pie(
            costs, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=90
        )

```python
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
    
    # 파일 경로 설정 (실제 경로로 변경 필요)
    file_paths = {
        'schedule': '스해물_스케줄 data.xlsx',
        'delayed': '스해물_딜레이 스케줄 data.xlsx',
        'vessel': '스해물_선박 data.xlsx',
        'port': '스해물_항구 위치 data.xlsx'
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
```

---

## 사용 방법

### 1. 필요 라이브러리 설치

```bash
pip install numpy pandas matplotlib openpyxl
```

### 2. 데이터 파일 준비

다음 4개의 엑셀 파일을 동일한 디렉토리에 준비:
- `스해물_스케줄 data.xlsx`
- `스해물_딜레이 스케줄 data.xlsx`
- `스해물_선박 data.xlsx`
- `스해물_항구 위치 data.xlsx`

### 3. 코드 실행

```python
# 파일 경로 설정
file_paths = {
    'schedule': '스해물_스케줄 data.xlsx',
    'delayed': '스해물_딜레이 스케줄 data.xlsx',
    'vessel': '스해물_선박 data.xlsx',
    'port': '스해물_항구 위치 data.xlsx'
}

# GA 실행
best_solution, fitness_history = run_ocean_shipping_ga(file_paths)
```

### 4. 결과 확인

프로그램 실행 시 다음 정보가 출력됩니다:

#### 콘솔 출력
- 데이터 로딩 상태
- 모델 파라미터 요약
- 진화 과정 (10세대마다)
- 최적 솔루션 요약
  - 총 비용
  - 컨테이너 할당 현황
  - 주요 루트별 수요 충족률

#### 시각화 (4개 차트)
1. **적합도 진화 그래프**: 세대별 최고 적합도 변화
2. **컨테이너 분포**: 스케줄별 Full/Empty 컨테이너 할당
3. **항구별 재고**: 각 항구의 평균 Empty 컨테이너 재고
4. **비용 구성**: 운송비, 지연 패널티, Empty 운송, 재고 보유비 비율

---

## 파라미터 조정 가이드

### GA 파라미터

| 파라미터 | 기본값 | 설명 | 조정 가이드 |
|---------|--------|------|------------|
| `population_size` | 100 | 개체군 크기 | 크게 하면 다양성↑, 속도↓ |
| `num_elite` | 20 | 엘리트 개체 수 | 전체의 10-20% 권장 |
| `p_crossover` | 0.7 | 교차 확률 | 0.6-0.9 범위 권장 |
| `p_mutation` | 0.3 | 돌연변이 확률 | 0.1-0.3 범위 권장 |
| `max_generations` | 500 | 최대 세대 수 | 문제 복잡도에 따라 조정 |

### 비용 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `CSHIP` | 1000 USD/TEU | 기본 운송비 |
| `CBAF` | 100 USD/TEU | 유류할증료 |
| `CETA` | 150 USD/일 | 지연 패널티 |
| `CHOLD` | 10 USD/TEU | 재고 보유비 |
| `theta` | 0.001 | 빈 컨테이너 비율 |

### 성능 개선 팁

#### 1. 수렴 속도 개선
```python
# GA 파라미터 조정
ga.population_size = 150  # 개체군 증가
ga.num_elite = 30        # 엘리트 증가
ga.p_mutation = 0.2       # 돌연변이 감소
```

#### 2. 해의 품질 개선
```python
# 더 많은 세대 실행
ga.max_generations = 1000

# 교차 확률 증가
ga.p_crossover = 0.8
```

#### 3. 초기해 개선
```python
# initialize_population 메서드 수정
# 수요 기반 초기화 강화
individual['xF'][idx] = demand  # 랜덤 대신 정확한 수요로 시작
```

---

## 문제 해결

### 일반적인 오류와 해결 방법

#### 1. 파일 로딩 오류
```python
# 오류: FileNotFoundError
# 해결: 파일 경로 확인
import os
print(os.getcwd())  # 현재 작업 디렉토리 확인
```

#### 2. 메모리 부족
```python
# 해결: 개체군 크기 축소
ga.population_size = 50
```

#### 3. 수렴하지 않음
```python
# 해결: 패널티 가중치 조정
# calculate_penalties 메서드에서
penalty_weight = 100000  # 증가시켜 제약 조건 강화
```

---

## 결과 해석

### 적합도 값
- **양수**: 실행 가능한 해 (제약 조건 만족)
- **음수**: 비용이 높거나 제약 조건 위반
- **개선 정체**: 수렴했거나 지역 최적해에 도달

### 컨테이너 할당
- **Full Container**: 화물 운송용
- **Empty Container**: 재배치용
- **재고 레벨**: 각 항구의 버퍼 재고

### 비용 구성 분석
- **운송비 비중 높음**: 정상적인 상황
- **지연 패널티 높음**: 스케줄 조정 필요
- **재고 비용 높음**: 재고 최적화 필요

---

## 확장 가능성

### 1. 다목적 최적화
```python
# 비용과 서비스 수준 동시 최적화
fitness = -(total_cost) + service_level * weight
```

### 2. 동적 파라미터 조정
```python
# 세대에 따라 돌연변이율 감소
ga.p_mutation = 0.3 * (1 - generation / max_generations)
```

### 3. 하이브리드 알고리즘
```python
# GA + Local Search
if generation % 50 == 0:
    best_individual = local_search(best_individual)
```



````
---


### LP (Linear Programming) 모델을 유전 알고리즘 (Genetic Algorithm)에 적용하는 방법

LP 모델의 수학적 구조를 유전 알고리즘의 최적화 프레임워크에 효과적으로 적용할 수 있습니다. 이는 특히 LP 모델로 표현하기 어려운 비선형적이거나 복잡한 제약 조건이 추가될 때 유용한 접근법입니다.

---

#### 1. 목적 함수 (Objective Function) → 적합도 함수 (Fitness Function)

* **LP 모델**: 총 비용을 최소화하는 것이 목적입니다.
* **유전 알고리즘**: 적합도를 최대화하는 것이 목적입니다.
* **변환 방법**: LP의 최소화 목적 함수에 음수를 취하여 GA의 최대화 적합도 함수로 변환합니다.
    * 예시: `적합도 = -(총 비용 + 패널티)`

#### 2. 의사결정 변수 (Decision Variables) → 염색체 (Chromosome)

* **LP 모델**: 문제의 해를 나타내는 변수들입니다 (예: `xF`, `xE`, `y`).
* **유전 알고리즘**: 문제의 해를 나타내는 염색체이며, 각 변수는 염색체의 유전자(Gene) 역할을 합니다.
* **변환 방법**: LP의 변수들을 GA 염색체의 구성 요소로 인코딩합니다.
    * 예시: `individual` 딕셔너리에 `xF`, `xE`, `y` 배열을 포함시켜 하나의 해를 표현합니다.

#### 3. 제약 조건 (Constraints) → 패널티 함수 (Penalty Function)

* **LP 모델**: 변수들이 반드시 만족해야 하는 제약식들입니다 (예: 수요 충족, 용량, 비음 제약).
* **유전 알고리즘**: 제약 조건을 위반할 경우 적합도를 낮추는 패널티 시스템입니다.
* **변환 방법**: 각 제약 조건의 위반 정도를 측정하여 적합도에서 차감합니다.
    * **예시**:
        * **수요 충족 제약**: 할당된 컨테이너가 수요량보다 적을 경우, 그 차이에 비례하는 높은 패널티를 부과합니다.
        * **용량 제약**: 할당된 컨테이너가 선박 용량을 초과할 경우, 초과분에 비례하는 패널티를 부과합니다.
        * **비음 제약**: 변수 값이 음수가 되면 큰 패널티를 부여합니다.

---

### GA_container.py 코드 분석 (예시)

제공된 코드는 위와 같은 원칙을 충실히 따르고 있습니다.

* `calculate_fitness` 메서드는 비용을 계산한 후 음수를 취해 적합도로 변환합니다.
* `initialize_population` 메서드는 LP 변수인 `xF`, `xE`, `y`를 포함하는 개체(염색체)를 생성합니다.
* `calculate_enhanced_penalties` 메서드는 수요 충족, 용량, 비음 등 여러 제약 조건을 위반할 때 적합도를 깎는 패널티 시스템을 구현했습니다.
* `selection`, `crossover`, `mutation`과 같은 유전 연산자들을 구현하여 최적해를 효과적으로 탐색하도록 설계되었습니다.

이러한 접근법은 LP 솔버가 필요 없다는 장점과 함께, 복잡한 현실 문제를 유전 알고리즘으로 해결하기 위한 강력한 프레임워크를 제공합니다.