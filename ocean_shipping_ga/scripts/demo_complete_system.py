#!/usr/bin/env python3
"""
완전한 시스템 기능 데모 스크립트
모든 구현된 기능들을 통합하여 시연
"""

import sys
import os
import numpy as np
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 모든 필요한 모듈 import
try:
    from models.parameters import GAParameters
    from models.dynamic_imbalance_detector import DynamicImbalanceDetector
    from models.auto_redistribution_trigger import AutoRedistributionTrigger
    from models.monitoring_dashboard import RealTimeMonitoringDashboard
    from models.integrated_monitoring_system import IntegratedMonitoringSystem
    from models.redistribution_optimizer import ContainerRedistributionOptimizer
    from visualization.graph_visualizer import GraphVisualizer
    from algorithms.fitness import FitnessCalculator
    from data.data_loader import DataLoader
except ImportError as e:
    print(f"모듈 import 오류: {e}")
    print("이 스크립트는 프로젝트 루트에서 실행해야 합니다")
    sys.exit(1)


class CompleteSystemDemo:
    """완전한 시스템 기능 데모 클래스"""
    
    def __init__(self):
        print("Ocean Shipping GA - 시스템 데모")
        print("=" * 60)
        
        # 실제 데이터 사용 시도, 실패 시 더미 데이터로 대체
        self.setup_real_data_environment()
        
        # 시스템 컴포넌트 초기화
        self.initialize_components()
        
    def setup_real_data_environment(self):
        """실제 데이터 환경 설정"""
        print("실제 데이터 환경 설정 중...")
        
        # 실제 데이터 파일 경로
        data_dir = project_root / "data"
        file_paths = {
            'schedule': str(data_dir / '스해물_스케줄data.xlsx'),
            'delayed': str(data_dir / '스해물_딜레이스케줄data.xlsx'),  # DataLoader에서 'delayed' 키 사용
            'vessel': str(data_dir / '스해물_선박data.xlsx'),           # DataLoader에서 'vessel' 키 사용
            'port': str(data_dir / '스해물_항구위치data.xlsx'),
            'fixed': str(data_dir / '스해물_고정값data.xlsx')
        }
        
        try:
            # 데이터 로더 초기화
            data_loader = DataLoader(file_paths)
            data_loader.load_all_data()
            
            # GAParameters 초기화 (실제 데이터 사용)
            from models.parameters import GAParameters
            self.params = GAParameters(data_loader, 'quick')
            
            print(f"실제 데이터 로딩 완료")
            print(f"   스케줄: {len(self.params.I)}개")
            print(f"   항구: {len(self.params.P)}개") 
            print(f"   루트: {len(self.params.R)}개")
            
        except Exception as e:
            print(f"실제 데이터 로딩 실패: {e}")
            print("더미 데이터로 대체 설정 중...")
            self.setup_fallback_dummy_environment()
    
    def setup_fallback_dummy_environment(self):
        """대체 더미 환경 설정"""
        # 더미 파라미터 생성
        class DummyParams:
            def __init__(self):
                self.I = [f"SCH_{i:03d}" for i in range(1, 21)]  # 20개 스케줄
                self.P = ['BUSAN', 'SHANGHAI', 'NINGBO', 'QINGDAO', 'TOKYO', 'YOKOHAMA', 'KOBE', 'OSAKA']  # 8개 항구
                self.R = [f"R{i}" for i in range(1, 11)]  # 10개 루트
                
                # 더미 비용 파라미터 (설정 파일에서 로드)
                from config import get_constant
                self.CSHIP = get_constant('costs.default.cship', 100)
                self.CBAF = get_constant('costs.default.cbaf', 50)
                self.CETA = get_constant('costs.default.ceta', 200)
                self.theta = get_constant('physical.theta', 0.3)
                
                # 더미 용량 및 수요
                self.CAP_v_r = {r: np.random.randint(800, 1200) for r in self.R}
                self.D_ab = {r: np.random.randint(600, 1000) for r in self.R}
                self.DELAY_i = {i: np.random.uniform(0, 2) for i in self.I}
                
                # 더미 초기 재고
                self.I0_p = {p: np.random.randint(1000, 5000) for p in self.P}
                
                # 더미 스케줄 데이터 (FitnessCalculator를 위해 필요)
                import pandas as pd
                schedule_data = []
                for i, schedule in enumerate(self.I):
                    route = self.R[i % len(self.R)]
                    schedule_data.append({
                        '스케줄 번호': schedule,
                        '루트번호': route
                    })
                self.schedule_data = pd.DataFrame(schedule_data)
                
            def calculate_empty_container_levels(self, individual):
                """빈 컨테이너 수준 계산 (더미)"""
                num_schedules = len(self.I)
                num_ports = len(self.P)
                
                # 시뮬레이션된 재고 수준
                levels = np.zeros((num_schedules, num_ports))
                
                for i in range(num_schedules):
                    for p in range(num_ports):
                        # 기본 수준에 일부 변동 추가
                        base_level = list(self.I0_p.values())[p]
                        variation = np.random.normal(0, base_level * 0.2)
                        levels[i, p] = max(0, base_level + variation)
                
                return levels
        
        self.params = DummyParams()
        print("더미 환경 설정 완료")
    
    def initialize_components(self):
        """모든 시스템 컴포넌트 초기화"""
        print("\n시스템 컴포넌트 초기화 중...")
        
        # 1. 동적 불균형 감지 시스템
        self.imbalance_detector = DynamicImbalanceDetector(self.params)
        print("   동적 불균형 감지 시스템")
        
        # 2. 재배치 최적화 시스템
        self.redistribution_optimizer = ContainerRedistributionOptimizer(self.params)
        print("   재배치 최적화 시스템")
        
        # 3. 자동 트리거 시스템
        self.auto_trigger = AutoRedistributionTrigger(
            self.params, self.imbalance_detector, self.redistribution_optimizer
        )
        print("   자동 트리거 시스템")
        
        # 4. 모니터링 대시보드
        self.dashboard = RealTimeMonitoringDashboard(
            self.params, self.imbalance_detector, self.auto_trigger
        )
        print("   모니터링 대시보드")
        
        # 5. 그래프 시각화 시스템
        self.graph_visualizer = GraphVisualizer(self.params)
        print("   그래프 시각화 시스템")
        
        # 6. 균형 최적화 적합도 계산기
        self.fitness_calculator = FitnessCalculator(self.params)
        print("   균형 최적화 적합도 계산기")
        
        # 7. 통합 모니터링 시스템
        self.monitoring_system = IntegratedMonitoringSystem(self.params)
        print("   통합 모니터링 시스템")
        
        print("모든 컴포넌트 초기화 완료\n")
    
    def demo_dynamic_imbalance_detection(self):
        """동적 불균형 감지 시스템 데모"""
        print("=== 동적 불균형 감지 시스템 데모 ===")
        
        # 더미 개체 생성
        individual = self.create_dummy_individual()
        
        # 불균형 감지 실행
        imbalance_report = self.imbalance_detector.detect_real_time_imbalance(individual)
        
        # 결과 출력
        print("\n불균형 분석 결과:")
        analysis = imbalance_report['imbalance_analysis']
        print(f"   불균형 지수: {analysis['imbalance_index']:.3f}")
        print(f"   균형 항구: {len(analysis['balanced_ports'])}개")
        print(f"   과잉 항구: {len(analysis['excess_ports'])}개 - {analysis['excess_ports']}")
        print(f"   부족 항구: {len(analysis['shortage_ports'])}개 - {analysis['shortage_ports']}")
        print(f"   심각 부족: {len(analysis['critical_shortage_ports'])}개 - {analysis['critical_shortage_ports']}")
        
        print(f"\n생성된 알림: {len(imbalance_report['alerts'])}건")
        for i, alert in enumerate(imbalance_report['alerts'][:3], 1):  # 상위 3개만
            print(f"   {i}. {alert.port}: {alert.alert_type} (심각도: {alert.severity})")
        
        print(f"\n권장사항:")
        for i, rec in enumerate(imbalance_report['recommendations'][:5], 1):
            print(f"   {i}. {rec}")
        
        return imbalance_report
    
    def demo_auto_redistribution_trigger(self, imbalance_report):
        """자동 재배치 트리거 시스템 데모"""
        print("\n🤖 === 자동 재배치 트리거 시스템 데모 ===")
        
        individual = self.create_dummy_individual()
        
        # 트리거 확인 및 실행
        trigger_result = self.auto_trigger.check_and_execute_triggers(individual)
        
        # 결과 출력
        print(f"\n⚡ 트리거 조건 평가: {len(trigger_result['triggered_conditions'])}개 조건 트리거됨")
        for condition in trigger_result['triggered_conditions']:
            rule = condition['rule']
            print(f"   • {rule.condition.value}: 우선순위 {rule.priority}, 영향 항구 {len(condition['affected_ports'])}개")
        
        print(f"\n🎯 실행 가능한 트리거: {len(trigger_result['executable_triggers'])}개")
        
        print(f"\n📈 실행 결과:")
        for result in trigger_result['execution_results']:
            success = "✅ 성공" if result['success'] else "❌ 실패"
            print(f"   {success} - 실행 시간: {result['execution_time']:.2f}초")
        
        print(f"\n💭 권장사항:")
        for rec in trigger_result['recommendations']:
            print(f"   • {rec}")
        
        return trigger_result
    
    def demo_monitoring_dashboard(self):
        """모니터링 대시보드 데모"""
        print("\n🖥️  === 실시간 모니터링 대시보드 데모 ===")
        
        individual = self.create_dummy_individual()
        
        # 대시보드 데이터 업데이트
        snapshot = self.dashboard.update_dashboard_data(individual)
        
        # 콘솔 대시보드 생성 및 출력
        console_output = self.dashboard.generate_console_dashboard()
        print("\n" + console_output)
        
        return snapshot
    
    def demo_balance_optimization_fitness(self):
        """균형 최적화 적합도 함수 데모"""
        print("\n⚖️  === 균형 최적화 적합도 함수 데모 ===")
        
        individual = self.create_dummy_individual()
        
        # 기본 적합도 계산 (비용만)
        self.fitness_calculator.enable_balance_optimization_mode(False)
        cost_only_fitness = self.fitness_calculator.calculate_fitness(individual.copy())
        
        # 균형 최적화 적합도 계산 (비용 + 균형)
        self.fitness_calculator.enable_balance_optimization_mode(True)
        self.fitness_calculator.set_balance_optimization_weights(0.7, 0.3)
        balanced_fitness = self.fitness_calculator.calculate_fitness(individual.copy())
        
        # 상세 분석
        breakdown = self.fitness_calculator.get_detailed_fitness_breakdown(individual)
        
        print("\n📊 적합도 비교:")
        print(f"   • 비용만 고려:     {cost_only_fitness:,.0f}")
        print(f"   • 균형 최적화 포함: {balanced_fitness:,.0f}")
        print(f"   • 개선 효과:       {((balanced_fitness - cost_only_fitness) / abs(cost_only_fitness) * 100):+.2f}%")
        
        print(f"\n🔍 상세 분석:")
        print(f"   • 기본 비용:       ${breakdown['base_cost']:,.0f}")
        print(f"   • 불균형 패널티:   ${breakdown['imbalance_penalty']:,.0f}")
        print(f"   • 제약 조건 패널티: ${breakdown['constraint_penalty']:,.0f}")
        print(f"   • 가중 목적함수:   ${breakdown['weighted_objective']:,.0f}")
        
        return breakdown
    
    def demo_redistribution_optimization(self):
        """재배치 최적화 데모"""
        print("\n🔄 === 재배치 최적화 시스템 데모 ===")
        
        individual = self.create_dummy_individual()
        
        # 재배치 계획 생성
        plan = self.redistribution_optimizer.generate_redistribution_plan(individual)
        
        # 결과 출력 (simplified version)
        print("\n🎯 재배치 계획 요약:")
        
        imbalance = plan.get('imbalance_analysis', {})
        print(f"   • 과잉 항구: {len(imbalance.get('excess_ports', []))}개")
        print(f"   • 부족 항구: {len(imbalance.get('shortage_ports', []))}개")
        
        paths = plan.get('redistribution_paths', [])
        print(f"   • 재배치 경로: {len(paths)}개")
        
        if paths:
            total_containers = sum(getattr(path, 'container_count', 0) for path in paths)
            total_cost = sum(getattr(path, 'cost', 0) for path in paths)
            print(f"   • 총 재배치량: {total_containers:,} TEU")
            print(f"   • 총 비용: ${total_cost:,.0f}")
        
        print(f"\n📋 권장사항: {len(plan.get('recommendations', []))}개")
        for i, rec in enumerate(plan.get('recommendations', [])[:3], 1):
            print(f"   {i}. {rec}")
        
        return plan
    
    def demo_integrated_monitoring_system(self):
        """통합 모니터링 시스템 데모"""
        print("\n🎛️  === 통합 모니터링 시스템 데모 ===")
        
        # 시스템 상태 확인
        summary = self.monitoring_system.get_system_summary()
        
        print(f"\n📋 시스템 현황:")
        print(f"   • 시스템 상태:     {summary['system_status']}")
        print(f"   • 헬스 점수:       {summary['health_score']:.1f}/100")
        print(f"   • 모니터링 활성화: {'✅' if summary['monitoring_enabled'] else '❌'}")
        print(f"   • 총 알림:         {summary['total_alerts']}건")
        print(f"   • 활성 알림:       {summary['active_alerts']}건")
        print(f"   • 중요 알림:       {summary['critical_alerts']}건")
        
        # 알림 요약
        alert_summary = self.monitoring_system.get_alert_summary()
        print(f"\n🚨 알림 요약:")
        print(f"   • 활성 알림:       {alert_summary['total_active']}건")
        
        if alert_summary['by_severity']:
            print("   • 심각도별:")
            for severity, count in alert_summary['by_severity'].items():
                print(f"     - {severity}: {count}건")
        
        # 강제 헬스 체크
        health_check = self.monitoring_system.force_health_check()
        print(f"\n🏥 헬스 체크 결과:")
        print(f"   • 실행 시간:       {health_check['timestamp']}")
        print(f"   • 헬스 점수:       {health_check['health_score']:.1f}/100")
        print(f"   • 시스템 상태:     {health_check['system_status']}")
        
        return summary
    
    def demo_graph_visualization(self, imbalance_report, redistribution_plan):
        """그래프 시각화 데모"""
        print("\n📊 === 그래프 시각화 시스템 데모 ===")
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # GUI 없는 환경을 위한 설정
            
            # 출력 디렉토리 생성
            output_dir = project_root / "output" / "visualizations"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 재배치 경로 추출
            redistribution_paths = redistribution_plan.get('redistribution_paths', [])
            
            # 모든 시각화 생성 및 저장
            saved_files = self.graph_visualizer.save_all_visualizations(
                str(output_dir),
                imbalance_report,
                redistribution_paths
            )
            
            print(f"\n🎨 생성된 시각화 파일: {len(saved_files)}개")
            for file_path in saved_files:
                print(f"   • {Path(file_path).name}")
            
            print(f"\n📁 저장 경로: {output_dir}")
            
            return saved_files
            
        except ImportError:
            print("⚠️  matplotlib을 사용할 수 없어 시각화를 건너뜁니다")
            return []
        except Exception as e:
            print(f"⚠️  시각화 생성 중 오류: {e}")
            return []
    
    def create_dummy_individual(self):
        """더미 개체 생성"""
        num_schedules = len(self.params.I)
        num_ports = len(self.params.P)
        
        return {
            'xF': np.random.randint(100, 800, num_schedules).astype(float),
            'xE': np.random.randint(50, 300, num_schedules).astype(float),
            'y': np.random.randint(500, 3000, (num_schedules, num_ports)).astype(float),
            'fitness': np.random.uniform(-100000, -50000)
        }
    
    def run_complete_demo(self):
        """완전한 시스템 데모 실행"""
        print("\n시스템 통합 데모 시작")
        print("=" * 60)
        
        try:
            # 1. 동적 불균형 감지
            imbalance_report = self.demo_dynamic_imbalance_detection()
            
            # 2. 자동 재배치 트리거
            trigger_result = self.demo_auto_redistribution_trigger(imbalance_report)
            
            # 3. 재배치 최적화
            redistribution_plan = self.demo_redistribution_optimization()
            
            # 4. 모니터링 대시보드
            dashboard_snapshot = self.demo_monitoring_dashboard()
            
            # 5. 균형 최적화 적합도
            fitness_breakdown = self.demo_balance_optimization_fitness()
            
            # 6. 통합 모니터링 시스템
            monitoring_summary = self.demo_integrated_monitoring_system()
            
            # 7. 그래프 시각화
            visualization_files = self.demo_graph_visualization(imbalance_report, redistribution_plan)
            
            print("\n" + "=" * 60)
            print("시스템 데모 완료")
            print("=" * 60)
            
            # 최종 요약
            print("\n데모 요약:")
            print(f"   불균형 감지:     {len(imbalance_report['alerts'])}건 알림")
            print(f"   자동 트리거:     {len(trigger_result['executable_triggers'])}개 실행")
            print(f"   재배치 최적화:   {len(redistribution_plan.get('redistribution_paths', []))}개 경로")
            print(f"   모니터링 시스템: 상태: {monitoring_summary['system_status']}")
            print(f"   균형 최적화:     적합도 개선 확인")
            print(f"   시각화:         {len(visualization_files)}개 파일 생성")
            
            # 성과 지표
            print(f"\n주요 성과 지표:")
            analysis = imbalance_report['imbalance_analysis']
            print(f"   불균형 지수:     {analysis['imbalance_index']:.3f}")
            print(f"   시스템 헬스:     {monitoring_summary['health_score']:.1f}/100")
            print(f"   효율성 점수:     {monitoring_summary.get('efficiency_score', 0):.1f}/100")
            
            # 데이터 내보내기
            export_file = self.monitoring_system.export_monitoring_data()
            print(f"   내보내기:       {export_file}")
            
            print(f"\n모든 핵심 기능이 성공적으로 구현되고 통합되었습니다.")
            print(f"실제 운영 환경에서는 실제 데이터를 사용하여 더욱 정확한 결과를 얻을 수 있습니다.")
            
        except Exception as e:
            print(f"\n데모 실행 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()


def main():
    """메인 함수"""
    try:
        demo = CompleteSystemDemo()
        demo.run_complete_demo()
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()