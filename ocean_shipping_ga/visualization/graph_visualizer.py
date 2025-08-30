"""
그래프 기반 시각화 시스템
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import seaborn as sns

from models.dynamic_imbalance_detector import DynamicImbalanceDetector, ImbalanceAlert
from models.redistribution_optimizer import ContainerRedistributionOptimizer
from config import get_constant


class GraphVisualizer:
    """
    네트워크 그래프 기반 시각화 시스템
    """
    
    def __init__(self, params):
        self.params = params
        
        # 시각화 설정 (설정 파일에서 로드)
        self.figure_size = (16, 12)
        self.node_size_scale = get_constant('visualization.graph.node_size_scale', 1000)
        self.edge_width_scale = get_constant('visualization.graph.edge_width_scale', 5)
        
        # 색상 스키마
        self.colors = {
            'critical_shortage': '#FF3333',
            'shortage': '#FF9933',
            'balanced': '#33AA33',
            'excess': '#3399FF',
            'critical_excess': '#9933FF',
            'redistribution_path': '#FF6600',
            'background': '#F8F9FA',
            'grid': '#E9ECEF'
        }
        
        # 레이아웃 설정
        self.layout_algorithms = {
            'spring': nx.spring_layout,
            'circular': nx.circular_layout,
            'kamada_kawai': nx.kamada_kawai_layout,
            'shell': nx.shell_layout
        }
        
    def create_port_network_graph(self, imbalance_data: Dict[str, Any], 
                                redistribution_paths: List = None,
                                layout: str = 'spring') -> plt.Figure:
        """항구 네트워크 그래프 생성"""
        
        # 네트워크 그래프 생성
        G = nx.Graph()
        
        # 노드 추가 (항구)
        current_levels = imbalance_data.get('current_levels', {})
        imbalance_analysis = imbalance_data.get('imbalance_analysis', {})
        
        for port, level in current_levels.items():
            G.add_node(port, level=level)
        
        # 재배치 경로 엣지 추가
        if redistribution_paths:
            for path in redistribution_paths:
                if hasattr(path, 'from_port') and hasattr(path, 'to_port'):
                    G.add_edge(path.from_port, path.to_port, 
                             weight=path.container_count,
                             cost=path.cost,
                             distance=path.distance)
        
        # 레이아웃 계산
        layout_func = self.layout_algorithms.get(layout, nx.spring_layout)
        if layout == 'spring':
            pos = layout_func(G, k=3, iterations=50)
        else:
            pos = layout_func(G)
        
        # 그림 생성
        fig, ax = plt.subplots(figsize=self.figure_size)
        ax.set_facecolor(self.colors['background'])
        
        # 노드 그리기
        self._draw_port_nodes(G, pos, ax, imbalance_analysis, current_levels)
        
        # 엣지 그리기 (재배치 경로)
        if redistribution_paths:
            self._draw_redistribution_edges(G, pos, ax)
        
        # 범례 추가
        self._add_network_legend(ax, len(redistribution_paths) > 0 if redistribution_paths else False)
        
        # 제목 및 설정
        timestamp = imbalance_data.get('timestamp', datetime.now())
        ax.set_title(f'Container Port Network Status\n{timestamp.strftime("%Y-%m-%d %H:%M:%S")}', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # 축 설정
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # 통계 정보 텍스트 박스
        self._add_statistics_box(ax, imbalance_analysis)
        
        plt.tight_layout()
        return fig
    
    def _draw_port_nodes(self, G: nx.Graph, pos: Dict, ax: plt.Axes, 
                        imbalance_analysis: Dict[str, Any], 
                        current_levels: Dict[str, float]):
        """항구 노드 그리기"""
        
        # 노드별 색상과 크기 결정
        node_colors = []
        node_sizes = []
        
        for node in G.nodes():
            level = current_levels.get(node, 0)
            
            # 크기 결정 (컨테이너 수량에 비례)
            size = max(300, min(3000, level * 2))
            node_sizes.append(size)
            
            # 색상 결정 (불균형 상태에 따라)
            if node in imbalance_analysis.get('critical_shortage_ports', []):
                color = self.colors['critical_shortage']
            elif node in imbalance_analysis.get('shortage_ports', []):
                color = self.colors['shortage']
            elif node in imbalance_analysis.get('excess_ports', []):
                excess_threshold = imbalance_analysis.get('statistics', {}).get('excess_threshold', 0)
                critical_threshold = excess_threshold * 1.25
                if level >= critical_threshold:
                    color = self.colors['critical_excess']
                else:
                    color = self.colors['excess']
            else:
                color = self.colors['balanced']
            
            node_colors.append(color)
        
        # 노드 그리기
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes,
                              alpha=0.8, ax=ax, edgecolors='white', linewidths=2)
        
        # 노드 라벨 (항구명 + 컨테이너 수)
        labels = {}
        for node in G.nodes():
            level = current_levels.get(node, 0)
            labels[node] = f'{node}\n{int(level):,}'
        
        nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold',
                               font_color='white', ax=ax)
    
    def _draw_redistribution_edges(self, G: nx.Graph, pos: Dict, ax: plt.Axes):
        """재배치 경로 엣지 그리기"""
        
        # 엣지별 가중치와 색상
        edge_weights = []
        edge_colors = []
        
        for edge in G.edges(data=True):
            weight = edge[2].get('weight', 0)
            edge_weights.append(max(1, min(10, weight / 100)))  # 두께 조절
            edge_colors.append(self.colors['redistribution_path'])
        
        # 엣지 그리기
        nx.draw_networkx_edges(G, pos, width=edge_weights, edge_color=edge_colors,
                              alpha=0.7, ax=ax, style='solid', arrows=True,
                              arrowsize=20, arrowstyle='->')
        
        # 엣지 라벨 (컨테이너 수량)
        edge_labels = {}
        for edge in G.edges(data=True):
            weight = edge[2].get('weight', 0)
            cost = edge[2].get('cost', 0)
            edge_labels[(edge[0], edge[1])] = f'{int(weight)} TEU\n${cost:.0f}'
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=7,
                                   bbox=dict(boxstyle='round,pad=0.2', 
                                           facecolor='white', alpha=0.8),
                                   ax=ax)
    
    def _add_network_legend(self, ax: plt.Axes, has_redistribution: bool):
        """네트워크 그래프 범례 추가"""
        legend_elements = [
            plt.scatter([], [], s=200, c=self.colors['critical_shortage'], 
                       label='Critical Shortage', alpha=0.8),
            plt.scatter([], [], s=200, c=self.colors['shortage'], 
                       label='Shortage', alpha=0.8),
            plt.scatter([], [], s=200, c=self.colors['balanced'], 
                       label='Balanced', alpha=0.8),
            plt.scatter([], [], s=200, c=self.colors['excess'], 
                       label='Excess', alpha=0.8),
            plt.scatter([], [], s=200, c=self.colors['critical_excess'], 
                       label='Critical Excess', alpha=0.8)
        ]
        
        if has_redistribution:
            legend_elements.append(
                plt.Line2D([0], [0], color=self.colors['redistribution_path'], 
                          linewidth=3, label='Redistribution Path')
            )
        
        ax.legend(handles=legend_elements, loc='upper left', 
                 bbox_to_anchor=(0, 1), frameon=True, 
                 facecolor='white', edgecolor='gray')
    
    def _add_statistics_box(self, ax: plt.Axes, imbalance_analysis: Dict[str, Any]):
        """통계 정보 박스 추가"""
        stats = []
        stats.append(f"Imbalance Index: {imbalance_analysis.get('imbalance_index', 0):.3f}")
        stats.append(f"Balanced Ports: {len(imbalance_analysis.get('balanced_ports', []))}")
        stats.append(f"Excess Ports: {len(imbalance_analysis.get('excess_ports', []))}")  
        stats.append(f"Shortage Ports: {len(imbalance_analysis.get('shortage_ports', []) + imbalance_analysis.get('critical_shortage_ports', []))}")
        
        # 텍스트 박스
        textstr = '\n'.join(stats)
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
    
    def create_flow_diagram(self, redistribution_paths: List, 
                          port_levels: Dict[str, float]) -> plt.Figure:
        """컨테이너 흐름 다이어그램 생성"""
        
        if not redistribution_paths:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No Redistribution Paths Available', 
                   ha='center', va='center', fontsize=16)
            ax.set_title('Container Flow Diagram')
            return fig
        
        # 소스-타겟 쌍 추출
        sources = set()
        targets = set()
        flows = []
        
        for path in redistribution_paths:
            if hasattr(path, 'from_port') and hasattr(path, 'to_port'):
                sources.add(path.from_port)
                targets.add(path.to_port)
                flows.append((path.from_port, path.to_port, path.container_count))
        
        # Sankey 다이어그램 스타일 플롯
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # 노드 위치 계산
        source_positions = {port: (0, i) for i, port in enumerate(sorted(sources))}
        target_positions = {port: (2, i) for i, port in enumerate(sorted(targets))}
        
        all_positions = {**source_positions, **target_positions}
        
        # 플로우 그리기
        for from_port, to_port, amount in flows:
            from_pos = all_positions[from_port]
            to_pos = all_positions[to_port]
            
            # 화살표 그리기
            ax.annotate('', xy=to_pos, xytext=from_pos,
                       arrowprops=dict(arrowstyle='->', lw=amount/100,
                                     color=self.colors['redistribution_path'],
                                     alpha=0.7))
            
            # 중간점에 수량 표시
            mid_x = (from_pos[0] + to_pos[0]) / 2
            mid_y = (from_pos[1] + to_pos[1]) / 2
            ax.text(mid_x, mid_y, f'{int(amount)} TEU', 
                   ha='center', va='center', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # 노드 그리기 및 라벨링
        for port, pos in all_positions.items():
            level = port_levels.get(port, 0)
            color = self.colors['excess'] if pos[0] == 0 else self.colors['shortage']
            
            circle = plt.Circle(pos, 0.1, color=color, alpha=0.8, zorder=10)
            ax.add_patch(circle)
            
            # 포트명과 레벨 표시
            ax.text(pos[0], pos[1] - 0.2, f'{port}\n{int(level):,} TEU',
                   ha='center', va='top', fontweight='bold', fontsize=10)
        
        # 섹션 라벨
        ax.text(0, max(len(sources), len(targets)) + 0.5, 'Excess Ports',
               ha='center', va='bottom', fontsize=14, fontweight='bold',
               color=self.colors['excess'])
        ax.text(2, max(len(sources), len(targets)) + 0.5, 'Shortage Ports',
               ha='center', va='bottom', fontsize=14, fontweight='bold', 
               color=self.colors['shortage'])
        
        # 축 설정
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(-1, max(len(sources), len(targets)) + 1)
        ax.set_aspect('equal')
        ax.axis('off')
        
        ax.set_title('Container Redistribution Flow Diagram', fontsize=16, fontweight='bold', pad=20)
        
        # 총합 정보
        total_amount = sum(flow[2] for flow in flows)
        total_paths = len(flows)
        info_text = f'Total Redistribution: {total_amount:,} TEU\nTotal Paths: {total_paths}'
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=12,
               verticalalignment='top', 
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        return fig
    
    def create_heatmap_visualization(self, port_levels: Dict[str, float], 
                                   time_series_data: List[Dict] = None) -> plt.Figure:
        """히트맵 시각화 생성"""
        
        if time_series_data and len(time_series_data) > 1:
            # 시계열 히트맵
            return self._create_time_series_heatmap(time_series_data)
        else:
            # 단일 시점 히트맵
            return self._create_single_point_heatmap(port_levels)
    
    def _create_time_series_heatmap(self, time_series_data: List[Dict]) -> plt.Figure:
        """시계열 히트맵 생성"""
        
        # 데이터 준비
        timestamps = []
        all_ports = set()
        
        for data_point in time_series_data:
            timestamps.append(data_point.get('timestamp', datetime.now()))
            all_ports.update(data_point.get('port_levels', {}).keys())
        
        all_ports = sorted(list(all_ports))
        
        # 데이터 매트릭스 생성
        matrix = np.zeros((len(timestamps), len(all_ports)))
        
        for i, data_point in enumerate(time_series_data):
            port_levels = data_point.get('port_levels', {})
            for j, port in enumerate(all_ports):
                matrix[i, j] = port_levels.get(port, 0)
        
        # 히트맵 플롯
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 정규화를 위한 컬러맵
        im = ax.imshow(matrix.T, cmap='RdYlGn', aspect='auto', origin='lower')
        
        # 축 라벨
        ax.set_xticks(range(len(timestamps)))
        ax.set_xticklabels([t.strftime('%m/%d %H:%M') for t in timestamps], rotation=45)
        ax.set_yticks(range(len(all_ports)))
        ax.set_yticklabels(all_ports)
        
        # 컬러바
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('컨테이너 수량 (TEU)', rotation=270, labelpad=20)
        
        # 제목
        ax.set_title('항구별 컨테이너 수준 시계열 히트맵', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def _create_single_point_heatmap(self, port_levels: Dict[str, float]) -> plt.Figure:
        """단일 시점 히트맵 생성"""
        
        ports = list(port_levels.keys())
        levels = list(port_levels.values())
        
        # 격자 형태로 배치 (적당한 행렬 크기 계산)
        n_ports = len(ports)
        cols = int(np.ceil(np.sqrt(n_ports)))
        rows = int(np.ceil(n_ports / cols))
        
        # 히트맵 매트릭스 생성
        heatmap_matrix = np.zeros((rows, cols))
        port_matrix = [[''] * cols for _ in range(rows)]
        
        for i, (port, level) in enumerate(port_levels.items()):
            row = i // cols
            col = i % cols
            heatmap_matrix[row, col] = level
            port_matrix[row][col] = port
        
        # 플롯 생성
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 히트맵 그리기
        im = ax.imshow(heatmap_matrix, cmap='RdYlGn', aspect='equal')
        
        # 포트명과 값 표시
        for i in range(rows):
            for j in range(cols):
                if port_matrix[i][j]:  # 빈 셀이 아닌 경우
                    port = port_matrix[i][j]
                    level = heatmap_matrix[i, j]
                    
                    # 텍스트 색상 결정 (배경에 따라)
                    text_color = 'white' if level < np.mean(levels) else 'black'
                    
                    ax.text(j, i, f'{port}\n{int(level):,}', 
                           ha='center', va='center', 
                           color=text_color, fontweight='bold', fontsize=10)
        
        # 컬러바
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('컨테이너 수량 (TEU)', rotation=270, labelpad=20)
        
        # 축 설정
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title('항구별 컨테이너 재고 현황', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def create_comparative_analysis_chart(self, before_data: Dict[str, Any], 
                                        after_data: Dict[str, Any]) -> plt.Figure:
        """재배치 전후 비교 분석 차트"""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 불균형 지수 비교
        before_imbalance = before_data.get('imbalance_analysis', {}).get('imbalance_index', 0)
        after_imbalance = after_data.get('imbalance_analysis', {}).get('imbalance_index', 0)
        
        ax1.bar(['재배치 전', '재배치 후'], [before_imbalance, after_imbalance],
               color=[self.colors['shortage'], self.colors['balanced']])
        ax1.set_title('불균형 지수 변화', fontweight='bold')
        ax1.set_ylabel('불균형 지수')
        
        # 개선률 표시
        improvement = ((before_imbalance - after_imbalance) / before_imbalance * 100) if before_imbalance > 0 else 0
        ax1.text(0.5, max(before_imbalance, after_imbalance) * 0.8, 
                f'개선률: {improvement:.1f}%', ha='center', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
        
        # 2. 항구 상태 분포 비교
        before_counts = self._count_port_statuses(before_data.get('imbalance_analysis', {}))
        after_counts = self._count_port_statuses(after_data.get('imbalance_analysis', {}))
        
        categories = ['심각한 부족', '부족', '균형', '과잉', '심각한 과잉']
        x_pos = np.arange(len(categories))
        
        width = get_constant('visualization.charts.bar_width', 0.35)
        ax2.bar(x_pos - width/2, [before_counts.get(cat, 0) for cat in categories], 
               width, label='재배치 전', alpha=0.8)
        ax2.bar(x_pos + width/2, [before_counts.get(cat, 0) for cat in categories], 
               width, label='재배치 후', alpha=0.8)
        
        ax2.set_title('항구 상태 분포 변화', fontweight='bold')
        ax2.set_xlabel('항구 상태')
        ax2.set_ylabel('항구 수')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(categories, rotation=45, ha='right')
        ax2.legend()
        
        # 3. 상위 항구별 재고 변화
        self._plot_top_ports_comparison(ax3, before_data, after_data)
        
        # 4. 비용-효과 분석
        self._plot_cost_effectiveness(ax4, before_data, after_data)
        
        plt.suptitle('컨테이너 재배치 전후 비교 분석', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        return fig
    
    def _count_port_statuses(self, imbalance_analysis: Dict[str, Any]) -> Dict[str, int]:
        """항구 상태별 개수 계산"""
        return {
            '심각한 부족': len(imbalance_analysis.get('critical_shortage_ports', [])),
            '부족': len(imbalance_analysis.get('shortage_ports', [])),
            '균형': len(imbalance_analysis.get('balanced_ports', [])),
            '과잉': len(imbalance_analysis.get('excess_ports', [])),
            '심각한 과잉': 0  # 추가 구현 필요
        }
    
    def _plot_top_ports_comparison(self, ax: plt.Axes, before_data: Dict[str, Any], 
                                 after_data: Dict[str, Any]):
        """상위 항구별 비교 플롯"""
        before_levels = before_data.get('current_levels', {})
        after_levels = after_data.get('current_levels', {})
        
        # 공통 항구들 중 상위 10개
        common_ports = set(before_levels.keys()) & set(after_levels.keys())
        sorted_ports = sorted(common_ports, 
                            key=lambda x: before_levels.get(x, 0) + after_levels.get(x, 0),
                            reverse=True)[:10]
        
        if sorted_ports:
            x_pos = np.arange(len(sorted_ports))
            width = get_constant('visualization.charts.bar_width', 0.35)
            
            before_values = [before_levels.get(port, 0) for port in sorted_ports]
            after_values = [after_levels.get(port, 0) for port in sorted_ports]
            
            ax.bar(x_pos - width/2, before_values, width, 
                  label='재배치 전', alpha=0.8, color=self.colors['shortage'])
            ax.bar(x_pos + width/2, after_values, width,
                  label='재배치 후', alpha=0.8, color=self.colors['balanced'])
            
            ax.set_title('주요 항구별 재고 변화', fontweight='bold')
            ax.set_xlabel('항구')
            ax.set_ylabel('컨테이너 수량 (TEU)')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(sorted_ports, rotation=45, ha='right')
            ax.legend()
    
    def _plot_cost_effectiveness(self, ax: plt.Axes, before_data: Dict[str, Any], 
                               after_data: Dict[str, Any]):
        """비용-효과 분석 플롯"""
        # 가상의 비용-효과 데이터 (실제 구현에서는 실제 계산)
        metrics = ['재배치 비용', '운영 절약', '효율성 개선', '순 효과']
        values = [100, 150, 200, 250]  # 예시 값
        
        colors = [self.colors['shortage'], self.colors['excess'], 
                 self.colors['balanced'], self.colors['critical_excess']]
        
        bars = ax.bar(metrics, values, color=colors, alpha=0.8)
        
        # 값 표시
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 5,
                   f'${value}K', ha='center', va='bottom', fontweight='bold')
        
        ax.set_title('비용-효과 분석', fontweight='bold')
        ax.set_ylabel('금액 ($1000)')
        
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def save_all_visualizations(self, output_dir: str, imbalance_data: Dict[str, Any],
                              redistribution_paths: List = None,
                              time_series_data: List[Dict] = None,
                              comparison_data: Tuple[Dict, Dict] = None) -> List[str]:
        """모든 시각화 저장"""
        
        saved_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. 네트워크 그래프
        try:
            network_fig = self.create_port_network_graph(imbalance_data, redistribution_paths)
            network_path = f"{output_dir}/network_graph_{timestamp}.png"
            network_fig.savefig(network_path, dpi=300, bbox_inches='tight')
            saved_files.append(network_path)
            plt.close(network_fig)
        except Exception as e:
            print(f"네트워크 그래프 저장 실패: {e}")
        
        # 2. 플로우 다이어그램
        if redistribution_paths:
            try:
                current_levels = imbalance_data.get('current_levels', {})
                flow_fig = self.create_flow_diagram(redistribution_paths, current_levels)
                flow_path = f"{output_dir}/flow_diagram_{timestamp}.png"
                flow_fig.savefig(flow_path, dpi=300, bbox_inches='tight')
                saved_files.append(flow_path)
                plt.close(flow_fig)
            except Exception as e:
                print(f"플로우 다이어그램 저장 실패: {e}")
        
        # 3. 히트맵
        try:
            current_levels = imbalance_data.get('current_levels', {})
            heatmap_fig = self.create_heatmap_visualization(current_levels, time_series_data)
            heatmap_path = f"{output_dir}/heatmap_{timestamp}.png"
            heatmap_fig.savefig(heatmap_path, dpi=300, bbox_inches='tight')
            saved_files.append(heatmap_path)
            plt.close(heatmap_fig)
        except Exception as e:
            print(f"히트맵 저장 실패: {e}")
        
        # 4. 비교 분석 (데이터가 있는 경우)
        if comparison_data:
            try:
                comparison_fig = self.create_comparative_analysis_chart(*comparison_data)
                comparison_path = f"{output_dir}/comparison_analysis_{timestamp}.png"
                comparison_fig.savefig(comparison_path, dpi=300, bbox_inches='tight')
                saved_files.append(comparison_path)
                plt.close(comparison_fig)
            except Exception as e:
                print(f"비교 분석 차트 저장 실패: {e}")
        
        return saved_files