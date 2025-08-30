#!/usr/bin/env python3
"""
학습 시스템
GA 성능 데이터를 학습하여 적응 전략을 개선
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
import pickle
from collections import deque

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class LearningSystem:
    """GA 성능 학습 및 개선 시스템"""
    
    def __init__(self, max_experiences: int = 1000,
                 learning_rate: float = 0.1):
        """
        Parameters:
        -----------
        max_experiences : int
            최대 경험 저장 수
        learning_rate : float
            학습률
        """
        self.max_experiences = max_experiences
        self.learning_rate = learning_rate
        
        # 경험 데이터 저장
        self.experiences = deque(maxlen=max_experiences)
        self.adaptation_patterns = {}
        self.performance_models = {}
        
        # 학습 상태
        self.learning_history = []
        self.model_accuracy = {}
        
        # 패턴 인식
        self.context_patterns = {
            'performance_decline': [],
            'system_overload': [],
            'environment_change': [],
            'successful_adaptations': []
        }
        
    def add_experience(self, experience_data: Dict):
        """새로운 경험 데이터 추가"""
        experience = {
            'timestamp': datetime.now(),
            'context': experience_data.get('context', {}),
            'actions': experience_data.get('actions', []),
            'performance_improvement': experience_data.get('performance_improvement', 0),
            'success': experience_data.get('success', False),
            'metadata': experience_data.get('metadata', {})
        }
        
        self.experiences.append(experience)
        
        # 패턴 업데이트
        self._update_patterns(experience)
        
        print(f"📚 Added new experience (total: {len(self.experiences)})")
    
    def _update_patterns(self, experience: Dict):
        """패턴 데이터 업데이트"""
        context = experience['context']
        success = experience['success']
        improvement = experience['performance_improvement']
        
        # 성공한 적응의 패턴 저장
        if success and improvement > 0:
            self.context_patterns['successful_adaptations'].append({
                'context_type': context.get('adaptation_type', 'unknown'),
                'reasons': context.get('reasons', []),
                'actions': [action.get('action', '') for action in experience['actions']],
                'improvement': improvement,
                'timestamp': experience['timestamp']
            })
        
        # 성능 하락 패턴
        if 'performance_decline' in context.get('reasons', []):
            self.context_patterns['performance_decline'].append({
                'severity': context.get('priority', 'unknown'),
                'actions_taken': len(experience['actions']),
                'success': success,
                'improvement': improvement
            })
        
        # 시스템 과부하 패턴
        if any('system' in reason for reason in context.get('reasons', [])):
            self.context_patterns['system_overload'].append({
                'context': context,
                'success': success,
                'improvement': improvement
            })
    
    def learn_adaptation_patterns(self) -> Dict:
        """적응 패턴 학습"""
        print("🧠 Learning adaptation patterns...")
        
        if len(self.experiences) < 10:
            return {'status': 'insufficient_data', 'experiences': len(self.experiences)}
        
        learning_results = {
            'timestamp': datetime.now(),
            'patterns_learned': {},
            'recommendations': [],
            'accuracy_scores': {}
        }
        
        try:
            # 성공 패턴 분석
            success_patterns = self._analyze_success_patterns()
            learning_results['patterns_learned']['success_patterns'] = success_patterns
            
            # 실패 패턴 분석
            failure_patterns = self._analyze_failure_patterns()
            learning_results['patterns_learned']['failure_patterns'] = failure_patterns
            
            # 컨텍스트별 최적 액션 학습
            optimal_actions = self._learn_optimal_actions()
            learning_results['patterns_learned']['optimal_actions'] = optimal_actions
            
            # 성능 예측 모델 훈련
            prediction_accuracy = self._train_performance_predictor()
            learning_results['accuracy_scores']['performance_prediction'] = prediction_accuracy
            
            # 추천사항 생성
            recommendations = self._generate_recommendations(success_patterns, failure_patterns)
            learning_results['recommendations'] = recommendations
            
            # 학습 이력 업데이트
            self.learning_history.append(learning_results)
            
            print(f"✅ Learning completed: {len(success_patterns)} success patterns, {len(failure_patterns)} failure patterns")
            
        except Exception as e:
            learning_results['error'] = str(e)
            print(f"❌ Learning failed: {e}")
        
        return learning_results
    
    def _analyze_success_patterns(self) -> List[Dict]:
        """성공 패턴 분석"""
        successful_experiences = [exp for exp in self.experiences if exp['success'] and exp['performance_improvement'] > 0]
        
        patterns = []
        
        # 적응 타입별 성공 패턴
        adaptation_types = {}
        for exp in successful_experiences:
            adapt_type = exp['context'].get('adaptation_type', 'unknown')
            if adapt_type not in adaptation_types:
                adaptation_types[adapt_type] = []
            adaptation_types[adapt_type].append(exp)
        
        for adapt_type, exps in adaptation_types.items():
            if len(exps) < 3:  # 최소 3개 이상의 경험
                continue
            
            # 공통 액션 패턴 찾기
            common_actions = self._find_common_actions([exp['actions'] for exp in exps])
            
            # 평균 성능 개선
            avg_improvement = np.mean([exp['performance_improvement'] for exp in exps])
            
            patterns.append({
                'adaptation_type': adapt_type,
                'success_count': len(exps),
                'common_actions': common_actions,
                'avg_improvement': avg_improvement,
                'success_rate': len(exps) / len([e for e in self.experiences if e['context'].get('adaptation_type') == adapt_type]),
                'confidence': min(1.0, len(exps) / 10)  # 10개 이상이면 신뢰도 1.0
            })
        
        # 성과가 좋은 순으로 정렬
        patterns.sort(key=lambda x: x['avg_improvement'], reverse=True)
        
        return patterns
    
    def _analyze_failure_patterns(self) -> List[Dict]:
        """실패 패턴 분석"""
        failed_experiences = [exp for exp in self.experiences if not exp['success'] or exp['performance_improvement'] <= 0]
        
        patterns = []
        
        # 실패 원인별 그룹화
        failure_reasons = {}
        for exp in failed_experiences:
            reasons = exp['context'].get('reasons', ['unknown'])
            for reason in reasons:
                if reason not in failure_reasons:
                    failure_reasons[reason] = []
                failure_reasons[reason].append(exp)
        
        for reason, exps in failure_reasons.items():
            if len(exps) < 2:  # 최소 2개 이상
                continue
            
            # 실패하는 액션 패턴
            failing_actions = self._find_common_actions([exp['actions'] for exp in exps])
            
            patterns.append({
                'failure_reason': reason,
                'failure_count': len(exps),
                'common_failing_actions': failing_actions,
                'avg_performance_impact': np.mean([exp['performance_improvement'] for exp in exps]),
                'confidence': min(1.0, len(exps) / 5)
            })
        
        return patterns
    
    def _find_common_actions(self, action_lists: List[List[Dict]]) -> List[str]:
        """공통 액션 패턴 찾기"""
        if not action_lists:
            return []
        
        # 모든 액션을 문자열로 변환
        action_strings = []
        for actions in action_lists:
            action_str_list = [action.get('action', '') for action in actions if action.get('action')]
            action_strings.append(action_str_list)
        
        # 빈도 계산
        action_counts = {}
        for actions in action_strings:
            for action in actions:
                action_counts[action] = action_counts.get(action, 0) + 1
        
        # 50% 이상 등장하는 액션들 반환
        min_frequency = len(action_lists) * 0.5
        common_actions = [action for action, count in action_counts.items() if count >= min_frequency]
        
        return common_actions
    
    def _learn_optimal_actions(self) -> Dict:
        """컨텍스트별 최적 액션 학습"""
        optimal_actions = {}
        
        # 컨텍스트 타입별로 그룹화
        context_groups = {}
        for exp in self.experiences:
            context_type = exp['context'].get('adaptation_type', 'unknown')
            if context_type not in context_groups:
                context_groups[context_type] = []
            context_groups[context_type].append(exp)
        
        for context_type, exps in context_groups.items():
            if len(exps) < 5:  # 최소 5개 경험
                continue
            
            # 액션별 성능 계산
            action_performance = {}
            for exp in exps:
                for action in exp['actions']:
                    action_name = action.get('action', '')
                    if not action_name:
                        continue
                    
                    if action_name not in action_performance:
                        action_performance[action_name] = []
                    
                    action_performance[action_name].append(exp['performance_improvement'])
            
            # 평균 성능이 가장 좋은 액션들 선택
            best_actions = []
            for action, performances in action_performance.items():
                if len(performances) >= 2:  # 최소 2번 이상 시도된 액션
                    avg_performance = np.mean(performances)
                    if avg_performance > 0:  # 양의 효과가 있는 액션
                        best_actions.append({
                            'action': action,
                            'avg_performance': avg_performance,
                            'frequency': len(performances),
                            'std_dev': np.std(performances)
                        })
            
            # 성능순 정렬
            best_actions.sort(key=lambda x: x['avg_performance'], reverse=True)
            optimal_actions[context_type] = best_actions[:3]  # 상위 3개
        
        return optimal_actions
    
    def _train_performance_predictor(self) -> float:
        """성능 예측 모델 훈련"""
        if len(self.experiences) < 20:
            return 0.0
        
        # 간단한 특징 추출
        features = []
        targets = []
        
        for exp in self.experiences:
            feature_vector = self._extract_features(exp)
            if feature_vector is not None:
                features.append(feature_vector)
                targets.append(exp['performance_improvement'])
        
        if len(features) < 10:
            return 0.0
        
        features = np.array(features)
        targets = np.array(targets)
        
        # 간단한 선형 회귀 (실제로는 더 복잡한 모델 사용 가능)
        try:
            from sklearn.linear_model import LinearRegression
            from sklearn.model_selection import cross_val_score
            
            model = LinearRegression()
            scores = cross_val_score(model, features, targets, cv=min(5, len(features)//2))
            accuracy = np.mean(scores)
            
            # 모델 저장
            model.fit(features, targets)
            self.performance_models['linear_predictor'] = model
            
            return max(0.0, accuracy)
            
        except ImportError:
            # sklearn이 없으면 단순한 평균 기반 예측
            return 0.5  # 기본 정확도
    
    def _extract_features(self, experience: Dict) -> Optional[np.ndarray]:
        """경험에서 특징 벡터 추출"""
        try:
            features = []
            
            # 컨텍스트 특징
            context = experience['context']
            
            # 적응 타입 원핫 인코딩
            adaptation_types = ['performance_improvement', 'system_optimization', 'environment_adaptation', 'emergency_response']
            adapt_type = context.get('adaptation_type', 'unknown')
            for atype in adaptation_types:
                features.append(1 if adapt_type == atype else 0)
            
            # 우선순위 인코딩
            priorities = {'low': 1, 'medium': 2, 'high': 3, 'urgent': 4}
            priority = priorities.get(context.get('priority', 'low'), 1)
            features.append(priority)
            
            # 신뢰도
            confidence = context.get('confidence', 0.0)
            features.append(confidence)
            
            # 이유 개수
            reasons_count = len(context.get('reasons', []))
            features.append(reasons_count)
            
            # 액션 개수
            actions_count = len(experience['actions'])
            features.append(actions_count)
            
            # 시간 특징 (하루 중 시간, 주중/주말 등)
            timestamp = experience['timestamp']
            features.append(timestamp.hour / 24.0)  # 정규화된 시간
            features.append(1 if timestamp.weekday() < 5 else 0)  # 주중 여부
            
            return np.array(features)
            
        except Exception as e:
            print(f"⚠️ Feature extraction error: {e}")
            return None
    
    def _generate_recommendations(self, success_patterns: List[Dict], failure_patterns: List[Dict]) -> List[Dict]:
        """학습 결과 기반 추천사항 생성"""
        recommendations = []
        
        # 성공 패턴 기반 추천
        for pattern in success_patterns[:3]:  # 상위 3개
            if pattern['confidence'] > 0.5:
                recommendations.append({
                    'type': 'promote_successful_pattern',
                    'description': f"Use {pattern['adaptation_type']} strategy more frequently",
                    'expected_improvement': pattern['avg_improvement'],
                    'confidence': pattern['confidence'],
                    'recommended_actions': pattern['common_actions']
                })
        
        # 실패 패턴 기반 회피 추천
        for pattern in failure_patterns:
            if pattern['confidence'] > 0.6:
                recommendations.append({
                    'type': 'avoid_failing_pattern',
                    'description': f"Avoid actions that typically fail for {pattern['failure_reason']}",
                    'risk_reduction': abs(pattern['avg_performance_impact']),
                    'confidence': pattern['confidence'],
                    'actions_to_avoid': pattern['common_failing_actions']
                })
        
        # 성능 임계값 기반 추천
        if len(self.experiences) > 0:
            recent_improvements = [exp['performance_improvement'] for exp in list(self.experiences)[-10:]]
            avg_recent = np.mean(recent_improvements)
            
            if avg_recent < 0:  # 최근 성능이 하락 추세
                recommendations.append({
                    'type': 'performance_recovery',
                    'description': 'Recent performance is declining, consider more aggressive adaptation',
                    'urgency': 'high',
                    'suggested_strategy': 'aggressive'
                })
        
        return recommendations
    
    def get_adaptation_recommendation(self) -> Dict:
        """현재 상황에 대한 적응 권장사항"""
        if len(self.experiences) < 5:
            return {'should_adapt': False, 'reason': 'insufficient_learning_data'}
        
        # 최근 성능 추세 분석
        recent_experiences = list(self.experiences)[-5:]
        recent_improvements = [exp['performance_improvement'] for exp in recent_experiences]
        recent_successes = [exp['success'] for exp in recent_experiences]
        
        avg_improvement = np.mean(recent_improvements)
        success_rate = np.mean(recent_successes)
        
        recommendation = {
            'should_adapt': False,
            'confidence': 0.0,
            'reason': '',
            'suggested_actions': [],
            'expected_improvement': 0.0
        }
        
        # 성능이 하락 중이면 적응 권장
        if avg_improvement < -50:  # 임계값
            recommendation['should_adapt'] = True
            recommendation['reason'] = 'performance_declining'
            recommendation['confidence'] = 0.8
            
            # 성공 패턴에서 권장 액션 추출
            if 'successful_adaptations' in self.context_patterns:
                successful_adaptations = self.context_patterns['successful_adaptations']
                if successful_adaptations:
                    # 가장 효과적이었던 적응의 액션들
                    best_adaptation = max(successful_adaptations, key=lambda x: x['improvement'])
                    recommendation['suggested_actions'] = best_adaptation['actions']
                    recommendation['expected_improvement'] = best_adaptation['improvement']
        
        # 성공률이 낮으면 다른 전략 시도 권장
        elif success_rate < 0.4:
            recommendation['should_adapt'] = True
            recommendation['reason'] = 'low_success_rate'
            recommendation['confidence'] = 0.6
        
        return recommendation
    
    def save_learning_state(self, filepath: str):
        """학습 상태 저장"""
        learning_state = {
            'experiences': list(self.experiences),
            'adaptation_patterns': self.adaptation_patterns,
            'performance_models': {},  # sklearn 모델은 별도 저장
            'learning_history': self.learning_history,
            'context_patterns': self.context_patterns,
            'model_accuracy': self.model_accuracy,
            'config': {
                'max_experiences': self.max_experiences,
                'learning_rate': self.learning_rate
            }
        }
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(learning_state, f)
            print(f"💾 Learning state saved to {filepath}")
            
        except Exception as e:
            print(f"❌ Failed to save learning state: {e}")
    
    def load_learning_state(self, filepath: str):
        """학습 상태 로드"""
        try:
            with open(filepath, 'rb') as f:
                learning_state = pickle.load(f)
            
            self.experiences = deque(learning_state['experiences'], maxlen=self.max_experiences)
            self.adaptation_patterns = learning_state['adaptation_patterns']
            self.learning_history = learning_state['learning_history']
            self.context_patterns = learning_state['context_patterns']
            self.model_accuracy = learning_state['model_accuracy']
            
            config = learning_state.get('config', {})
            self.max_experiences = config.get('max_experiences', self.max_experiences)
            self.learning_rate = config.get('learning_rate', self.learning_rate)
            
            print(f"📂 Learning state loaded from {filepath}")
            print(f"   - Experiences loaded: {len(self.experiences)}")
            print(f"   - Learning history: {len(self.learning_history)}")
            
        except Exception as e:
            print(f"❌ Failed to load learning state: {e}")
    
    def get_learning_stats(self) -> Dict:
        """학습 통계 정보"""
        if not self.experiences:
            return {'status': 'no_data'}
        
        experiences = list(self.experiences)
        
        return {
            'total_experiences': len(experiences),
            'successful_experiences': sum(1 for exp in experiences if exp['success']),
            'success_rate': np.mean([exp['success'] for exp in experiences]),
            'avg_performance_improvement': np.mean([exp['performance_improvement'] for exp in experiences]),
            'learning_sessions': len(self.learning_history),
            'pattern_counts': {
                key: len(patterns) for key, patterns in self.context_patterns.items()
            },
            'model_accuracy': self.model_accuracy,
            'data_timespan': {
                'oldest': min(exp['timestamp'] for exp in experiences),
                'newest': max(exp['timestamp'] for exp in experiences)
            } if experiences else None
        }