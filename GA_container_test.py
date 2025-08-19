# GA_container_test.py - 빠른 테스트용 버전
import sys
sys.path.append('.')
from GA_container import OceanShippingGA

def run_quick_test():
    """빠른 테스트 실행"""
    file_paths = {
        'schedule': './스해물_스케줄 data.xlsx',
        'delayed': './스해물_딜레이 스케줄 data.xlsx', 
        'vessel': './스해물_선박 data.xlsx',
        'port': './스해물_항구 위치 data.xlsx'
    }
    
    # GA 인스턴스 생성
    ga = OceanShippingGA(file_paths)
    
    # 테스트용으로 작은 population 설정
    ga.population_size = 50
    ga.max_generations = 100
    ga.num_elite = 10
    ga.convergence_patience = 20
    
    print(f"\n🧪 빠른 테스트 설정:")
    print(f"   Population: {ga.population_size}")
    print(f"   Generations: {ga.max_generations}")
    print(f"   Elite: {ga.num_elite}")
    
    # 최적화 실행
    best_solution, fitness_history = ga.run()
    
    # 결과 출력
    ga.print_solution(best_solution)
    
    return best_solution, fitness_history

if __name__ == "__main__":
    best_solution, fitness_history = run_quick_test()