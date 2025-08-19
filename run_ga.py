#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple runner script for GA Ocean Shipping Optimization
한글 인코딩 문제 해결된 간단한 실행 스크립트
"""

import os
import numpy as np
from GA_container import run_ocean_shipping_ga

def main():
    """GA 최적화 실행"""
    print("🌊 해상 운송 GA 최적화 시작")
    print("=" * 50)
    
    # 파일 경로 설정
    base_path = '/Users/dong/Downloads/ocean'
    file_paths = {
        'schedule': f'{base_path}/스해물_스케줄 data.xlsx',
        'delayed': f'{base_path}/스해물_딜레이 스케줄 data.xlsx',
        'vessel': f'{base_path}/스해물_선박 data.xlsx',
        'port': f'{base_path}/스해물_항구 위치 data.xlsx'
    }
    
    # 파일 존재 확인
    print("📁 데이터 파일 확인 중...")
    all_files_exist = True
    for name, path in file_paths.items():
        if os.path.exists(path):
            print(f"  ✅ {name}: {os.path.basename(path)}")
        else:
            print(f"  ❌ {name}: {path} - 파일을 찾을 수 없습니다")
            all_files_exist = False
    
    if not all_files_exist:
        print("\n❌ 필요한 데이터 파일이 없어 실행할 수 없습니다.")
        return
    
    print("\n🎲 랜덤 시드 설정...")
    np.random.seed(42)
    
    try:
        # GA 실행
        best_solution, fitness_history = run_ocean_shipping_ga(file_paths)
        
        print("\n✅ 최적화 완료!")
        print(f"📊 최적 적합도: {best_solution['fitness']:.2f}")
        
        return best_solution, fitness_history
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    main()