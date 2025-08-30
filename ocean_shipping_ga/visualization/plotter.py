"""
결과 시각화 클래스
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
import os
from models.parameters import GAParameters
from algorithms.fitness import FitnessCalculator


class ResultPlotter:
    """
    GA 결과 시각화 클래스
    """
    
    def __init__(self, params: GAParameters):
        """
        Parameters:
        -----------
        params : GAParameters
            GA 및 LP 모델 파라미터
        """
        self.params = params
        self.fitness_calculator = FitnessCalculator(params)
        
    def print_solution_summary(self, best_individual: Dict[str, Any]):
        """최적해 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 최적 솔루션 요약")
        print("=" * 60)
        
        total_cost = self.fitness_calculator.calculate_total_cost(best_individual)
        penalty = self.fitness_calculator.calculate_penalties(best_individual)
        
        print(f"\n💰 비용 분석:")
        print(f"  • 총 비용: ${total_cost:,.2f}")
        print(f"  • 패널티: {penalty:.2f}")
        print(f"  • 적합도: {best_individual['fitness']:.2f}")
        
        print(f"\n📦 컨테이너 할당:")
        print(f"  • Full 컨테이너: {np.sum(best_individual['xF']):,.0f} TEU")
        print(f"  • Empty 컨테이너: {np.sum(best_individual['xE']):,.0f} TEU")
        print(f"  • 평균 재고(전체 컨테이너 풀): {np.mean(best_individual['y']):,.0f} TEU")
        
        # 루트별 수요 충족률
        print(f"\n🚢 주요 루트 상태 (상위 5개):")
        for r in self.params.R[:5]:
            if r in self.params.D_ab:
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = sum(
                    best_individual['xF'][self.params.I.index(i)]
                    for i in route_schedules if i in self.params.I
                )
                
                demand = self.params.D_ab[r]
                fulfillment = (total_full / demand * 100) if demand > 0 else 0
                
                vessel = self.params.V_r.get(r, "Unknown")[:20]
                print(f"  루트 {r:3d}: {total_full:5.0f}/{demand:5.0f} TEU "
                      f"({fulfillment:5.1f}%) - {vessel}")
    
    def visualize_results(self, best_individual: Dict[str, Any], fitness_history: List[float]):
        """결과 시각화"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 적합도 진화
        axes[0, 0].plot(fitness_history, 'b-', linewidth=2)
        axes[0, 0].set_xlabel('Generation')
        axes[0, 0].set_ylabel('Fitness')
        axes[0, 0].set_title('Fitness Evolution Process')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 컨테이너 분포 (상위 20개 스케줄)
        n_display = min(20, self.params.num_schedules)
        x_pos = np.arange(n_display)
        
        axes[0, 1].bar(x_pos, best_individual['xF'][:n_display], 
                      alpha=0.7, label='Full', color='blue')
        axes[0, 1].bar(x_pos, best_individual['xE'][:n_display], 
                      alpha=0.7, label='Empty', color='orange', 
                      bottom=best_individual['xF'][:n_display])
        axes[0, 1].set_xlabel('Schedule Number')
        axes[0, 1].set_ylabel('Container Count (TEU)')
        axes[0, 1].set_title('Container Allocation by Schedule (Top 20)')
        axes[0, 1].legend()
        axes[0, 1].set_xticks(x_pos[::2])
        axes[0, 1].set_xticklabels(self.params.I[:n_display:2])
        
        # 3. 항구별 평균 재고
        avg_inventory = np.mean(best_individual['y'], axis=0)
        ports = self.params.P[:min(10, len(self.params.P))]
        
        axes[1, 0].barh(range(len(ports)), avg_inventory[:len(ports)], color='green', alpha=0.7)
        axes[1, 0].set_yticks(range(len(ports)))
        axes[1, 0].set_yticklabels(ports)
        axes[1, 0].set_xlabel('Average Inventory (TEU)')
        axes[1, 0].set_title('Average Empty Container Inventory by Port')
        axes[1, 0].grid(True, alpha=0.3, axis='x')
        
        # 4. 비용 구성
        total_cost = self.fitness_calculator.calculate_total_cost(best_individual)
        
        transport_cost = sum(
            (self.params.CSHIP + self.params.CBAF) * best_individual['xF'][i]
            for i in range(self.params.num_schedules)
        )
        delay_cost = sum(
            self.params.CETA * self.params.DELAY_i.get(self.params.I[i], 0) * best_individual['xF'][i]
            for i in range(self.params.num_schedules)
        )
        empty_cost = self.params.CEMPTY_SHIP * np.sum(best_individual['xE'])
        
        costs = [transport_cost, delay_cost, empty_cost]
        labels = ['Transport Cost', 'Delay Penalty', 'Empty Transport']
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        
        _, texts, autotexts = axes[1, 1].pie(
            costs, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        
        axes[1, 1].set_title(f'Cost Breakdown (Total: ${total_cost:,.0f})')        
        # 폰트 크기 조정
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color('white')
            autotext.set_weight('bold')
        
        plt.tight_layout()
        plt.show()
        
        return fig
    
    def generate_markdown_report(self, best_individual: Dict[str, Any], fitness_history: List[float], 
                                version: str = "Unknown", execution_time: float = 0.0) -> str:
        """상세한 마크다운 보고서 생성"""
        
        # 기본 계산
        total_cost = self.fitness_calculator.calculate_total_cost(best_individual)
        penalty = self.fitness_calculator.calculate_penalties(best_individual)
        
        # 비용 세부 계산
        transport_cost = sum(
            (self.params.CSHIP + self.params.CBAF) * best_individual['xF'][i]
            for i in range(self.params.num_schedules)
        )
        delay_cost = sum(
            self.params.CETA * self.params.DELAY_i.get(self.params.I[i], 0) * best_individual['xF'][i]
            for i in range(self.params.num_schedules)
        )
        empty_cost = self.params.CEMPTY_SHIP * np.sum(best_individual['xE'])
        
        # 마크다운 보고서 생성
        report = []
        report.append("# Ocean Shipping GA Optimization Report")
        report.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # 실행 정보
        report.append("## 🚀 Execution Summary")
        report.append(f"- **Version**: {version}")
        report.append(f"- **Execution Time**: {execution_time:.2f} seconds")
        report.append(f"- **Generations**: {len(fitness_history)}")
        report.append(f"- **Population Size**: {self.params.population_size}")
        report.append(f"- **Crossover Rate**: {self.params.p_crossover}")
        report.append(f"- **Mutation Rate**: {self.params.p_mutation}\n")
        
        # 최적해 요약
        report.append("## 📊 Optimal Solution Summary")
        report.append(f"- **Final Fitness**: {best_individual['fitness']:,.2f}")
        report.append(f"- **Total Cost**: ${total_cost:,.2f}")
        report.append(f"- **Total Penalty**: {penalty:,.2f}")
        report.append(f"- **Cost per TEU**: ${total_cost / (np.sum(best_individual['xF']) + np.sum(best_individual['xE'])):,.2f}\n")
        
        # 컨테이너 할당
        report.append("## 📦 Container Allocation Overview")
        total_full = np.sum(best_individual['xF'])
        total_empty = np.sum(best_individual['xE'])
        total_containers = total_full + total_empty
        
        report.append(f"- **Total Full Containers**: {total_full:,.0f} TEU ({total_full/total_containers*100:.1f}%)")
        report.append(f"- **Total Empty Containers**: {total_empty:,.0f} TEU ({total_empty/total_containers*100:.1f}%)")
        report.append(f"- **Total Containers**: {total_containers:,.0f} TEU")
        report.append(f"- **Average Inventory**: {np.mean(best_individual['y']):,.0f} TEU\n")
        
        # 비용 분석
        report.append("## 💰 Cost Breakdown Analysis")
        total_operational_cost = transport_cost + delay_cost + empty_cost
        
        report.append("| Cost Category | Amount ($) | Percentage |")
        report.append("|---------------|------------|------------|")
        report.append(f"| Transport Cost | {transport_cost:,.2f} | {transport_cost/total_operational_cost*100:.1f}% |")
        report.append(f"| Delay Penalty | {delay_cost:,.2f} | {delay_cost/total_operational_cost*100:.1f}% |")
        report.append(f"| Empty Transport | {empty_cost:,.2f} | {empty_cost/total_operational_cost*100:.1f}% |")
        report.append(f"| **Total Operational** | **{total_operational_cost:,.2f}** | **100.0%** |\n")
        
        # 루트별 상세 분석
        report.append("## 🚢 Route-by-Route Analysis")
        report.append("### Top Performing Routes")
        report.append("| Route | Vessel | Full TEU | Demand | Fulfillment | Efficiency |")
        report.append("|-------|--------|----------|--------|-------------|------------|")
        
        route_analysis = []
        for r in self.params.R:
            if r in self.params.D_ab:
                route_schedules = self.params.schedule_data[
                    self.params.schedule_data['루트번호'] == r
                ]['스케줄 번호'].unique()
                
                total_full = sum(
                    best_individual['xF'][self.params.I.index(i)]
                    for i in route_schedules if i in self.params.I
                )
                
                demand = self.params.D_ab[r]
                fulfillment = (total_full / demand * 100) if demand > 0 else 0
                efficiency = total_full / (total_full + sum(
                    best_individual['xE'][self.params.I.index(i)]
                    for i in route_schedules if i in self.params.I
                )) if total_full > 0 else 0
                
                vessel = self.params.V_r.get(r, "Unknown")
                route_analysis.append((r, vessel, total_full, demand, fulfillment, efficiency))
        
        # 상위 20개 루트만 표시
        route_analysis.sort(key=lambda x: x[4], reverse=True)  # fulfillment로 정렬
        for r, vessel, full, demand, fulfillment, efficiency in route_analysis[:20]:
            report.append(f"| {r} | {vessel[:15]} | {full:,.0f} | {demand:,.0f} | {fulfillment:.1f}% | {efficiency:.1f}% |")
        
        report.append("")
        
        # 제약조건 분석
        report.append("## ⚠️ Constraint Analysis")
        
        # 용량 제약 위반 체크
        capacity_violations = 0
        for i in range(self.params.num_schedules):
            schedule_id = self.params.I[i]
            # Get route number for this schedule
            schedule_info = self.params.schedule_data[self.params.schedule_data['스케줄 번호'] == schedule_id]
            if not schedule_info.empty:
                route_num = schedule_info['루트번호'].iloc[0]
                capacity = self.params.CAP_v_r.get(route_num, float('inf'))
                total_allocated = best_individual['xF'][i] + best_individual['xE'][i]
                if total_allocated > capacity:
                    capacity_violations += 1
        
        # 재고 제약 위반 체크  
        inventory_violations = 0
        for j in range(len(self.params.P)):
            for i in range(self.params.num_schedules):
                if best_individual['y'][i][j] < 0:
                    inventory_violations += 1
        
        report.append(f"- **Capacity Constraint Violations**: {capacity_violations}")
        report.append(f"- **Inventory Constraint Violations**: {inventory_violations}")
        report.append(f"- **Solution Feasibility**: {'✅ Feasible' if capacity_violations == 0 and inventory_violations == 0 else '❌ Infeasible'}\n")
        
        # 진화 통계
        report.append("## 📈 Evolution Statistics")
        if len(fitness_history) > 1:
            improvement = fitness_history[-1] - fitness_history[0]
            max_fitness = max(fitness_history)
            
            report.append(f"- **Initial Fitness**: {fitness_history[0]:,.2f}")
            report.append(f"- **Final Fitness**: {fitness_history[-1]:,.2f}")
            report.append(f"- **Total Improvement**: {improvement:,.2f}")
            report.append(f"- **Best Fitness Achieved**: {max_fitness:,.2f}")
            report.append(f"- **Convergence Rate**: {(improvement/abs(fitness_history[0])*100) if fitness_history[0] != 0 else 0:.2f}%\n")
        
        # 항구별 재고 분석
        report.append("## 🏢 Port Inventory Analysis")
        report.append("| Port | Avg Inventory | Max Inventory | Min Inventory |")
        report.append("|------|---------------|---------------|---------------|")
        
        for j, port in enumerate(self.params.P[:10]):  # 상위 10개 항구만
            avg_inv = np.mean(best_individual['y'][:, j])
            max_inv = np.max(best_individual['y'][:, j])
            min_inv = np.min(best_individual['y'][:, j])
            report.append(f"| {port} | {avg_inv:,.0f} | {max_inv:,.0f} | {min_inv:,.0f} |")
        
        report.append("")
        
        # 권장사항
        report.append("## 💡 Recommendations")
        
        if capacity_violations > 0:
            report.append(f"- **Capacity Issues**: {capacity_violations} schedules exceed capacity. Consider fleet expansion or route optimization.")
        
        if delay_cost > transport_cost * 0.1:
            report.append("- **Delay Management**: Delay costs are significant. Consider schedule optimization or buffer time.")
        
        if empty_cost > total_operational_cost * 0.2:
            report.append("- **Empty Container Efficiency**: Empty transport costs are high. Consider repositioning strategies.")
        
        empty_ratio = total_empty / total_containers
        if empty_ratio > 0.3:
            report.append(f"- **Container Utilization**: Empty container ratio is {empty_ratio*100:.1f}%. Focus on demand-supply balancing.")
        
        report.append("")
        
        # 메타데이터
        report.append("---")
        report.append("*Report generated by Ocean Shipping GA Optimizer*")
        report.append(f"*Data files processed: {len([f for f in ['schedule', 'delay_schedule', 'ship', 'port'] if hasattr(self.params, f + '_data')])} files*")
        
        return "\n".join(report)
    
    def save_markdown_report(self, best_individual: Dict[str, Any], fitness_history: List[float],
                           version: str = "Unknown", execution_time: float = 0.0, 
                           output_dir: str = "results") -> str:
        """마크다운 보고서를 파일로 저장"""
        
        # 결과 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ocean_shipping_optimization_report_{version}_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)
        
        # 보고서 생성 및 저장
        report_content = self.generate_markdown_report(best_individual, fitness_history, version, execution_time)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n📄 상세 보고서가 저장되었습니다: {filepath}")
        return filepath