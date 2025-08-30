#!/bin/bash

# 롤링 최적화 실행 스크립트
# 시간 윈도우를 이동하며 지속적으로 최적화 수행

echo "🔄 Ocean Shipping Rolling Optimization"
echo "======================================"

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_CMD="python3"

# 파라미터 설정
WINDOW_SIZE_DAYS=30
OVERLAP_DAYS=7
GA_GENERATIONS=50
ENABLE_WARM_START=true
SAVE_RESULTS=true
EXPORT_ANALYSIS=true

# 명령행 인수 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--window-size)
            WINDOW_SIZE_DAYS="$2"
            shift 2
            ;;
        -o|--overlap)
            OVERLAP_DAYS="$2"
            shift 2
            ;;
        -g|--generations)
            GA_GENERATIONS="$2"
            shift 2
            ;;
        --no-warm-start)
            ENABLE_WARM_START=false
            shift
            ;;
        --no-save)
            SAVE_RESULTS=false
            shift
            ;;
        --no-analysis)
            EXPORT_ANALYSIS=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -w, --window-size DAYS       Window size in days (default: 30)"
            echo "  -o, --overlap DAYS           Overlap between windows in days (default: 7)"
            echo "  -g, --generations COUNT      GA generations per window (default: 50)"
            echo "  --no-warm-start              Disable warm start optimization"
            echo "  --no-save                    Don't save optimization results"
            echo "  --no-analysis                Don't export performance analysis"
            echo "  -h, --help                   Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 환경 확인
cd "$PROJECT_ROOT"

echo "📋 Configuration:"
echo "  - Window size: $WINDOW_SIZE_DAYS days"
echo "  - Window overlap: $OVERLAP_DAYS days"
echo "  - GA generations per window: $GA_GENERATIONS"
echo "  - Warm start: $ENABLE_WARM_START"
echo "  - Save results: $SAVE_RESULTS"
echo "  - Export analysis: $EXPORT_ANALYSIS"
echo ""

# Python 스크립트 실행
$PYTHON_CMD -c "
import sys
import os
sys.path.append('$PROJECT_ROOT')

from datetime import datetime
from data.data_loader import DataLoader
from models.parameters import GAParameters
from advanced_features.rolling_optimization import RollingOptimizer, TimeWindowManager

print('🚀 Starting rolling optimization...')

try:
    # 데이터 로드
    print('📂 Loading data...')
    data_loader = DataLoader()
    
    # GA 파라미터 생성
    print('🔧 Initializing parameters...')
    ga_params = GAParameters(data_loader, version='standard')
    
    # Python boolean 변수로 변환
    enable_warm_start = '$ENABLE_WARM_START' == 'true'
    save_results = '$SAVE_RESULTS' == 'true'
    export_analysis = '$EXPORT_ANALYSIS' == 'true'
    
    # 롤링 최적화기 생성
    print('🔄 Creating rolling optimizer...')
    rolling_optimizer = RollingOptimizer(
        ga_params, 
        window_size_days=$WINDOW_SIZE_DAYS,
        overlap_days=$OVERLAP_DAYS,
        ga_generations=$GA_GENERATIONS
    )
    
    # 윈도우 매니저 상태 출력
    window_stats = rolling_optimizer.window_manager.get_window_stats()
    print(f'🪟 Time window configuration:')
    print(f'   - Total windows: {window_stats[\"total_windows\"]}')
    print(f'   - Average schedules per window: {window_stats[\"avg_schedules_per_window\"]:.1f}')
    print(f'   - Schedule range: {window_stats[\"min_schedules\"]} - {window_stats[\"max_schedules\"]}')
    
    # 윈도우 커버리지 검증
    coverage_stats = rolling_optimizer.window_manager.validate_window_coverage()
    print(f'   - Coverage: {coverage_stats[\"coverage_percentage\"]:.1f}%')
    if not coverage_stats['coverage_complete']:
        print(f'   ⚠️ Missing schedules: {len(coverage_stats[\"missing_schedules\"])}')
    
    print('')
    
    # 롤링 최적화 실행
    print('⚡ Starting rolling optimization process...')
    start_time = datetime.now()
    
    rolling_summary = rolling_optimizer.run_rolling_optimization(
        enable_warm_start=enable_warm_start
    )
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print('')
    print('📊 Rolling Optimization Results:')
    print(f'   - Status: {rolling_summary[\"status\"]}')
    print(f'   - Total windows: {rolling_summary[\"total_windows\"]}')
    print(f'   - Successful windows: {rolling_summary[\"successful_windows\"]}')
    print(f'   - Failed windows: {rolling_summary[\"failed_windows\"]}')
    print(f'   - Success rate: {rolling_summary[\"successful_windows\"]/rolling_summary[\"total_windows\"]*100:.1f}%')
    print(f'   - Total optimization time: {rolling_summary[\"total_optimization_time\"]:.1f}s')
    print(f'   - Average fitness: {rolling_summary[\"average_fitness\"]:.2f}')
    print(f'   - Total schedules optimized: {rolling_summary[\"total_schedules_optimized\"]}')
    
    # 성능 분석
    if export_analysis:
        print('')
        print('📈 Analyzing performance...')
        performance_analysis = rolling_optimizer.analyze_window_performance()
        
        if performance_analysis.get('fitness_stats'):
            fs = performance_analysis['fitness_stats']
            ts = performance_analysis['time_stats']
            em = performance_analysis['efficiency_metrics']
            
            print('   Performance Statistics:')
            print(f'     - Fitness range: {fs[\"min\"]:.2f} - {fs[\"max\"]:.2f}')
            print(f'     - Fitness std dev: {fs[\"std\"]:.2f}')
            print(f'     - Avg time per window: {ts[\"mean_seconds\"]:.1f}s')
            print(f'     - Total optimization time: {ts[\"total_seconds\"]:.1f}s')
            print(f'     - Efficiency: {em[\"fitness_per_second\"]:.3f} fitness/sec')
            print(f'     - Throughput: {em[\"schedules_per_second\"]:.1f} schedules/sec')
    
    # 전역 해 정보
    if rolling_summary['global_solution']:
        global_fitness = rolling_summary['global_solution']['fitness']
        print('')
        print(f'🎯 Global Solution:')
        print(f'   - Global fitness: {global_fitness:.2f}')
        print(f'   - Construction method: {rolling_summary[\"global_solution\"][\"construction_method\"]}')
    
    # 결과 저장
    if save_results:
        print('')
        print('💾 Saving results...')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 결과 디렉토리 생성
        os.makedirs('results', exist_ok=True)
        
        # 롤링 요약 저장
        import json
        summary_file = f'results/rolling_summary_{timestamp}.json'
        
        # datetime 객체를 문자열로 변환
        def datetime_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError
        
        with open(summary_file, 'w') as f:
            json.dump(rolling_summary, f, default=datetime_converter, indent=2)
        print(f'   📄 Summary saved to {summary_file}')
        
        # 전역 해 저장
        if rolling_summary['global_solution']:
            import pickle
            solution_file = f'results/rolling_solution_{timestamp}.pkl'
            with open(solution_file, 'wb') as f:
                pickle.dump(rolling_summary['global_solution'], f)
            print(f'   🧬 Global solution saved to {solution_file}')
        
        # 성능 분석 저장
        if export_analysis and performance_analysis.get('fitness_stats'):
            analysis_file = f'results/rolling_analysis_{timestamp}.json'
            with open(analysis_file, 'w') as f:
                json.dump(performance_analysis, f, default=datetime_converter, indent=2)
            print(f'   📊 Performance analysis saved to {analysis_file}')
    
    # 리포트 생성
    print('')
    print('📋 Generating report...')
    if export_analysis and performance_analysis.get('fitness_stats'):
        report = rolling_optimizer.generate_rolling_report(rolling_summary, performance_analysis)
    else:
        # 기본 리포트 생성
        report = f'''🔄 Rolling Optimization Report
========================
Status: {rolling_summary[\"status\"]}
Total Windows: {rolling_summary[\"total_windows\"]}
Successful: {rolling_summary[\"successful_windows\"]}
Failed: {rolling_summary[\"failed_windows\"]}
Success Rate: {rolling_summary[\"successful_windows\"]/rolling_summary[\"total_windows\"]*100:.1f}%
Total Time: {rolling_summary[\"total_optimization_time\"]:.1f}s
Average Fitness: {rolling_summary[\"average_fitness\"]:.2f}
'''
    
    if save_results:
        report_file = f'results/rolling_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'   📋 Report saved to {report_file}')
    
    print('')
    print('✅ Rolling optimization completed successfully!')
    
    # 최종 리포트 출력
    print('')
    print(report)
    
except Exception as e:
    print(f'❌ Rolling optimization failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

echo ""
echo "🎉 Rolling optimization script completed!"