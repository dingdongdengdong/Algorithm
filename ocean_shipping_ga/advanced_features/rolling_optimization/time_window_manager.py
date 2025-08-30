#!/usr/bin/env python3
"""
시간 윈도우 관리자
롤링 최적화를 위한 시간 기반 스케줄 분할 및 관리
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.parameters import GAParameters


class TimeWindowManager:
    """시간 윈도우 기반 스케줄 관리"""
    
    def __init__(self, ga_parameters: GAParameters, 
                 window_size_days: int = 30, 
                 overlap_days: int = 7):
        """
        Parameters:
        -----------
        ga_parameters : GAParameters
            GA 파라미터 인스턴스
        window_size_days : int
            각 윈도우의 크기 (일)
        overlap_days : int
            윈도우 간 겹치는 기간 (일)
        """
        self.ga_params = ga_parameters
        self.window_size_days = window_size_days
        self.overlap_days = overlap_days
        
        self.time_windows = []
        self.window_schedules = {}
        self.current_window_idx = 0
        
        self._create_time_windows()
        
    def _create_time_windows(self):
        """시간 윈도우 생성"""
        print(f"🪟 Creating time windows (size: {self.window_size_days}d, overlap: {self.overlap_days}d)")
        
        start_date = self.ga_params.time_horizon_start
        end_date = self.ga_params.time_horizon_end
        total_days = (end_date - start_date).days
        
        current_start = start_date
        window_id = 0
        
        while current_start < end_date:
            window_end = min(current_start + timedelta(days=self.window_size_days), end_date)
            
            # 윈도우 정보 저장
            window_info = {
                'id': window_id,
                'start_date': current_start,
                'end_date': window_end,
                'duration_days': (window_end - current_start).days
            }
            
            self.time_windows.append(window_info)
            
            # 해당 윈도우에 속하는 스케줄들 찾기
            window_schedules = []
            for schedule_id in self.ga_params.I:
                schedule_etd = self.ga_params.ETD_i[schedule_id]
                if current_start <= schedule_etd < window_end:
                    window_schedules.append(schedule_id)
            
            self.window_schedules[window_id] = window_schedules
            
            # 다음 윈도우 시작점 (겹치는 부분 고려)
            current_start = current_start + timedelta(days=self.window_size_days - self.overlap_days)
            window_id += 1
        
        print(f"✅ Created {len(self.time_windows)} time windows")
        for i, window in enumerate(self.time_windows):
            schedule_count = len(self.window_schedules[i])
            print(f"   Window {i}: {window['start_date'].date()} - {window['end_date'].date()} ({schedule_count} schedules)")
    
    def get_window_parameters(self, window_id: int) -> GAParameters:
        """특정 윈도우의 GA 파라미터 생성"""
        if window_id >= len(self.time_windows):
            raise ValueError(f"Window ID {window_id} out of range")
        
        window_schedules = self.window_schedules[window_id]
        
        if not window_schedules:
            return None
        
        print(f"🔧 Creating parameters for window {window_id} ({len(window_schedules)} schedules)")
        
        # 새 GA 파라미터 인스턴스 생성 (복사)
        window_params = GAParameters(self.ga_params.data_loader, version='quick')
        
        # 윈도우 스케줄만 필터링
        window_params.I = window_schedules
        window_params.num_schedules = len(window_schedules)
        
        # 시간 인덱스 재매핑
        window_params.time_index_mapping = {
            schedule_id: idx for idx, schedule_id in enumerate(window_schedules)
        }
        
        # ETD, ETA 정보 필터링
        window_params.ETD_i = {
            schedule_id: self.ga_params.ETD_i[schedule_id] 
            for schedule_id in window_schedules
        }
        window_params.ETA_i = {
            schedule_id: self.ga_params.ETA_i[schedule_id] 
            for schedule_id in window_schedules
        }
        
        # 윈도우 시간 범위 업데이트
        if window_schedules:
            window_params.time_horizon_start = min(window_params.ETD_i.values())
            window_params.time_horizon_end = max(window_params.ETA_i.values())
        
        return window_params
    
    def get_overlap_schedules(self, window_id1: int, window_id2: int) -> List[int]:
        """두 윈도우 간 겹치는 스케줄 반환"""
        if window_id1 >= len(self.time_windows) or window_id2 >= len(self.time_windows):
            return []
        
        schedules1 = set(self.window_schedules[window_id1])
        schedules2 = set(self.window_schedules[window_id2])
        
        return list(schedules1.intersection(schedules2))
    
    def get_current_window(self) -> Dict:
        """현재 활성 윈도우 정보 반환"""
        if self.current_window_idx < len(self.time_windows):
            return self.time_windows[self.current_window_idx]
        return None
    
    def advance_window(self) -> bool:
        """다음 윈도우로 이동"""
        if self.current_window_idx < len(self.time_windows) - 1:
            self.current_window_idx += 1
            print(f"🔄 Advanced to window {self.current_window_idx}")
            return True
        return False
    
    def reset_to_first_window(self):
        """첫 번째 윈도우로 리셋"""
        self.current_window_idx = 0
        print("🔄 Reset to first window")
    
    def get_window_transition_info(self, from_window: int, to_window: int) -> Dict:
        """윈도우 전환 정보"""
        overlap_schedules = self.get_overlap_schedules(from_window, to_window)
        
        from_schedules = set(self.window_schedules[from_window])
        to_schedules = set(self.window_schedules[to_window])
        
        new_schedules = to_schedules - from_schedules
        removed_schedules = from_schedules - to_schedules
        
        return {
            'overlap_schedules': overlap_schedules,
            'new_schedules': list(new_schedules),
            'removed_schedules': list(removed_schedules),
            'overlap_count': len(overlap_schedules),
            'new_count': len(new_schedules),
            'removed_count': len(removed_schedules)
        }
    
    def create_schedule_continuity_map(self) -> Dict[int, List[int]]:
        """스케줄 연속성 매핑 생성 (어느 윈도우에 속하는지)"""
        schedule_windows = {}
        
        for window_id, schedules in self.window_schedules.items():
            for schedule_id in schedules:
                if schedule_id not in schedule_windows:
                    schedule_windows[schedule_id] = []
                schedule_windows[schedule_id].append(window_id)
        
        return schedule_windows
    
    def validate_window_coverage(self) -> Dict:
        """윈도우 커버리지 검증"""
        all_original_schedules = set(self.ga_params.I)
        all_windowed_schedules = set()
        
        for schedules in self.window_schedules.values():
            all_windowed_schedules.update(schedules)
        
        missing_schedules = all_original_schedules - all_windowed_schedules
        extra_schedules = all_windowed_schedules - all_original_schedules
        
        coverage_stats = {
            'total_original': len(all_original_schedules),
            'total_windowed': len(all_windowed_schedules),
            'missing_schedules': list(missing_schedules),
            'extra_schedules': list(extra_schedules),
            'coverage_complete': len(missing_schedules) == 0,
            'coverage_percentage': (len(all_windowed_schedules) / len(all_original_schedules)) * 100 if all_original_schedules else 0
        }
        
        return coverage_stats
    
    def get_window_stats(self) -> Dict:
        """윈도우 통계 정보"""
        stats = {
            'total_windows': len(self.time_windows),
            'window_size_days': self.window_size_days,
            'overlap_days': self.overlap_days,
            'current_window': self.current_window_idx,
            'schedules_per_window': {},
            'avg_schedules_per_window': 0,
            'min_schedules': float('inf'),
            'max_schedules': 0
        }
        
        schedule_counts = []
        for window_id, schedules in self.window_schedules.items():
            count = len(schedules)
            stats['schedules_per_window'][window_id] = count
            schedule_counts.append(count)
            stats['min_schedules'] = min(stats['min_schedules'], count)
            stats['max_schedules'] = max(stats['max_schedules'], count)
        
        stats['avg_schedules_per_window'] = np.mean(schedule_counts) if schedule_counts else 0
        
        return stats