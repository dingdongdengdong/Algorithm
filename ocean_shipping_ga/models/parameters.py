"""
GA 및 LP 모델 파라미터 설정 클래스
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from data.data_loader import DataLoader


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
        # 기본값 설정
        self.KG_PER_TEU = 30000      # TEU당 무게 (kg)
        self.theta = 0.001           # 빈 컨테이너 최소 비율
        
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
        """집합(Sets) 정의"""
        self.P = self.port_data['항구명'].unique().tolist()        # 모든 항구들의 집합
        self.I = self.schedule_data['스케줄 번호'].unique().tolist()  # 모든 스케줄들의 집합
        self.R = self.schedule_data['루트번호'].unique().tolist()    # 모든 루트들의 집합
        self.V = self.vessel_data['선박명'].unique().tolist()       # 모든 선박들의 집합
        
        self.num_schedules = len(self.I)
        self.num_ports = len(self.P)
        
        print(f"\n📊 모델 파라미터:")
        print(f"  - 스케줄 수: {self.num_schedules}")
        print(f"  - 항구 수: {self.num_ports}")
        print(f"  - 루트 수: {len(self.R)}")
        print(f"  - 선박 수: {len(self.V)}")
        
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
                self.D_ab[r] = 1
                
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
                self.CAP_v_r[r] = 10000
                
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
        
        # 공통 파라미터
        self.p_crossover = 0.85
        self.p_mutation = 0.25
        self.target_fitness = -3000
        
        # 수렴 감지 및 조기 종료 파라미터
        self.convergence_threshold = 0.0005
        self.stagnation_counter = 0
        
        # 성능 추적 파라미터
        self.best_ever_fitness = float('-inf')
        self.generation_stats = []
        self.diversity_history = []
        
        # M1 최적화: 병렬 처리 및 벡터화 강화
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
        self.CSHIP = 1000
        self.CBAF = 100
        self.CETA = 150