"""
결과 시각화 클래스
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, List, Any
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