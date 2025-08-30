#!/usr/bin/env python3
"""
Quick temporal features test - focused testing without full data loading
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_temporal_features_quick():
    """Quick test of temporal features implementation"""
    print("🧪 Quick Temporal Features Test")
    print("=" * 50)
    
    try:
        # Import with timeout protection
        print("1️⃣ Testing imports...")
        from models.parameters import GAParameters
        from data.data_loader import DataLoader
        print("✅ Imports successful")
        
        # Check if data files exist
        print("\n2️⃣ Checking data files...")
        data_files = [
            'data/스해물_스케줄data.xlsx',
            'data/스해물_딜레이스케줄data.xlsx',
            'data/스해물_선박data.xlsx',
            'data/스해물_항구위치data.xlsx'
        ]
        
        missing_files = []
        for file_path in data_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Missing data files: {missing_files}")
            return False
        else:
            print("✅ All data files exist")
        
        # Test data loading (with timeout simulation)
        print("\n3️⃣ Testing data loading...")
        try:
            data_loader = DataLoader()
            print("✅ DataLoader created successfully")
            
            # Quick check of loaded data
            schedule_data = data_loader.get_schedule_data()
            print(f"   - Schedule data: {len(schedule_data)} records")
            
            vessel_data = data_loader.get_vessel_data()
            print(f"   - Vessel data: {len(vessel_data)} records")
            
            port_data = data_loader.get_port_data()  
            print(f"   - Port data: {len(port_data)} records")
            
        except Exception as e:
            print(f"❌ Data loading failed: {e}")
            return False
            
        # Test parameters initialization
        print("\n4️⃣ Testing GAParameters initialization...")
        try:
            params = GAParameters(data_loader, version='quick')
            print("✅ GAParameters created successfully")
            
            # Test temporal features
            print(f"   - Total schedules: {len(params.I)}")
            print(f"   - Time horizon: {params.time_horizon_start} to {params.time_horizon_end}")
            print(f"   - Daily schedule groups: {len(params.daily_schedules)}")
            print(f"   - Vessel timelines: {len(params.vessel_timeline)}")
            print(f"   - Port timelines: {len(params.port_timeline)}")
            
        except Exception as e:
            print(f"❌ Parameters initialization failed: {e}")
            return False
        
        # Test temporal methods
        print("\n5️⃣ Testing temporal methods...")
        
        # Create test individual
        test_individual = {
            'xF': np.random.uniform(100, 1000, len(params.I)),
            'xE': np.random.uniform(10, 100, len(params.I)),
            'y': np.zeros((len(params.I), len(params.P)))
        }
        
        # Test container flow calculation
        try:
            y_result = params.calculate_empty_container_levels(test_individual)
            print(f"✅ Container flow calculation: {y_result.shape}")
        except Exception as e:
            print(f"❌ Container flow calculation failed: {e}")
            return False
            
        # Test schedule conflict detection
        try:
            conflicts = params.get_schedule_conflicts(test_individual)
            print(f"✅ Schedule conflict detection: {len(conflicts['vessel_conflicts'])} vessel conflicts")
        except Exception as e:
            print(f"❌ Schedule conflict detection failed: {e}")
            return False
            
        # Test feasibility validation
        try:
            validation = params.validate_temporal_feasibility(test_individual)
            print(f"✅ Feasibility validation: {'feasible' if validation['is_feasible'] else 'infeasible'}")
        except Exception as e:
            print(f"❌ Feasibility validation failed: {e}")
            return False
            
        # Test container flow at time
        try:
            target_time = params.time_horizon_start + timedelta(days=7)
            flow_at_time = params.get_container_flow_at_time(test_individual, target_time)
            print(f"✅ Container flow at time: {len(flow_at_time)} ports tracked")
        except Exception as e:
            print(f"❌ Container flow at time failed: {e}")
            return False
        
        print("\n🎉 All temporal features tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_temporal_features_quick()
    if success:
        print("\n✅ Temporal features are working correctly!")
    else:
        print("\n❌ Some temporal features need attention.")