import logging
import re
import time
import httpx
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

CACHE_TTL = 86400  # 24 hours in seconds

INDIAMART_SEARCH_URL = "https://dir.indiamart.com/search.mp"

# Common chemical name mappings for better search results
CHEMICAL_ALIASES = {
    "hcl": "hydrochloric acid",
    "h2so4": "sulfuric acid",
    "naoh": "sodium hydroxide caustic soda",
    "nacl": "sodium chloride",
    "hno3": "nitric acid",
    "h3po4": "phosphoric acid",
    "nh3": "ammonia",
    "cacl2": "calcium chloride",
    "na2co3": "soda ash sodium carbonate",
    "koh": "potassium hydroxide",
    "ch3cooh": "acetic acid",
    "h2o2": "hydrogen peroxide",
    "caso4": "calcium sulfate gypsum",
    "mgso4": "magnesium sulfate",
    "znso4": "zinc sulfate",
    "feso4": "ferrous sulfate",
    "cuso4": "copper sulfate",
    "kmno4": "potassium permanganate",
}

# User-Agent to avoid blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class PriceHTMLParser(HTMLParser):
    """Parse IndiaMART search results for price information."""

    def __init__(self):
        super().__init__()
        self.prices = []
        self.units = []
        self.in_price = False
        self.in_unit = False
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")

        # IndiaMART price spans
        if "prc" in class_name or "price" in class_name.lower():
            self.in_price = True
            self.current_text = ""
        if "unt" in class_name or "unit" in class_name.lower():
            self.in_unit = True
            self.current_text = ""

    def handle_data(self, data):
        if self.in_price:
            self.current_text += data
        if self.in_unit:
            self.current_text += data

    def handle_endtag(self, tag):
        if self.in_price:
            self.in_price = False
            text = self.current_text.strip()
            # Extract numbers from price text
            numbers = re.findall(r'[\d,]+(?:\.\d+)?', text.replace(',', ''))
            for num in numbers:
                try:
                    price = float(num.replace(',', ''))
                    if 0.1 < price < 1_000_000:  # Reasonable price range
                        self.prices.append(price)
                except ValueError:
                    pass
        if self.in_unit:
            self.in_unit = False
            text = self.current_text.strip().lower()
            if any(u in text for u in ["kg", "kilogram", "litre", "liter", "ton", "mt", "piece"]):
                self.units.append(text)


def _extract_prices_from_html(html: str) -> dict:
    """Extract price data from raw HTML using regex patterns."""
    prices = []
    units = set()

    # Pattern 1: Rs/INR followed by number
    price_patterns = [
        r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)',
        r'([\d,]+(?:\.\d+)?)\s*(?:/\s*(?:Kg|KG|Kilogram|Litre|Liter|MT|Ton|Piece))',
        r'price["\s:]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)',
    ]

    for pattern in price_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            try:
                price = float(match.replace(',', ''))
                if 0.5 < price < 500_000:  # Reasonable per-unit range
                    prices.append(price)
            except ValueError:
                pass

    # Extract units
    unit_matches = re.findall(
        r'/\s*(Kg|KG|Kilogram|Litre|Liter|MT|Ton|Metric Ton|Piece|Bag|Drum)',
        html, re.IGNORECASE
    )
    for u in unit_matches:
        units.add(u.upper())

    return {"prices": prices, "units": list(units)}


class MarketPricingService:
    """Fetches and caches Indian chemical market prices from IndiaMART."""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def _get_search_term(self, chemical_name: str) -> str:
        """Get the best search term for a chemical."""
        name_lower = chemical_name.lower().strip()
        # Check aliases
        for code, full_name in CHEMICAL_ALIASES.items():
            if code == name_lower or name_lower in full_name:
                return full_name
        return chemical_name

    def _is_cached(self, key: str) -> bool:
        """Check if a cached result is still valid."""
        if key not in self._cache:
            return False
        return (time.time() - self._cache[key]["timestamp"]) < CACHE_TTL

    async def get_price(self, chemical_name: str) -> dict:
        """Get market price for a chemical from IndiaMART."""
        cache_key = chemical_name.lower().strip()

        # Return cached result if valid
        if self._is_cached(cache_key):
            return self._cache[cache_key]["data"]

        search_term = self._get_search_term(chemical_name)
        result = {
            "chemical": chemical_name,
            "price_min": None,
            "price_max": None,
            "unit": "KG",
            "source": "IndiaMART",
            "available": False,
        }

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(
                    INDIAMART_SEARCH_URL,
                    params={"ss": search_term, "prdsrc": "1"},
                    headers=HEADERS,
                )

                if response.status_code == 200:
                    html = response.text
                    extracted = _extract_prices_from_html(html)
                    prices = extracted["prices"]
                    units = extracted["units"]

                    if prices:
                        # Remove outliers (prices more than 3x median)
                        prices.sort()
                        median = prices[len(prices) // 2]
                        filtered = [p for p in prices if p < median * 3]
                        if filtered:
                            result["price_min"] = round(min(filtered), 2)
                            result["price_max"] = round(max(filtered), 2)
                            result["available"] = True
                            if units:
                                result["unit"] = units[0]

                    # Also try the HTML parser as backup
                    if not result["available"]:
                        parser = PriceHTMLParser()
                        try:
                            parser.feed(html)
                        except Exception:
                            pass
                        if parser.prices:
                            result["price_min"] = round(min(parser.prices), 2)
                            result["price_max"] = round(max(parser.prices), 2)
                            result["available"] = True

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching price for {chemical_name}")
        except Exception as e:
            logger.warning(f"Failed to fetch market price for {chemical_name}: {e}")

        # Cache the result (even failures, to avoid hammering)
        self._cache[cache_key] = {
            "data": result,
            "timestamp": time.time(),
        }

        return result

    async def get_bulk_prices(self, chemicals: list[str]) -> list[dict]:
        """Get prices for multiple chemicals."""
        results = []
        for chem in chemicals[:10]:  # Limit to 10 to avoid rate limiting
            result = await self.get_price(chem)
            results.append(result)
        return results

    def clear_cache(self):
        """Clear all cached prices."""
        self._cache.clear()


# Singleton
market_pricing_service = MarketPricingService()
