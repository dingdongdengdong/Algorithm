#!/bin/bash

# 모든 고급 기능 통합 실행 스크립트
# 수요 예측 → 롤링 최적화 → 적응형 GA 순차 실행

echo "🌟 Ocean Shipping Advanced Features Suite"
echo "=========================================="

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 실행 모드 설정
RUN_FORECASTING=true
RUN_ROLLING=true
RUN_ADAPTIVE=true
FORECASTING_INTEGRATION=true
SAVE_ALL_RESULTS=true
GENERATE_COMBINED_REPORT=true

# 각 모듈별 설정
FORECAST_DAYS=30
WINDOW_SIZE=30
OVERLAP_DAYS=7
GA_GENERATIONS=50
ADAPTATION_INTERVAL=300
ADAPTIVE_DURATION=1800  # 30분

# 명령행 인수 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        --forecasting-only)
            RUN_ROLLING=false
            RUN_ADAPTIVE=false
            shift
            ;;
        --rolling-only)
            RUN_FORECASTING=false
            RUN_ADAPTIVE=false
            shift
            ;;
        --adaptive-only)
            RUN_FORECASTING=false
            RUN_ROLLING=false
            shift
            ;;
        --no-forecasting)
            RUN_FORECASTING=false
            shift
            ;;
        --no-rolling)
            RUN_ROLLING=false
            shift
            ;;
        --no-adaptive)
            RUN_ADAPTIVE=false
            shift
            ;;
        --no-integration)
            FORECASTING_INTEGRATION=false
            shift
            ;;
        --no-save)
            SAVE_ALL_RESULTS=false
            shift
            ;;
        --no-report)
            GENERATE_COMBINED_REPORT=false
            shift
            ;;
        -d|--duration)
            ADAPTIVE_DURATION="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Execution Control:"
            echo "  --forecasting-only          Run only demand forecasting"
            echo "  --rolling-only              Run only rolling optimization"
            echo "  --adaptive-only             Run only adaptive GA"
            echo "  --no-forecasting            Skip demand forecasting"
            echo "  --no-rolling                Skip rolling optimization"  
            echo "  --no-adaptive               Skip adaptive GA"
            echo ""
            echo "Feature Control:"
            echo "  --no-integration            Don't integrate forecasting with GA"
            echo "  --no-save                   Don't save results"
            echo "  --no-report                 Don't generate combined report"
            echo "  -d, --duration SEC          Adaptive GA duration in seconds (default: 1800)"
            echo ""
            echo "  -h, --help                  Show this help"
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

echo "📋 Execution Plan:"
echo "  - Demand Forecasting: $RUN_FORECASTING"
echo "  - Rolling Optimization: $RUN_ROLLING"
echo "  - Adaptive GA: $RUN_ADAPTIVE"
echo "  - Forecasting Integration: $FORECASTING_INTEGRATION"
echo "  - Save Results: $SAVE_ALL_RESULTS"
echo "  - Generate Combined Report: $GENERATE_COMBINED_REPORT"
echo ""

# 결과 저장 디렉토리 준비
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULTS_DIR="results/advanced_suite_$TIMESTAMP"

if [ "$SAVE_ALL_RESULTS" = true ]; then
    mkdir -p "$RESULTS_DIR"
    echo "📁 Results will be saved to: $RESULTS_DIR"
    echo ""
fi

# 실행 로그 파일
EXECUTION_LOG="$RESULTS_DIR/execution.log"
if [ "$SAVE_ALL_RESULTS" = true ]; then
    touch "$EXECUTION_LOG"
    echo "📝 Execution log: $EXECUTION_LOG"
    echo ""
fi

# 로깅 함수
log_message() {
    local message="$1"
    echo "$message"
    if [ "$SAVE_ALL_RESULTS" = true ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $message" >> "$EXECUTION_LOG"
    fi
}

# 오류 핸들링
handle_error() {
    local step="$1"
    local exit_code="$2"
    
    log_message "❌ $step failed with exit code $exit_code"
    
    if [ "$SAVE_ALL_RESULTS" = true ]; then
        echo "Error in step: $step" >> "$RESULTS_DIR/errors.txt"
        echo "Exit code: $exit_code" >> "$RESULTS_DIR/errors.txt"
        echo "Timestamp: $(date)" >> "$RESULTS_DIR/errors.txt"
        echo "---" >> "$RESULTS_DIR/errors.txt"
    fi
    
    echo ""
    echo "❌ Execution failed at step: $step"
    echo "Check logs for details: $EXECUTION_LOG"
    exit $exit_code
}

# 성공 체크
check_success() {
    if [ $? -ne 0 ]; then
        handle_error "$1" $?
    else
        log_message "✅ $1 completed successfully"
    fi
}

# 실행 시작
SUITE_START_TIME=$(date +%s)
log_message "🚀 Starting Advanced Features Suite execution..."

# 1. 수요 예측 실행
if [ "$RUN_FORECASTING" = true ]; then
    echo "🔮 Phase 1: Demand Forecasting"
    echo "=============================="
    
    FORECASTING_ARGS="--days $FORECAST_DAYS"
    if [ "$SAVE_ALL_RESULTS" = false ]; then
        FORECASTING_ARGS="$FORECASTING_ARGS --no-save"
    fi
    
    log_message "Starting demand forecasting with $FORECAST_DAYS days horizon..."
    
    bash "$SCRIPT_DIR/run_demand_forecasting.sh" $FORECASTING_ARGS
    check_success "Demand Forecasting"
    
    # 결과 이동
    if [ "$SAVE_ALL_RESULTS" = true ]; then
        mv results/demand_forecast_*.csv "$RESULTS_DIR/" 2>/dev/null || true
        mv results/forecast_report_*.txt "$RESULTS_DIR/" 2>/dev/null || true
        log_message "Forecasting results moved to suite directory"
    fi
    
    echo ""
fi

# 2. 롤링 최적화 실행
if [ "$RUN_ROLLING" = true ]; then
    echo "🔄 Phase 2: Rolling Optimization"
    echo "================================"
    
    ROLLING_ARGS="--window-size $WINDOW_SIZE --overlap $OVERLAP_DAYS --generations $GA_GENERATIONS"
    if [ "$SAVE_ALL_RESULTS" = false ]; then
        ROLLING_ARGS="$ROLLING_ARGS --no-save"
    fi
    
    log_message "Starting rolling optimization with ${WINDOW_SIZE}d windows..."
    
    bash "$SCRIPT_DIR/run_rolling_optimization.sh" $ROLLING_ARGS
    check_success "Rolling Optimization"
    
    # 결과 이동
    if [ "$SAVE_ALL_RESULTS" = true ]; then
        mv results/rolling_*.* "$RESULTS_DIR/" 2>/dev/null || true
        log_message "Rolling optimization results moved to suite directory"
    fi
    
    echo ""
fi

# 3. 적응형 GA 실행
if [ "$RUN_ADAPTIVE" = true ]; then
    echo "🧠 Phase 3: Adaptive GA System"
    echo "==============================="
    
    ADAPTIVE_ARGS="--duration $ADAPTIVE_DURATION --adaptation-interval $ADAPTATION_INTERVAL --strategy balanced"
    if [ "$SAVE_ALL_RESULTS" = false ]; then
        ADAPTIVE_ARGS="$ADAPTIVE_ARGS --no-save"
    fi
    
    log_message "Starting adaptive GA for $ADAPTIVE_DURATION seconds..."
    
    bash "$SCRIPT_DIR/run_adaptive_ga.sh" $ADAPTIVE_ARGS
    check_success "Adaptive GA System"
    
    # 결과 이동
    if [ "$SAVE_ALL_RESULTS" = true ]; then
        mv results/adaptive_*.* "$RESULTS_DIR/" 2>/dev/null || true
        mv results/learning_*.* "$RESULTS_DIR/" 2>/dev/null || true
        mv results/monitoring_*.* "$RESULTS_DIR/" 2>/dev/null || true
        log_message "Adaptive GA results moved to suite directory"
    fi
    
    echo ""
fi

# 4. 통합 리포트 생성
if [ "$GENERATE_COMBINED_REPORT" = true ]; then
    echo "📋 Phase 4: Combined Report Generation"
    echo "======================================"
    
    log_message "Generating combined report..."
    
    # 통합 리포트 생성
    COMBINED_REPORT="$RESULTS_DIR/combined_report.txt"
    
    cat > "$COMBINED_REPORT" << EOF
🌟 Ocean Shipping Advanced Features Suite - Execution Report
================================================================

Execution Summary:
- Timestamp: $(date)
- Duration: $(($(date +%s) - SUITE_START_TIME)) seconds
- Results Directory: $RESULTS_DIR

Modules Executed:
- Demand Forecasting: $RUN_FORECASTING
- Rolling Optimization: $RUN_ROLLING  
- Adaptive GA: $RUN_ADAPTIVE

Configuration:
- Forecast Days: $FORECAST_DAYS
- Window Size: $WINDOW_SIZE days
- Window Overlap: $OVERLAP_DAYS days
- GA Generations per Window: $GA_GENERATIONS
- Adaptation Interval: $ADAPTATION_INTERVAL seconds
- Adaptive GA Duration: $ADAPTIVE_DURATION seconds

Files Generated:
EOF

    # 생성된 파일 목록 추가
    if [ "$SAVE_ALL_RESULTS" = true ]; then
        echo "" >> "$COMBINED_REPORT"
        echo "Generated Files:" >> "$COMBINED_REPORT"
        ls -la "$RESULTS_DIR" | grep -v "^d" | awk '{print "  - " $9 " (" $5 " bytes)"}' >> "$COMBINED_REPORT"
    fi
    
    # 각 모듈의 개별 리포트 내용 통합
    echo "" >> "$COMBINED_REPORT"
    echo "Individual Module Reports:" >> "$COMBINED_REPORT"
    echo "=========================" >> "$COMBINED_REPORT"
    
    if [ "$RUN_FORECASTING" = true ] && [ -f "$RESULTS_DIR/forecast_report_"*".txt" ]; then
        echo "" >> "$COMBINED_REPORT"
        echo "1. DEMAND FORECASTING REPORT:" >> "$COMBINED_REPORT"
        echo "----------------------------" >> "$COMBINED_REPORT"
        cat "$RESULTS_DIR"/forecast_report_*.txt >> "$COMBINED_REPORT" 2>/dev/null || true
    fi
    
    if [ "$RUN_ROLLING" = true ] && [ -f "$RESULTS_DIR/rolling_report_"*".txt" ]; then
        echo "" >> "$COMBINED_REPORT"
        echo "2. ROLLING OPTIMIZATION REPORT:" >> "$COMBINED_REPORT"
        echo "-------------------------------" >> "$COMBINED_REPORT"  
        cat "$RESULTS_DIR"/rolling_report_*.txt >> "$COMBINED_REPORT" 2>/dev/null || true
    fi
    
    if [ "$RUN_ADAPTIVE" = true ] && [ -f "$RESULTS_DIR/adaptive_report_"*".txt" ]; then
        echo "" >> "$COMBINED_REPORT"
        echo "3. ADAPTIVE GA REPORT:" >> "$COMBINED_REPORT"
        echo "---------------------" >> "$COMBINED_REPORT"
        cat "$RESULTS_DIR"/adaptive_report_*.txt >> "$COMBINED_REPORT" 2>/dev/null || true
    fi
    
    # 통합 분석 추가
    echo "" >> "$COMBINED_REPORT"
    echo "Integrated Analysis:" >> "$COMBINED_REPORT"
    echo "===================" >> "$COMBINED_REPORT"
    echo "This suite executed multiple advanced optimization techniques:" >> "$COMBINED_REPORT"
    
    if [ "$RUN_FORECASTING" = true ]; then
        echo "- Demand forecasting provided future demand insights using LSTM/statistical models" >> "$COMBINED_REPORT"
    fi
    
    if [ "$RUN_ROLLING" = true ]; then
        echo "- Rolling optimization handled time-windowed optimization for scalability" >> "$COMBINED_REPORT"
    fi
    
    if [ "$RUN_ADAPTIVE" = true ]; then
        echo "- Adaptive GA system provided real-time adaptation to changing conditions" >> "$COMBINED_REPORT"
    fi
    
    echo "" >> "$COMBINED_REPORT"
    echo "The combination of these techniques provides a comprehensive solution for" >> "$COMBINED_REPORT"
    echo "complex ocean shipping optimization under uncertainty and dynamic conditions." >> "$COMBINED_REPORT"
    
    log_message "✅ Combined report generated: $COMBINED_REPORT"
    
    # 리포트 요약 출력
    echo ""
    echo "📊 Combined Report Summary:"
    echo "  - Total execution time: $(($(date +%s) - SUITE_START_TIME)) seconds"
    echo "  - Modules completed successfully: $([ "$RUN_FORECASTING" = true ] && echo -n "1 " || echo -n "")$([ "$RUN_ROLLING" = true ] && echo -n "2 " || echo -n "")$([ "$RUN_ADAPTIVE" = true ] && echo -n "3 " || echo -n "")"
    echo "  - Results saved to: $RESULTS_DIR"
    echo ""
fi

# 실행 완료
SUITE_END_TIME=$(date +%s)
TOTAL_DURATION=$((SUITE_END_TIME - SUITE_START_TIME))

log_message "🎉 Advanced Features Suite execution completed!"
log_message "Total execution time: ${TOTAL_DURATION} seconds ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)"

echo ""
echo "🎉 All Advanced Features Completed Successfully!"
echo "==============================================="
echo ""
echo "📊 Execution Summary:"
echo "  - Total time: ${TOTAL_DURATION} seconds ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)"
echo "  - Modules executed:"

if [ "$RUN_FORECASTING" = true ]; then
    echo "    ✅ Demand Forecasting (LSTM-based)"
fi

if [ "$RUN_ROLLING" = true ]; then
    echo "    ✅ Rolling Optimization (Time-windowed)"
fi

if [ "$RUN_ADAPTIVE" = true ]; then
    echo "    ✅ Adaptive GA (Real-time adaptation)"
fi

if [ "$SAVE_ALL_RESULTS" = true ]; then
    echo ""
    echo "📁 Results Location: $RESULTS_DIR"
    echo "📋 Combined Report: $RESULTS_DIR/combined_report.txt"
    echo "📝 Execution Log: $EXECUTION_LOG"
    
    # 결과 파일 개수 출력
    file_count=$(ls -1 "$RESULTS_DIR" | wc -l)
    echo "📄 Total files generated: $file_count"
fi

echo ""
echo "🌟 The Ocean Shipping GA system now includes state-of-the-art"
echo "   time series forecasting, rolling optimization, and adaptive"
echo "   learning capabilities for superior performance in dynamic"
echo "   shipping environments."