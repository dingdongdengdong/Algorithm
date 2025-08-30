"""
데이터 로딩 및 전처리 모듈
"""

import pandas as pd
import numpy as np
import re
import os
from typing import Dict, Any, Optional, List
from datetime import datetime


class DataLoader:
    """
    엑셀 파일에서 데이터를 로드하고 전처리하는 클래스
    """
    
    def __init__(self, file_paths: Optional[Dict[str, str]] = None):
        """
        Parameters:
        -----------
        file_paths : dict, optional
            필요한 엑셀 파일 경로를 담은 딕셔너리
            None인 경우 패키지 내 data 폴더에서 자동 검색
            - 'schedule': 스케줄 데이터 파일 경로
            - 'delayed': 딜레이 스케줄 데이터 파일 경로
            - 'vessel': 선박 데이터 파일 경로
            - 'port': 항구 데이터 파일 경로
        """
        if file_paths is None:
            self.file_paths = self._get_default_file_paths()
        else:
            self.file_paths = file_paths
        self.data = {}
        
    def load_all_data(self) -> Dict[str, pd.DataFrame]:
        """모든 데이터 파일을 로드하고 정제"""
        print("📂 데이터 로딩 중...")
        
        # 원본 데이터 로드
        self.data['schedule'] = pd.read_excel(self.file_paths['schedule'])
        self.data['delayed'] = pd.read_excel(self.file_paths['delayed'])
        
        # 선박 데이터는 특별한 구조를 가지고 있어서 수동으로 처리
        vessel_raw = pd.read_excel(self.file_paths['vessel'])
        vessel_columns = ['선박명', '용량(TEU)']
        vessel_data = vessel_raw.iloc[2:].reset_index(drop=True)  # 처음 2행 건너뛰기
        vessel_data.columns = vessel_columns
        self.data['vessel'] = vessel_data
        
        # 항구 데이터도 특별한 구조를 가지고 있어서 수동으로 처리
        port_raw = pd.read_excel(self.file_paths['port'])
        port_columns = ['항구명', '위치_위도', '위치_경도']
        port_data = port_raw.iloc[2:].reset_index(drop=True)  # 처음 2행 건너뛰기
        port_data.columns = port_columns
        self.data['port'] = port_data
        self.data['fixed'] = pd.read_excel(self.file_paths['fixed'])
        
        print(f"✅ 스케줄 데이터: {len(self.data['schedule'])}개 로드")
        print(f"✅ 딜레이 데이터: {len(self.data['delayed'])}개 로드")
        print(f"✅ 선박 데이터: {len(self.data['vessel'])}개 로드")
        print(f"✅ 항구 데이터: {len(self.data['port'])}개 로드")
        print(f"✅ 고정값 데이터: {len(self.data['fixed'])}개 로드")
        
        # 데이터 정제 수행
        self._clean_datetime_columns()
        self._standardize_vessel_names()
        self._restructure_fixed_values()
        self._validate_data_integrity()
        
        print("✅ 데이터 정제 완료")
        return self.data
    
    def parse_order_quantity(self, q: Any) -> float:
        """
        주문량 데이터를 안전하게 파싱
        
        Parameters:
        -----------
        q : Any
            주문량 데이터 (문자열, 숫자, NaN 등)
            
        Returns:
        --------
        float
            파싱된 주문량
        """
        try:
            if pd.isna(q):  # NaN 값인 경우
                return 10000.0  # 기본값 설정
            elif isinstance(q, str):  # 문자열인 경우
                # 정규식을 사용해서 문자열에서 숫자만 추출
                numbers = re.findall(r'\d+\.?\d*', str(q))
                if numbers:
                    return float(numbers[0])
                else:
                    return 10000.0  # 숫자가 없으면 기본값
            else:
                return float(q)  # 이미 숫자인 경우 직접 변환
        except (ValueError, IndexError):
            print(f"Warning: Could not parse order quantity: {q}")
            return 10000.0  # 변환 실패시 기본값
    
    def get_schedule_data(self) -> pd.DataFrame:
        """스케줄 데이터 반환"""
        return self.data.get('schedule', pd.DataFrame())
    
    def get_delayed_data(self) -> pd.DataFrame:
        """딜레이 데이터 반환"""
        return self.data.get('delayed', pd.DataFrame())
    
    def get_vessel_data(self) -> pd.DataFrame:
        """선박 데이터 반환"""
        return self.data.get('vessel', pd.DataFrame())
    
    def get_port_data(self) -> pd.DataFrame:
        """항구 데이터 반환"""
        return self.data.get('port', pd.DataFrame())
    
    def get_fixed_data(self) -> pd.DataFrame:
        """고정값 데이터 반환"""
        return self.data.get('fixed', pd.DataFrame())
    
    def _get_default_file_paths(self) -> Dict[str, str]:
        """패키지 내 data 폴더에서 기본 파일 경로 설정"""
        # 현재 파일의 디렉토리를 기준으로 data 폴더 경로 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        file_paths = {
            'schedule': os.path.join(current_dir, '스해물_스케줄data.xlsx'),
            'delayed': os.path.join(current_dir, '스해물_딜레이스케줄data.xlsx'),
            'vessel': os.path.join(current_dir, '스해물_선박data.xlsx'),
            'port': os.path.join(current_dir, '스해물_항구위치data.xlsx'),
            'fixed': os.path.join(current_dir, '스해물_고정값data.xlsx')
        }
        
        # 파일 존재 확인
        for name, path in file_paths.items():
            if not os.path.exists(path):
                print(f"⚠️ 파일을 찾을 수 없습니다: {path}")
                raise FileNotFoundError(f"Required data file not found: {path}")
        
        return file_paths
    
    def _clean_datetime_columns(self):
        """날짜 컬럼을 datetime 형식으로 변환"""
        datetime_columns = {
            'schedule': ['ETD', 'ETA'],
            'delayed': ['ETD', 'ETA', '딜레이 ETA', ' 딜레이 ETA']  # 공백 있는 경우도 처리
        }
        
        for data_type, columns in datetime_columns.items():
            if data_type in self.data:
                df = self.data[data_type]
                converted_count = 0
                
                for col in columns:
                    if col in df.columns:
                        original_type = df[col].dtype
                        try:
                            # 다양한 날짜 형식 시도
                            df[col] = pd.to_datetime(df[col], errors='coerce', 
                                                   format=None, infer_datetime_format=True)
                            
                            # NaT 값 체크
                            nat_count = df[col].isna().sum()
                            if nat_count > 0:
                                print(f"⚠️  {data_type}.{col}: {nat_count}개 날짜 파싱 실패")
                            else:
                                print(f"✅ {data_type}.{col}: {original_type} → datetime64")
                                converted_count += 1
                                
                        except Exception as e:
                            print(f"❌ {data_type}.{col} 변환 실패: {e}")
                
                if converted_count > 0:
                    print(f"📅 {data_type} 데이터: {converted_count}개 날짜 컬럼 변환 완료")
    
    def _standardize_vessel_names(self):
        """선박명 표준화 (공백, 특수문자 정리)"""
        vessel_columns = {
            'schedule': '선박명',
            'vessel': '선박명'
        }
        
        standardized_count = 0
        vessel_mapping = {}
        
        for data_type, column in vessel_columns.items():
            if data_type in self.data and column in self.data[data_type].columns:
                df = self.data[data_type]
                original_names = df[column].unique()
                
                # 선박명 정제 함수
                def clean_vessel_name(name):
                    if pd.isna(name):
                        return name
                    
                    # 문자열로 변환하고 앞뒤 공백 제거
                    clean_name = str(name).strip()
                    
                    # 연속된 공백을 하나로 변경
                    clean_name = re.sub(r'\s+', ' ', clean_name)
                    
                    # 특수문자 정리 (따옴표 등)
                    clean_name = clean_name.replace("'", "").replace('"', '')
                    
                    return clean_name
                
                # 선박명 정제 적용
                df[column] = df[column].apply(clean_vessel_name)
                cleaned_names = df[column].unique()
                
                # 변경 사항 추적
                for orig, clean in zip(original_names, cleaned_names):
                    if orig != clean:
                        vessel_mapping[orig] = clean
                        standardized_count += 1
        
        if standardized_count > 0:
            print(f"🚢 선박명 표준화: {standardized_count}개 선박명 정리")
            for orig, clean in list(vessel_mapping.items())[:5]:  # 처음 5개만 표시
                print(f"   '{orig}' → '{clean}'")
        else:
            print("🚢 선박명: 정리할 항목 없음")
    
    def _restructure_fixed_values(self):
        """고정값 데이터를 key-value 구조로 재구성 (단위 고려)"""
        if 'fixed' not in self.data or self.data['fixed'].empty:
            print("⚠️  고정값 데이터 없음")
            return
        
        df = self.data['fixed']
        restructured_data = {}
        
        try:
            print(f"🔧 고정값 데이터 파싱 중...")
            print(f"  - 데이터 형태: {df.shape}")
            print(f"  - 컬럼: {df.columns.tolist()}")
            
            # 새로운 엑셀 구조: 첫 번째 컬럼이 파라미터명, 두 번째 컬럼이 값+단위
            for idx, row in df.iterrows():
                # 첫 번째 컬럼이 키, 두 번째 컬럼이 값+단위
                key = row.iloc[0]  # 첫 번째 컬럼
                value_with_unit = row.iloc[1]  # 두 번째 컬럼
                
                if pd.notna(key) and pd.notna(value_with_unit):
                    # 단위를 고려한 값 파싱
                    parsed_value = self._parse_value_with_unit(str(value_with_unit))
                    if parsed_value is not None:
                        restructured_data[key] = parsed_value
                        print(f"   ✅ {key}: {parsed_value} (원본: {value_with_unit})")
                    else:
                        print(f"   ❌ {key}: 파싱 실패 (원본: {value_with_unit})")
            
            # 재구성된 데이터 저장
            self.data['fixed_params'] = restructured_data
            
            print(f"💰 고정값 파라미터 재구성: {len(restructured_data)}개 항목")
            
        except Exception as e:
            print(f"❌ 고정값 데이터 재구성 실패: {e}")
            self.data['fixed_params'] = {}
    
    def _validate_data_integrity(self):
        """데이터 무결성 검증"""
        print("\n🔍 데이터 무결성 검증:")
        
        # 1. 선박명 일치 검증
        schedule_vessels = set(self.data['schedule']['선박명'].dropna())
        vessel_names = set(self.data['vessel']['선박명'].dropna())
        
        missing_vessels = schedule_vessels - vessel_names
        if missing_vessels:
            print(f"⚠️  스케줄에 있지만 선박 데이터에 없는 선박: {len(missing_vessels)}개")
            for vessel in list(missing_vessels)[:3]:
                print(f"     - {vessel}")
        else:
            print("✅ 선박명 일치: 모든 스케줄 선박이 선박 데이터에 존재")
        
        # 2. 딜레이 스케줄 일치 검증
        schedule_ids = set(self.data['schedule']['스케줄 번호'].dropna())
        delayed_ids = set(self.data['delayed']['스케줄 번호'].dropna())
        
        invalid_delays = delayed_ids - schedule_ids
        if invalid_delays:
            print(f"⚠️  존재하지 않는 스케줄의 딜레이: {len(invalid_delays)}개")
        else:
            print("✅ 딜레이 스케줄 일치: 모든 딜레이가 유효한 스케줄")
        
        # 3. 항구명 일치 검증
        schedule_ports = set(self.data['schedule']['출발항'].dropna()) | set(self.data['schedule']['도착항'].dropna())
        port_names = set(self.data['port']['항구명'].dropna())
        
        missing_ports = schedule_ports - port_names
        if missing_ports:
            print(f"⚠️  스케줄에 있지만 항구 데이터에 없는 항구: {len(missing_ports)}개")
            for port in missing_ports:
                print(f"     - {port}")
        else:
            print("✅ 항구명 일치: 모든 스케줄 항구가 항구 데이터에 존재")
        
        # 4. 날짜 유효성 검증
        if 'ETA' in self.data['schedule'].columns and 'ETD' in self.data['schedule'].columns:
            invalid_dates = (self.data['schedule']['ETA'] <= self.data['schedule']['ETD']).sum()
            if invalid_dates > 0:
                print(f"⚠️  ETA가 ETD보다 빠른 스케줄: {invalid_dates}개")
            else:
                print("✅ 날짜 순서: ETA > ETD 조건 만족")
    
    def get_fixed_params(self) -> Dict[str, float]:
        """재구성된 고정값 파라미터 반환"""
        return self.data.get('fixed_params', {})
    
    def _parse_value_with_unit(self, value_with_unit: str) -> Optional[float]:
        """
        단위가 포함된 값을 파싱하여 숫자로 변환
        
        Parameters:
        -----------
        value_with_unit : str
            단위가 포함된 값 (예: "100 USD/TEU", "150 USD/DAY")
            
        Returns:
        --------
        Optional[float]
            파싱된 숫자 값, 실패 시 None
        """
        try:
            # 공백 제거 및 대문자 변환
            value_with_unit = value_with_unit.strip().upper()
            
            # 숫자 부분 추출
            import re
            numbers = re.findall(r'\d+\.?\d*', value_with_unit)
            if not numbers:
                return None
            
            base_value = float(numbers[0])
            
            # 단위별 변환
            if 'USD/TEU' in value_with_unit:
                # TEU 단위는 그대로 사용
                return base_value
            elif 'USD/FEU' in value_with_unit:
                # FEU를 TEU로 변환 (FEU = 2 TEU)
                return base_value / 2
            elif 'USD/DAY' in value_with_unit or 'USD/일' in value_with_unit:
                # 일일 단위는 그대로 사용
                return base_value
            elif 'USD' in value_with_unit:
                # USD만 있는 경우 기본값으로 처리
                return base_value
            elif 'KG' in value_with_unit or 'KG/TEU' in value_with_unit:
                # KG 단위는 그대로 사용 (TEU 변환 기준)
                return base_value
            else:
                # 단위가 명확하지 않은 경우 기본값으로 처리
                print(f"     ⚠️  알 수 없는 단위: {value_with_unit}")
                return base_value
                
        except Exception as e:
            print(f"     ❌ 값 파싱 오류: {value_with_unit} - {e}")
            return None