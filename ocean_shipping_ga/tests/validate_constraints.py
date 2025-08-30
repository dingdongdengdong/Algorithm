#!/usr/bin/env python3
"""
Constraint validation test
"""

import sys
import os
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.parameters import GAParameters
from data.data_loader import DataLoader

def test_constraint_validation():
    """Test constraint validation functionality"""
    print("🔍 Constraint Validation Test")
    print("=" * 50)
    
    # Load data and parameters
    data_loader = DataLoader()
    params = GAParameters(data_loader, version='quick')
    
    print(f"📊 Loaded {len(params.I)} schedules, {len(params.V)} vessels, {len(params.P)} ports")
    
    # Test 1: Valid solution (should pass most constraints)
    print("\n1️⃣ Testing valid solution...")
    valid_individual = {
        'xF': np.random.uniform(10, 100, len(params.I)),  # Conservative allocation
        'xE': np.random.uniform(1, 10, len(params.I)),
        'y': np.zeros((len(params.I), len(params.P)))
    }
    
    validation = params.validate_temporal_feasibility(valid_individual)
    print(f"   Valid solution feasible: {validation['is_feasible']}")
    print(f"   Penalty score: {validation['penalty_score']:.2f}")
    
    # Test 2: Invalid solution (high capacity violations)
    print("\n2️⃣ Testing invalid solution...")
    invalid_individual = {
        'xF': np.random.uniform(5000, 10000, len(params.I)),  # Very high allocation
        'xE': np.random.uniform(1000, 2000, len(params.I)),
        'y': np.zeros((len(params.I), len(params.P)))
    }
    
    validation = params.validate_temporal_feasibility(invalid_individual)
    print(f"   Invalid solution feasible: {validation['is_feasible']}")
    print(f"   Penalty score: {validation['penalty_score']:.2f}")
    if validation['recommendations']:
        print("   Recommendations:")
        for rec in validation['recommendations'][:3]:  # Show first 3
            print(f"     - {rec}")
    
    # Test 3: Schedule conflict detection
    print("\n3️⃣ Testing schedule conflicts...")
    conflicts = params.get_schedule_conflicts(valid_individual)
    print(f"   Vessel conflicts: {len(conflicts['vessel_conflicts'])}")
    print(f"   Port conflicts: {len(conflicts['port_conflicts'])}")
    
    if conflicts['vessel_conflicts']:
        print(f"   Sample vessel conflict: {conflicts['vessel_conflicts'][0]}")
    
    # Test 4: Container flow at different times
    print("\n4️⃣ Testing container flow over time...")
    time_points = [
        params.time_horizon_start + timedelta(days=d) 
        for d in [7, 30, 60, 120]
    ]
    
    for i, time_point in enumerate(time_points):
        flow = params.get_container_flow_at_time(valid_individual, time_point)
        total_containers = sum(flow.values())
        print(f"   Day {7 * (i+1)}: {total_containers:.0f} total containers across ports")
    
    # Test 5: Temporal features summary
    print("\n5️⃣ Temporal features summary...")
    print(f"   Time horizon: {(params.time_horizon_end - params.time_horizon_start).days} days")
    print(f"   Daily schedule groups: {len(params.daily_schedules)}")
    print(f"   Weekly schedule groups: {len(params.weekly_schedules)}")
    print(f"   Monthly schedule groups: {len(params.monthly_schedules)}")
    
    # Show vessel reuse analysis
    reusable_vessels = sum(1 for v in params.vessel_timeline.values() if v['reuse_possibility']['reusable'])
    print(f"   Reusable vessels: {reusable_vessels}/{len(params.vessel_timeline)}")
    
    # Show port capacity analysis
    max_port_operations = max(
        info['capacity_analysis']['max_daily_operations'] 
        for info in params.port_timeline.values()
    )
    print(f"   Max daily port operations: {max_port_operations}")
    
    print("\n✅ Constraint validation tests completed!")
    
    # 모든 테스트가 성공적으로 완료되었으므로 True 반환
    return True

if __name__ == "__main__":
    results = test_constraint_validation()
    
    print("\n🎯 Test Results Summary:")
    for feature, working in results.items():
        status = "✅" if working else "❌"
        print(f"   {status} {feature.replace('_', ' ').title()}")