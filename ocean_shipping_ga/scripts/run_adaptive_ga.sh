#!/bin/bash

# 실시간 적응형 GA 실행 스크립트
# 환경에 적응하며 지속적으로 최적화 성능을 개선

echo "🧠 Ocean Shipping Adaptive GA System"
echo "===================================="

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_CMD="python3"

# 파라미터 설정
ADAPTATION_INTERVAL=300  # 5분
MONITORING_INTERVAL=30   # 30초
INITIAL_STRATEGY="balanced"
ENABLE_LEARNING=true
RUN_DURATION=3600       # 1시간 (초)
SAVE_STATE=true
EXPORT_LOGS=true

# 명령행 인수 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--adaptation-interval)
            ADAPTATION_INTERVAL="$2"
            shift 2
            ;;
        -m|--monitoring-interval)
            MONITORING_INTERVAL="$2"
            shift 2
            ;;
        -s|--strategy)
            INITIAL_STRATEGY="$2"
            shift 2
            ;;
        -d|--duration)
            RUN_DURATION="$2"
            shift 2
            ;;
        --no-learning)
            ENABLE_LEARNING=false
            shift
            ;;
        --no-save)
            SAVE_STATE=false
            shift
            ;;
        --no-logs)
            EXPORT_LOGS=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -i, --adaptation-interval SEC   Adaptation interval in seconds (default: 300)"
            echo "  -m, --monitoring-interval SEC   Monitoring interval in seconds (default: 30)"
            echo "  -s, --strategy STRATEGY         Initial strategy: aggressive|balanced|conservative|reactive (default: balanced)"
            echo "  -d, --duration SEC              Run duration in seconds (default: 3600)"
            echo "  --no-learning                   Disable learning system"
            echo "  --no-save                       Don't save adaptation state"
            echo "  --no-logs                       Don't export monitoring logs"
            echo "  -h, --help                      Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 전략 유효성 검사
case $INITIAL_STRATEGY in
    aggressive|balanced|conservative|reactive)
        ;;
    *)
        echo "❌ Invalid strategy: $INITIAL_STRATEGY"
        echo "Valid strategies: aggressive, balanced, conservative, reactive"
        exit 1
        ;;
esac

# 환경 확인
cd "$PROJECT_ROOT"

echo "📋 Configuration:"
echo "  - Adaptation interval: ${ADAPTATION_INTERVAL}s"
echo "  - Monitoring interval: ${MONITORING_INTERVAL}s"
echo "  - Initial strategy: $INITIAL_STRATEGY"
echo "  - Run duration: ${RUN_DURATION}s ($(($RUN_DURATION/60)) minutes)"
echo "  - Learning enabled: $ENABLE_LEARNING"
echo "  - Save state: $SAVE_STATE"
echo "  - Export logs: $EXPORT_LOGS"
echo ""

# 신호 핸들러 설정 (Ctrl+C로 안전한 종료)
cleanup() {
    echo ""
    echo "🛑 Received interrupt signal, shutting down adaptive GA..."
    # Python 프로세스에 종료 신호 전달
    if [[ -n $PYTHON_PID ]]; then
        kill -TERM $PYTHON_PID 2>/dev/null
        wait $PYTHON_PID 2>/dev/null
    fi
    echo "✅ Adaptive GA stopped safely"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Python 스크립트 실행
$PYTHON_CMD -c "
import sys
import os
import signal
import time
import threading
from datetime import datetime, timedelta

sys.path.append('$PROJECT_ROOT')

from data.data_loader import DataLoader
from models.parameters import GAParameters
from advanced_features.adaptive_systems import AdaptiveGA, RealTimeMonitor, LearningSystem

# 글로벌 변수
adaptive_ga = None
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    print('')
    print('🛑 Shutdown signal received...')
    shutdown_requested = True

# 신호 핸들러 등록
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print('🚀 Starting adaptive GA system...')

try:
    # 데이터 로드
    print('📂 Loading data...')
    data_loader = DataLoader()
    
    # GA 파라미터 생성
    print('🔧 Initializing parameters...')
    ga_params = GAParameters(data_loader, version='standard')
    
    # 적응형 GA 시스템 생성
    print('🧠 Creating adaptive GA system...')
    adaptive_ga = AdaptiveGA(
        ga_params,
        adaptation_interval=$ADAPTATION_INTERVAL,
        learning_enabled=$ENABLE_LEARNING
    )
    
    # 초기 전략 설정
    adaptive_ga.change_adaptation_strategy('$INITIAL_STRATEGY')
    
    # 모니터링 간격 조정
    adaptive_ga.monitor.monitoring_interval = $MONITORING_INTERVAL
    
    print(f'✅ Adaptive GA system initialized')
    print(f'   - Initial strategy: $INITIAL_STRATEGY')
    print(f'   - Learning enabled: $ENABLE_LEARNING')
    
    # 적응형 모드 시작
    print('')
    print('🔄 Starting adaptive mode...')
    adaptive_ga.start_adaptive_mode()
    
    # 실행 상태 정보
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=$RUN_DURATION)
    
    print(f'⏰ Adaptive GA will run until {end_time.strftime(\"%H:%M:%S\")}')
    print('   Press Ctrl+C to stop early')
    print('')
    
    # 상태 모니터링 루프
    last_status_time = datetime.now()
    status_interval = 60  # 1분마다 상태 출력
    
    while not shutdown_requested and datetime.now() < end_time:
        time.sleep(5)  # 5초마다 체크
        
        # 주기적 상태 출력
        if (datetime.now() - last_status_time).seconds >= status_interval:
            current_status = adaptive_ga.get_adaptation_status()
            
            print(f'📊 Status Update ({datetime.now().strftime(\"%H:%M:%S\")}):')
            print(f'   - Current strategy: {current_status[\"current_strategy\"]}')
            print(f'   - Total adaptations: {current_status[\"total_adaptations\"]}')
            print(f'   - Successful adaptations: {current_status[\"successful_adaptations\"]}')
            if current_status['total_adaptations'] > 0:
                success_rate = current_status['successful_adaptations'] / current_status['total_adaptations'] * 100
                print(f'   - Success rate: {success_rate:.1f}%')
            
            monitor_status = current_status['monitor_status']
            print(f'   - System health: {monitor_status.get(\"system_health\", \"unknown\")}')
            print(f'   - Recent alerts: {monitor_status.get(\"recent_alerts_count\", 0)}')
            print(f'   - Cache size: {current_status[\"cache_size\"]}')
            print('')
            
            last_status_time = datetime.now()
    
    # 적응형 모드 중지
    print('🛑 Stopping adaptive mode...')
    adaptive_ga.stop_adaptive_mode()
    
    # 최종 결과 분석
    print('')
    print('📊 Final Results Analysis:')
    final_status = adaptive_ga.get_adaptation_status()
    
    total_adaptations = final_status['total_adaptations']
    successful_adaptations = final_status['successful_adaptations']
    
    print(f'   - Runtime: {(datetime.now() - start_time).total_seconds():.0f} seconds')
    print(f'   - Total adaptations: {total_adaptations}')
    print(f'   - Successful adaptations: {successful_adaptations}')
    if total_adaptations > 0:
        success_rate = successful_adaptations / total_adaptations * 100
        print(f'   - Overall success rate: {success_rate:.1f}%')
    print(f'   - Final strategy: {final_status[\"current_strategy\"]}')
    
    # 성능 추세 분석
    if final_status['recent_performance']:
        recent_perf = final_status['recent_performance']
        fitness_values = [p['fitness'] for p in recent_perf]
        
        print(f'   - Recent performance average: {sum(fitness_values)/len(fitness_values):.2f}')
        print(f'   - Performance range: {min(fitness_values):.2f} - {max(fitness_values):.2f}')
    
    # 상태 저장
    if $SAVE_STATE:
        print('')
        print('💾 Saving adaptation state...')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        os.makedirs('results', exist_ok=True)
        
        # 적응 상태 저장
        state_file = f'results/adaptive_state_{timestamp}.pkl'
        adaptive_ga.dynamic_updater.save_adaptation_state(state_file)
        
        # 학습 시스템 상태 저장 (활성화된 경우)
        if $ENABLE_LEARNING and adaptive_ga.learning_system:
            learning_file = f'results/learning_state_{timestamp}.pkl'
            adaptive_ga.learning_system.save_learning_state(learning_file)
            print(f'   📚 Learning state saved to {learning_file}')
    
    # 모니터링 로그 내보내기
    if $EXPORT_LOGS:
        print('')
        print('📄 Exporting monitoring logs...')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logs_file = f'results/monitoring_logs_{timestamp}.json'
        adaptive_ga.monitor.export_metrics(logs_file, hours_back=24)
    
    # 최종 리포트 생성
    print('')
    print('📋 Generating final report...')
    final_report = adaptive_ga.generate_adaptation_report()
    
    if $SAVE_STATE:
        report_file = f'results/adaptive_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(final_report)
        print(f'   📋 Report saved to {report_file}')
    
    print('')
    print('✅ Adaptive GA system completed successfully!')
    
    # 최종 리포트 출력
    print('')
    print(final_report)
    
    # 학습 시스템 통계 (활성화된 경우)
    if $ENABLE_LEARNING and adaptive_ga.learning_system:
        print('')
        learning_stats = adaptive_ga.learning_system.get_learning_stats()
        if learning_stats.get('status') != 'no_data':
            print('🧠 Learning System Statistics:')
            print(f'   - Total experiences: {learning_stats[\"total_experiences\"]}')
            print(f'   - Success rate: {learning_stats[\"success_rate\"]:.1%}')
            print(f'   - Avg performance improvement: {learning_stats[\"avg_performance_improvement\"]:.2f}')
            print(f'   - Learning sessions: {learning_stats[\"learning_sessions\"]}')

except KeyboardInterrupt:
    print('')
    print('🛑 Interrupted by user')
    if adaptive_ga:
        adaptive_ga.stop_adaptive_mode()

except Exception as e:
    print(f'❌ Adaptive GA system failed: {e}')
    import traceback
    traceback.print_exc()
    
    if adaptive_ga:
        adaptive_ga.stop_adaptive_mode()
    
    exit(1)

finally:
    # 정리 작업
    if adaptive_ga:
        try:
            adaptive_ga.stop_adaptive_mode()
        except:
            pass
" &

PYTHON_PID=$!
wait $PYTHON_PID

echo ""
echo "🎉 Adaptive GA script completed!"