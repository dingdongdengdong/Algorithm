"""
GA 및 LP 모델 파라미터 설정 클래스
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from data.data_loader import DataLoader
from config import get_constant


class GAParameters:
    """
    Linear Programming 모델 및 GA 파라미터를 관리하는 클래스
    """
    
    def __init__(self, data_loader: DataLoader, version: str = 'default'):
        """
        Parameters:
        -----------
        data_loader : DataLoader
            로드된 데이터를 포함하는 DataLoader 인스턴스
        version : str
            실행 버전 ('quick', 'medium', 'standard', 'full', 'default')
        """
        self.data_loader = data_loader
        self.version = version
        
        # 데이터 참조
        self.schedule_data = data_loader.get_schedule_data()
        self.delayed_schedule_data = data_loader.get_delayed_data()
        self.vessel_data = data_loader.get_vessel_data()
        self.port_data = data_loader.get_port_data()
        self.fixed_data = data_loader.get_fixed_data()
        
        # 파라미터 초기화
        self.setup_cost_parameters()
        self.setup_sets()
        self.setup_route_parameters()
        self.setup_capacity_parameters()
        self.setup_delay_parameters()
        self.setup_initial_inventory()
        self.setup_ga_parameters(version)
        
    def setup_cost_parameters(self):
        """비용 관련 상수 정의 - 고정값 데이터에서 로드"""
        # 기본값 설정 (설정 파일에서 로드)
        self.KG_PER_TEU = get_constant('physical.kg_per_teu', 30000)      # TEU당 무게 (kg)
        self.theta = get_constant('physical.theta', 0.25)                  # 빈 컨테이너 최소 비율 (25%)
        
        # 고정값 데이터에서 비용 파라미터 로드 (개선된 방식)
        fixed_params = self.data_loader.get_fixed_params()
        
        if fixed_params:
            try:
                # 비용 파라미터 매핑 (다양한 키 이름 지원)
                self.CBAF = self._get_cost_param(fixed_params, ['유류할증료', 'BAF', 'Fuel Surcharge'], 100)
                self.CETA = self._get_cost_param(fixed_params, ['ETA 패널티', 'ETA Penalty', 'ETA_PENALTY'], 150)
                self.CSHIP = self._get_cost_param(fixed_params, ['운송비', 'Transport Cost', 'CSHIP'], 2000)
                
                # FEU를 TEU로 변환 확인 (키 이름에서 FEU 언급 시)
                ship_keys = [k for k in fixed_params.keys() if 'FEU' in str(k).upper()]
                if ship_keys:
                    self.CSHIP = self.CSHIP / 2  # FEU를 TEU로 변환
                    print(f"🔄 FEU→TEU 변환: {self.CSHIP*2:.0f}/FEU → {self.CSHIP:.0f}/TEU")
                
                print(f"✅ 고정값 데이터에서 비용 파라미터 로드:")
                print(f"  - 운송비(CSHIP): ${self.CSHIP:.0f}/TEU")
                print(f"  - 유류할증료(CBAF): ${self.CBAF:.0f}/TEU") 
                print(f"  - ETA 패널티(CETA): ${self.CETA:.0f}/일")

                
            except Exception as e:
                print(f"⚠️ 고정값 데이터 로드 실패, 기본값 사용: {e}")
                self._use_default_cost_params()
        else:
            print("⚠️ 고정값 데이터 없음, 기본값 사용")
            self._use_default_cost_params()
        self.CEMPTY_SHIP = self.CSHIP + self.CBAF  # 빈 컨테이너 운송 총비용
        
    def setup_sets(self):
        """집합(Sets) 정의 - 시간적 복잡성 반영"""
        self.P = self.port_data['항구명'].unique().tolist()        # 모든 항구들의 집합
        self.R = self.schedule_data['루트번호'].unique().tolist()    # 모든 루트들의 집합
        self.V = self.vessel_data['선박명'].unique().tolist()       # 모든 선박들의 집합
        
        # 시간 기반 스케줄 정렬 및 집합 설정
        self._setup_time_based_schedules()
        
        self.num_schedules = len(self.I)
        self.num_ports = len(self.P)
        
        print(f"\n📊 모델 파라미터:")
        print(f"  - 스케줄 수: {self.num_schedules}")
        print(f"  - 항구 수: {self.num_ports}")
        print(f"  - 루트 수: {len(self.R)}")
        print(f"  - 선박 수: {len(self.V)}")
        print(f"  - 시간 범위: {self.time_horizon_start} ~ {self.time_horizon_end}")
        
    def _setup_time_based_schedules(self):
        """시간 기반 스케줄 정렬 및 시간적 복잡성 설정"""
        # ETD 시간으로 스케줄 정렬
        sorted_schedules = self.schedule_data.sort_values('ETD').reset_index(drop=True)
        self.I = sorted_schedules['스케줄 번호'].tolist()  # 시간 순서대로 정렬된 스케줄
        
        # 시간 인덱스 매핑 (스케줄 번호 -> 시간 순서)
        self.time_index_mapping = {schedule_id: idx for idx, schedule_id in enumerate(self.I)}
        
        # 시간 범위 설정
        self.time_horizon_start = sorted_schedules['ETD'].min()
        self.time_horizon_end = sorted_schedules['ETA'].max()
        
        # 스케줄별 시간 정보 저장
        self.ETD_i = sorted_schedules.set_index('스케줄 번호')['ETD'].to_dict()
        self.ETA_i = sorted_schedules.set_index('스케줄 번호')['ETA'].to_dict()
        
        # 시간별 스케줄 그룹화
        self._setup_temporal_schedule_groups()
        
        # 선박별 스케줄 타임라인
        self._setup_vessel_timeline()
        
        # 항구별 스케줄 타임라인
        self._setup_port_timeline()
        
        print(f"✅ 시간 기반 스케줄 정렬 완료: {len(self.I)}개 스케줄")
        
    def _setup_temporal_schedule_groups(self):
        """시간별 스케줄 그룹화"""
        # 일별 스케줄 그룹
        self.daily_schedules = {}
        for i in self.I:
            date_key = self.ETD_i[i].date()
            if date_key not in self.daily_schedules:
                self.daily_schedules[date_key] = []
            self.daily_schedules[date_key].append(i)
        
        # 주별 스케줄 그룹
        self.weekly_schedules = {}
        for i in self.I:
            week_key = self.ETD_i[i].isocalendar()[1]  # ISO 주차
            if week_key not in self.weekly_schedules:
                self.weekly_schedules[week_key] = []
            self.weekly_schedules[week_key].append(i)
        
        # 월별 스케줄 그룹
        self.monthly_schedules = {}
        for i in self.I:
            month_key = self.ETD_i[i].month
            if month_key not in self.monthly_schedules:
                self.monthly_schedules[month_key] = []
            self.monthly_schedules[month_key].append(i)
            
    def _setup_vessel_timeline(self):
        """선박별 스케줄 타임라인 설정"""
        self.vessel_timeline = {}
        
        for vessel in self.V:
            vessel_schedules = self.schedule_data[
                self.schedule_data['선박명'] == vessel
            ]['스케줄 번호'].tolist()
            
            # 시간 순서대로 정렬
            vessel_schedules.sort(key=lambda x: self.ETD_i[x])
            
            # 선박별 스케줄 간격 및 재사용 가능성 분석
            self.vessel_timeline[vessel] = {
                'schedules': vessel_schedules,
                'schedule_gaps': self._calculate_schedule_gaps(vessel_schedules),
                'reuse_possibility': self._analyze_vessel_reuse(vessel_schedules)
            }
            
    def _setup_port_timeline(self):
        """항구별 스케줄 타임라인 설정"""
        self.port_timeline = {}
        
        for port in self.P:
            # 출발 항구인 스케줄
            departure_schedules = self.schedule_data[
                self.schedule_data['출발항'] == port
            ]['스케줄 번호'].tolist()
            
            # 도착 항구인 스케줄
            arrival_schedules = self.schedule_data[
                self.schedule_data['도착항'] == port
            ]['스케줄 번호'].tolist()
            
            # 시간 순서대로 정렬
            departure_schedules.sort(key=lambda x: self.ETD_i[x])
            arrival_schedules.sort(key=lambda x: self.ETA_i[x])
            
            self.port_timeline[port] = {
                'departures': departure_schedules,
                'arrivals': arrival_schedules,
                'capacity_analysis': self._analyze_port_capacity(port, departure_schedules, arrival_schedules)
            }
            
    def _calculate_schedule_gaps(self, vessel_schedules):
        """선박 스케줄 간격 계산"""
        gaps = []
        for i in range(len(vessel_schedules) - 1):
            current_schedule = vessel_schedules[i]
            next_schedule = vessel_schedules[i + 1]
            
            # 현재 스케줄 도착 ~ 다음 스케줄 출발 간격
            gap_days = (self.ETD_i[next_schedule] - self.ETA_i[current_schedule]).days
            gaps.append({
                'from_schedule': current_schedule,
                'to_schedule': next_schedule,
                'gap_days': gap_days,
                'is_reusable': gap_days >= get_constant('data_processing.schedule.min_reuse_gap_days', 1)  # 1일 이상 간격이면 재사용 가능
            })
        return gaps
        
    def _analyze_vessel_reuse(self, vessel_schedules):
        """선박 재사용 가능성 분석"""
        if len(vessel_schedules) < 2:
            return {'reusable': False, 'reuse_count': 0, 'avg_gap': 0}
            
        gaps = self._calculate_schedule_gaps(vessel_schedules)
        reusable_gaps = [g for g in gaps if g['is_reusable']]
        
        return {
            'reusable': len(reusable_gaps) > 0,
            'reuse_count': len(reusable_gaps),
            'avg_gap': np.mean([g['gap_days'] for g in reusable_gaps]) if reusable_gaps else 0
        }
        
    def _analyze_port_capacity(self, port, departure_schedules, arrival_schedules):
        """항구별 동시 처리 능력 분석"""
        # 시간별 출발/도착 스케줄 수 계산
        time_slots = {}
        
        # 출발 스케줄 처리
        for schedule_id in departure_schedules:
            date_key = self.ETD_i[schedule_id].date()
            if date_key not in time_slots:
                time_slots[date_key] = {'departures': 0, 'arrivals': 0}
            time_slots[date_key]['departures'] += 1
            
        # 도착 스케줄 처리
        for schedule_id in arrival_schedules:
            date_key = self.ETA_i[schedule_id].date()
            if date_key not in time_slots:
                time_slots[date_key] = {'departures': 0, 'arrivals': 0}
            time_slots[date_key]['arrivals'] += 1
            
        # 동시 처리 능력 분석
        max_daily_operations = max(
            [slot['departures'] + slot['arrivals'] for slot in time_slots.values()]
        ) if time_slots else 0
        
        return {
            'max_daily_operations': max_daily_operations,
            'daily_breakdown': time_slots,
            'capacity_utilization': max_daily_operations / 24 if max_daily_operations > 0 else 0  # 시간당 평균
        }
        
    def setup_route_parameters(self):
        """루트 관련 파라미터 설정"""
        self.O_i = self.schedule_data.set_index('스케줄 번호')['출발항'].to_dict()
        self.D_i = self.schedule_data.set_index('스케줄 번호')['도착항'].to_dict()
        self.V_r = self.schedule_data.set_index('루트번호')['선박명'].to_dict()
        
        # 주문량 처리
        Q_r_raw = self.schedule_data.groupby('루트번호')['주문량(KG)'].first()
        self.Q_r = {}
        
        for r, q in Q_r_raw.items():
            self.Q_r[r] = self.data_loader.parse_order_quantity(q)
        
        # 주문량을 KG에서 TEU 단위로 변환
        self.D_ab = {}
        for r in self.R:
            if r in self.Q_r:
                self.D_ab[r] = max(1, int(np.ceil(self.Q_r[r] / self.KG_PER_TEU)))
            else:
                self.D_ab[r] = get_constant('data_processing.defaults.demand_default', 1)
                
    def setup_capacity_parameters(self):
        """선박 용량 관련 파라미터 설정"""
        self.CAP_v = self.vessel_data.set_index('선박명')['용량(TEU)'].to_dict()
        
        # 루트별 선박 용량 매핑
        self.CAP_v_r = {}
        for r in self.V_r:
            vessel_name = self.V_r[r]
            if vessel_name in self.CAP_v:
                self.CAP_v_r[r] = self.CAP_v[vessel_name]
            else:
                self.CAP_v_r[r] = get_constant('physical.default_vessel_capacity', 10000)
                
    def setup_delay_parameters(self):
        """지연 관련 파라미터 설정"""
        self.ETA_i = pd.to_datetime(
            self.schedule_data.set_index('스케줄 번호')['ETA']
        ).to_dict()
        
        # 딜레이 데이터 처리
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
                self.DELAY_i[i] = get_constant('data_processing.defaults.delay_default', 0)
                
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
                
    def setup_ga_parameters(self, version: str = 'default'):
        """GA 파라미터 설정 - 버전별 설정 지원"""
        
        # 버전별 파라미터 설정
        version_configs = {
            'quick': {
                'population_size': 50,
                'max_generations': 20,
                'num_elite': 10,
                'convergence_patience': 10,
                'description': '빠른 테스트 (20세대)'
            },
            'medium': {
                'population_size': 100,
                'max_generations': 50,
                'num_elite': 20,
                'convergence_patience': 25,
                'description': '중간 테스트 (50세대)'
            },
            'standard': {
                'population_size': 200,
                'max_generations': 100,
                'num_elite': 40,
                'convergence_patience': 50,
                'description': '표준 실행 (100세대)'
            },
            'full': {
                'population_size': 1000,
                'max_generations': 2000,
                'num_elite': 200,
                'convergence_patience': 200,
                'description': '전체 실행 (2000세대)'
            },
            'default': {
                'population_size': 100,
                'max_generations': 100,
                'num_elite': 20,
                'convergence_patience': 50,
                'description': '기본 설정 (100세대)'
            }
        }
        
        # 선택된 버전의 설정 적용
        config = version_configs.get(version, version_configs['default'])
        
        self.version_description = config['description']
        self.population_size = config['population_size']
        self.num_elite = config['num_elite']
        self.max_generations = config['max_generations']
        self.convergence_patience = config['convergence_patience']
        
        # 공통 파라미터 (설정 파일에서 로드)
        self.p_crossover = get_constant('genetic_algorithm.p_crossover', 0.85)
        self.p_mutation = get_constant('genetic_algorithm.p_mutation', 0.25)
        self.target_fitness = get_constant('genetic_algorithm.target_fitness', -3000)
        
        # 수렴 감지 및 조기 종료 파라미터 (설정 파일에서 로드)
        self.convergence_threshold = get_constant('genetic_algorithm.convergence_threshold', 0.0005)
        self.stagnation_counter = get_constant('system.initialization.stagnation_counter', 0)
        
        # 성능 추적 파라미터
        self.best_ever_fitness = float('-inf')
        self.generation_stats = []
        self.diversity_history = []
        
        # 성능 최적화: 병렬 처리 및 벡터화 강화
        self.use_adaptive_mutation = True
    
    def calculate_empty_container_levels(self, individual: Dict[str, Any]) -> np.ndarray:
        """
        개체의 xF, xE 값에 기반하여 적절한 최종 빈 컨테이너 수 y를 계산
        y_ip = 스케줄 i의 항구 p의 최종 empty 컨테이너 수 (TEU)
        
        컨테이너 흐름: y_(i+1)p = y_ip + (들어온 empty + 들어온 full) - (나간 empty + 나간 full)
        - 들어온 full은 empty로 전환
        - 나간 full은 empty를 소모
        
        Parameters:
        -----------
        individual : Dict[str, Any]
            GA 개체 (xF, xE 포함)
            
        Returns:
        --------
        np.ndarray
            계산된 최종 빈 컨테이너 수 배열 (num_schedules, num_ports)
        """
        y = np.zeros((self.num_schedules, self.num_ports))
        
        # 각 항구별 빈 컨테이너 수준을 스케줄 순서대로 계산
        port_empty_levels = {p: self.I0_p.get(p, 0) for p in self.P}  # 초기 빈 컨테이너 수
        
        for i_idx, i in enumerate(self.I):
            schedule_info = self.schedule_data[self.schedule_data['스케줄 번호'] == i]
            
            if not schedule_info.empty:
                origin_port = schedule_info['출발항'].iloc[0]
                dest_port = schedule_info['도착항'].iloc[0]
                
                if origin_port in self.P and dest_port in self.P:
                    # 출발항에서 컨테이너가 나감 (빈 컨테이너 소모)
                    outgoing_containers = individual['xF'][i_idx] + individual['xE'][i_idx]
                    port_empty_levels[origin_port] = max(0, 
                        port_empty_levels[origin_port] - outgoing_containers)
                    
                    # 도착항에서 컨테이너가 들어옴
                    # Full 컨테이너는 empty로 전환, Empty 컨테이너는 그대로 추가
                    incoming_full = individual['xF'][i_idx]  # full -> empty 전환
                    incoming_empty = individual['xE'][i_idx]  # empty 그대로
                    port_empty_levels[dest_port] += (incoming_full + incoming_empty)
                    
                    # 스케줄 i 이후의 각 항구별 최종 빈 컨테이너 수 저장
                    for p_idx, port in enumerate(self.P):
                        y[i_idx, p_idx] = max(0, port_empty_levels[port])
        
        return y
    
    def _get_cost_param(self, params_dict: Dict[str, float], key_options: List[str], default_value: float) -> float:
        """다양한 키 이름으로 비용 파라미터를 찾아서 반환"""
        for key in key_options:
            if key in params_dict:
                return float(params_dict[key])
        
        # 부분 매치 시도 (키에 포함된 단어로 찾기)
        for param_key, param_value in params_dict.items():
            for key_option in key_options:
                if key_option.lower() in param_key.lower() or param_key.lower() in key_option.lower():
                    return float(param_value)
        
        return default_value
    
    def _use_default_cost_params(self):
        """기본 비용 파라미터 설정"""
        # 기본값 설정 (설정 파일에서 로드)
        self.CSHIP = get_constant('costs.default.cship', 1000)
        self.CBAF = get_constant('costs.default.cbaf', 100)
        self.CETA = get_constant('costs.default.ceta', 150)
        
    def get_schedule_conflicts(self, individual: Dict[str, Any]) -> Dict[str, List]:
        """스케줄 충돌 검사"""
        conflicts = {
            'vessel_conflicts': [],
            'port_conflicts': [],
            'temporal_constraints': []
        }
        
        # 선박별 스케줄 충돌 검사
        for vessel in self.V:
            vessel_schedules = []
            for i_idx, schedule_id in enumerate(self.I):
                schedule_info = self.schedule_data[self.schedule_data['스케줄 번호'] == schedule_id]
                if not schedule_info.empty and schedule_info['선박명'].iloc[0] == vessel:
                    vessel_schedules.append((schedule_id, self.ETD_i[schedule_id], self.ETA_i[schedule_id]))
            
            # 시간 겹침 검사
            for i in range(len(vessel_schedules)):
                for j in range(i+1, len(vessel_schedules)):
                    s1_id, s1_etd, s1_eta = vessel_schedules[i]
                    s2_id, s2_etd, s2_eta = vessel_schedules[j]
                    
                    if s1_etd <= s2_eta and s2_etd <= s1_eta:  # 시간 겹침
                        conflicts['vessel_conflicts'].append({
                            'vessel': vessel,
                            'schedule1': s1_id,
                            'schedule2': s2_id,
                            'conflict_type': 'time_overlap'
                        })
        
        # 항구별 용량 초과 검사
        for port in self.P:
            daily_operations = {}
            for i_idx, schedule_id in enumerate(self.I):
                schedule_info = self.schedule_data[self.schedule_data['스케줄 번호'] == schedule_id]
                if not schedule_info.empty:
                    origin_port = schedule_info['출발항'].iloc[0]
                    dest_port = schedule_info['도착항'].iloc[0]
                    
                    if origin_port == port:
                        etd_date = self.ETD_i[schedule_id].date()
                        daily_operations[etd_date] = daily_operations.get(etd_date, 0) + 1
                    
                    if dest_port == port:
                        eta_date = self.ETA_i[schedule_id].date()
                        daily_operations[eta_date] = daily_operations.get(eta_date, 0) + 1
            
            # 일일 최대 처리 능력 초과 검사 (가정: 항구당 최대 10개 스케줄/일)
            max_capacity = get_constant('data_processing.defaults.max_capacity', 10)
            for date, operations in daily_operations.items():
                if operations > max_capacity:
                    conflicts['port_conflicts'].append({
                        'port': port,
                        'date': date,
                        'operations': operations,
                        'capacity': max_capacity
                    })
        
        return conflicts
    
    def validate_temporal_feasibility(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """시간적 실행 가능성 검증"""
        conflicts = self.get_schedule_conflicts(individual)
        penalty_score = 0
        recommendations = []
        
        # 선박 충돌 패널티
        vessel_conflicts = len(conflicts['vessel_conflicts'])
        if vessel_conflicts > 0:
            penalty_score += vessel_conflicts * 1000
            recommendations.append(f"선박 스케줄 충돌 해결 필요: {vessel_conflicts}개")
        
        # 항구 용량 패널티
        port_conflicts = len(conflicts['port_conflicts'])
        if port_conflicts > 0:
            penalty_score += port_conflicts * 500
            recommendations.append(f"항구 용량 초과 해결 필요: {port_conflicts}개")
        
        # 용량 제약 검사
        capacity_violations = 0
        for i_idx, schedule_id in enumerate(self.I):
            total_containers = individual['xF'][i_idx] + individual['xE'][i_idx]
            schedule_info = self.schedule_data[self.schedule_data['스케줄 번호'] == schedule_id]
            if not schedule_info.empty:
                route_num = schedule_info['루트번호'].iloc[0]
                if route_num in self.CAP_v_r:
                    capacity = self.CAP_v_r[route_num]
                    if total_containers > capacity:
                        capacity_violations += 1
                        penalty_score += (total_containers - capacity) * 10
        
        if capacity_violations > 0:
            recommendations.append(f"선박 용량 초과 해결 필요: {capacity_violations}개 스케줄")
        
        return {
            'is_feasible': penalty_score == 0,
            'penalty_score': penalty_score,
            'recommendations': recommendations,
            'conflicts': conflicts
        }
    
    def get_container_flow_at_time(self, individual: Dict[str, Any], target_time) -> Dict[str, float]:
        """특정 시점의 컨테이너 흐름 계산"""
        port_containers = {p: self.I0_p.get(p, 0) for p in self.P}
        
        # 타겟 시점까지의 스케줄만 처리
        for i_idx, schedule_id in enumerate(self.I):
            if self.ETD_i[schedule_id] <= target_time:
                schedule_info = self.schedule_data[self.schedule_data['스케줄 번호'] == schedule_id]
                if not schedule_info.empty:
                    origin_port = schedule_info['출발항'].iloc[0]
                    dest_port = schedule_info['도착항'].iloc[0]
                    
                    if origin_port in self.P and dest_port in self.P:
                        # 출발항에서 컨테이너 소모
                        outgoing = individual['xF'][i_idx] + individual['xE'][i_idx]
                        port_containers[origin_port] = max(0, port_containers[origin_port] - outgoing)
                        
                        # 도착항에서 컨테이너 추가 (ETA가 타겟 시점 이전인 경우)
                        if self.ETA_i[schedule_id] <= target_time:
                            incoming = individual['xF'][i_idx] + individual['xE'][i_idx]
                            port_containers[dest_port] += incoming
        
        return port_containers