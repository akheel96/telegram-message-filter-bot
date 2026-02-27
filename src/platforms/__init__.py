# Platform handlers package
from .base import BasePlatform, ProductInfo
from .amazon import AmazonHandler
from .flipkart import FlipkartHandler
from .myntra import MyntraHandler

__all__ = [
    'BasePlatform',
    'ProductInfo',
    'AmazonHandler',
    'FlipkartHandler',
    'MyntraHandler',
]
