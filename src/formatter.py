"""
Message Formatter module for Telegram Loot Filter Bot.
Formats product information into clean, readable Telegram messages.
"""

import logging
from typing import Optional

from .platforms.base import ProductInfo

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Formats product information for Telegram messages."""
    
    def __init__(self, discount_highlight_threshold: int = 50):
        """
        Initialize the formatter.
        
        Args:
            discount_highlight_threshold: Highlight discounts above this percentage
        """
        self.discount_highlight_threshold = discount_highlight_threshold
    
    def format_product_message(self, product: ProductInfo, original_message: str = "") -> str:
        """
        Format product information into a Telegram-friendly message.
        
        Args:
            product: ProductInfo object with product details
            original_message: Original message text (optional, for context)
            
        Returns:
            Formatted message string
        """
        if not product or not product.is_valid():
            return original_message
        
        lines = []
        
        # Header with deal indicator
        discount = product.discount_percent or product.calculate_discount()
        if discount and discount >= self.discount_highlight_threshold:
            lines.append(f"🔥🔥🔥 MEGA LOOT DEAL - {discount}% OFF! 🔥🔥🔥")
        elif discount and discount >= 30:
            lines.append(f"🔥 LOOT DEAL FOUND - {discount}% OFF!")
        else:
            lines.append("🛒 DEAL FOUND")
        
        lines.append("")  # Empty line
        
        # Summary line
        summary_parts = []
        if product.brand:
            summary_parts.append(product.brand)
        if product.title:
            # Truncate long titles for summary
            title_short = product.title[:50] + "..." if len(product.title) > 50 else product.title
            summary_parts.append(title_short)
        if summary_parts:
            lines.append(f"📦 {' | '.join(summary_parts)}")
            lines.append("")
        
        # Product details
        if product.title:
            lines.append(f"📌 Product: {product.title}")
        
        if product.brand:
            lines.append(f"🏷️ Brand: {product.brand}")
        
        # Pricing section
        if product.current_price:
            price_str = self._format_price(product.current_price)
            if discount and discount > 0:
                lines.append(f"💰 Price: {price_str} 🎉")
            else:
                lines.append(f"💰 Price: {price_str}")
        
        if product.original_price and product.original_price != product.current_price:
            mrp_str = self._format_price(product.original_price)
            lines.append(f"💸 MRP: ~~{mrp_str}~~")
        
        if discount and discount > 0:
            discount_emoji = "🚀" if discount >= self.discount_highlight_threshold else "✂️"
            lines.append(f"{discount_emoji} Discount: {discount}% OFF")
        
        # Rating
        if product.rating:
            stars = self._get_star_rating(product.rating)
            rating_str = f"⭐ Rating: {stars} ({product.rating}/5)"
            if product.rating_count:
                rating_str += f" • {self._format_number(product.rating_count)} reviews"
            lines.append(rating_str)
        
        # Category
        if product.category:
            lines.append(f"📂 Category: {product.category}")
        
        # Platform
        if product.platform:
            platform_emoji = self._get_platform_emoji(product.platform)
            lines.append(f"{platform_emoji} Platform: {product.platform}")
        
        # Stock status
        if product.in_stock is not None:
            if product.in_stock:
                lines.append("✅ In Stock")
            else:
                lines.append("❌ Out of Stock")
        
        # URL
        lines.append("")
        if product.url:
            lines.append(f"🔗 Link: {product.url}")
        
        # Footer
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        
        return "\n".join(lines)
    
    def format_simple_message(self, product: ProductInfo) -> str:
        """
        Format a simpler, more compact message.
        
        Args:
            product: ProductInfo object
            
        Returns:
            Compact formatted message
        """
        if not product or not product.is_valid():
            return ""
        
        parts = []
        
        # Header
        discount = product.discount_percent or product.calculate_discount()
        if discount and discount >= self.discount_highlight_threshold:
            parts.append(f"🔥 {discount}% OFF LOOT!")
        else:
            parts.append("🛒 Deal Found")
        
        # Title
        if product.title:
            title = product.title[:80] + "..." if len(product.title) > 80 else product.title
            parts.append(title)
        
        # Price info
        price_info = []
        if product.current_price:
            price_info.append(f"₹{int(product.current_price)}")
        if product.original_price and product.original_price != product.current_price:
            price_info.append(f"MRP ₹{int(product.original_price)}")
        if price_info:
            parts.append(" | ".join(price_info))
        
        # Platform and link
        if product.platform:
            parts.append(f"Platform: {product.platform}")
        if product.url:
            parts.append(product.url)
        
        return "\n".join(parts)
    
    def _format_price(self, price: float) -> str:
        """Format price with currency symbol."""
        if price >= 100000:
            return f"₹{price/100000:.2f}L"
        elif price >= 1000:
            return f"₹{int(price):,}"
        else:
            return f"₹{price:.2f}"
    
    def _format_number(self, num: int) -> str:
        """Format large numbers with K/L suffix."""
        if num >= 100000:
            return f"{num/100000:.1f}L"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)
    
    def _get_star_rating(self, rating: float) -> str:
        """Convert numeric rating to star display."""
        full_stars = int(rating)
        half_star = rating - full_stars >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)
        
        stars = "★" * full_stars
        if half_star:
            stars += "½"
        stars += "☆" * empty_stars
        
        return stars
    
    def _get_platform_emoji(self, platform: str) -> str:
        """Get emoji for platform."""
        platform_emojis = {
            'Amazon': '📦',
            'Flipkart': '🛍️',
            'Myntra': '👗',
        }
        return platform_emojis.get(platform, '🏪')
    
    def should_format_product(self, product: Optional[ProductInfo], skip_out_of_stock: bool = True) -> bool:
        """
        Check if product info is worth formatting.
        
        Args:
            product: ProductInfo to check
            skip_out_of_stock: If True, skip products that are confirmed out of stock
            
        Returns:
            True if product has enough info to format and passes stock check
        """
        if not product:
            return False
        
        # At minimum need title or price
        if not (product.title or product.current_price):
            return False
        
        # Requirement 2: Skip out-of-stock products
        # Forward if: in_stock is True OR in_stock is None (unknown)
        # Skip if: in_stock is explicitly False
        if skip_out_of_stock and product.in_stock is False:
            logger.info(f"⏭️ Skipping out-of-stock product: {product.title}")
            return False
        
        return True
