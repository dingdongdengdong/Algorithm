#!/usr/bin/env python3
"""
설정 관리자 (Configuration Manager)
YAML 설정 파일을 로드하고 시스템 전반에서 사용되는 상수값들을 중앙에서 관리
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """설정 파일을 로드하고 관리하는 클래스"""
    
    def __init__(self, config_path: str = None):
        """
        Parameters:
        -----------
        config_path : str, optional
            설정 파일 경로. None이면 기본 경로 사용
        """
        if config_path is None:
            # 프로젝트 루트 디렉토리 기준으로 설정 파일 경로 설정
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "constants.yaml"
        
        self.config_path = Path(config_path)
        self.config = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """설정 파일 로드"""
        try:
            if not self.config_path.exists():
                print(f"⚠️ 설정 파일을 찾을 수 없습니다: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            print(f"✅ 설정 파일 로드 완료: {self.config_path}")
            return True
            
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")
            return False
    
    def reload_config(self) -> bool:
        """설정 파일 재로드"""
        return self.load_config()
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        점(.)으로 구분된 키 경로로 설정값 조회
        
        Parameters:
        -----------
        key_path : str
            점(.)으로 구분된 키 경로 (예: 'physical.kg_per_teu')
        default : Any
            키가 없을 때 반환할 기본값
            
        Returns:
        --------
        Any
            설정값 또는 기본값
        """
        try:
            keys = key_path.split('.')
            value = self.config
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def get_physical_constants(self) -> Dict[str, Any]:
        """물리적 상수 조회"""
        return self.config.get('physical', {})
    
    def get_cost_parameters(self) -> Dict[str, Any]:
        """비용 파라미터 조회"""
        return self.config.get('costs', {})
    
    def get_ga_parameters(self) -> Dict[str, Any]:
        """유전 알고리즘 파라미터 조회"""
        return self.config.get('genetic_algorithm', {})
    
    def get_monitoring_parameters(self) -> Dict[str, Any]:
        """모니터링 파라미터 조회"""
        return self.config.get('monitoring', {})
    
    def get_imbalance_detection_parameters(self) -> Dict[str, Any]:
        """불균형 감지 파라미터 조회"""
        return self.config.get('imbalance_detection', {})
    
    def get_auto_redistribution_parameters(self) -> Dict[str, Any]:
        """자동 재배치 파라미터 조회"""
        return self.config.get('auto_redistribution', {})
    
    def get_redistribution_optimization_parameters(self) -> Dict[str, Any]:
        """재배치 최적화 파라미터 조회"""
        return self.config.get('redistribution_optimization', {})
    
    def get_forecasting_parameters(self) -> Dict[str, Any]:
        """예측 파라미터 조회"""
        return self.config.get('forecasting', {})
    
    def get_visualization_parameters(self) -> Dict[str, Any]:
        """시각화 파라미터 조회"""
        return self.config.get('visualization', {})
    
    def get_performance_parameters(self) -> Dict[str, Any]:
        """성능 최적화 파라미터 조회"""
        return self.config.get('performance', {})
    
    def get_data_processing_parameters(self) -> Dict[str, Any]:
        """데이터 처리 파라미터 조회"""
        return self.config.get('data_processing', {})
    
    def get_system_parameters(self) -> Dict[str, Any]:
        """시스템 동작 파라미터 조회"""
        return self.config.get('system', {})
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """모든 파라미터 조회"""
        return self.config.copy()
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        설정값 설정 (런타임에만 적용, 파일에는 저장되지 않음)
        
        Parameters:
        -----------
        key_path : str
            점(.)으로 구분된 키 경로
        value : Any
            설정할 값
            
        Returns:
        --------
        bool
            설정 성공 여부
        """
        try:
            keys = key_path.split('.')
            config = self.config
            
            # 마지막 키를 제외한 모든 키에 대해 딕셔너리 생성
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 마지막 키에 값 설정
            config[keys[-1]] = value
            return True
            
        except Exception as e:
            print(f"❌ 설정값 설정 실패: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """
        설정 파일 유효성 검증
        
        Returns:
        --------
        Dict[str, Any]
            검증 결과
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_sections': []
        }
        
        required_sections = [
            'physical', 'costs', 'genetic_algorithm', 'monitoring',
            'imbalance_detection', 'auto_redistribution'
        ]
        
        for section in required_sections:
            if section not in self.config:
                validation_result['missing_sections'].append(section)
                validation_result['is_valid'] = False
        
        # 필수 값들 검증
        required_values = [
            'physical.kg_per_teu',
            'physical.theta',
            'costs.default.cship',
            'genetic_algorithm.p_crossover',
            'genetic_algorithm.p_mutation'
        ]
        
        for value_path in required_values:
            if self.get(value_path) is None:
                validation_result['errors'].append(f"필수 값 누락: {value_path}")
                validation_result['is_valid'] = False
        
        return validation_result
    
    def print_config_summary(self):
        """설정 요약 출력"""
        print("\n" + "="*60)
        print("📋 설정 파일 요약")
        print("="*60)
        
        sections = [
            ('물리적 상수', 'physical'),
            ('비용 파라미터', 'costs'),
            ('유전 알고리즘', 'genetic_algorithm'),
            ('모니터링', 'monitoring'),
            ('불균형 감지', 'imbalance_detection'),
            ('자동 재배치', 'auto_redistribution')
        ]
        
        for section_name, section_key in sections:
            section_data = self.config.get(section_key, {})
            if section_data:
                print(f"\n🔧 {section_name}:")
                for key, value in section_data.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for sub_key, sub_value in value.items():
                            print(f"    {sub_key}: {sub_value}")
                    else:
                        print(f"  {key}: {value}")
        
        print("\n" + "="*60)


# 전역 설정 관리자 인스턴스
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """전역 설정 관리자 반환"""
    return config_manager


def get_constant(key_path: str, default: Any = None) -> Any:
    """설정값을 간편하게 조회하는 함수"""
    return config_manager.get(key_path, default)


# 사용 예시
if __name__ == "__main__":
    # 설정 요약 출력
    config_manager.print_config_summary()
    
    # 개별 값 조회 예시
    kg_per_teu = get_constant('physical.kg_per_teu')
    print(f"\nTEU당 무게: {kg_per_teu} kg")
    
    # 유효성 검증
    validation = config_manager.validate_config()
    print(f"\n설정 유효성: {'✅ 유효' if validation['is_valid'] else '❌ 유효하지 않음'}")
    
    if validation['errors']:
        print("오류:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if validation['warnings']:
        print("경고:")
        for warning in validation['warnings']:
            print(f"  - {warning}")
