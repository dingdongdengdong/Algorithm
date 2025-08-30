"""
Ocean Shipping GA Optimization Package

해상 운송 최적화를 위한 유전 알고리즘 패키지
"""

from .models.ga_optimizer import OceanShippingGA
from .utils.runner import run_ocean_shipping_ga

__version__ = "1.0.0"
__all__ = ["OceanShippingGA", "run_ocean_shipping_ga"]