import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExchangeRate:
    rate: float
    timestamp: datetime

    def is_expired(self, max_age: timedelta = timedelta(hours=1)) -> bool:
        return datetime.now() - self.timestamp > max_age


class ExchangeRateError(Exception):
    pass


class ExchangeRateService:
    def __init__(self) -> None:
        self._cache: dict[str, ExchangeRate] = {}
        self._lock = asyncio.Lock()

    async def get_rate(
        self, from_currency: str = "USD", to_currency: str = "CAD"
    ) -> float:
        cache_key = f"{from_currency}-{to_currency}"

        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached and not cached.is_expired():
                return cached.rate

            try:
                rate = await self._fetch_rate(from_currency, to_currency)
                self._cache[cache_key] = ExchangeRate(
                    rate=rate, timestamp=datetime.now()
                )
                return rate
            except Exception as e:
                logger.error(f"Failed to fetch exchange rate: {e}")
                if cached:
                    logger.warning("Using expired exchange rate from cache")
                    return cached.rate
                return 1.4

    async def _fetch_rate(self, from_currency: str, to_currency: str) -> float:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data["rates"].get(to_currency, 1.4)
            except Exception as e:
                raise ExchangeRateError(f"Failed to fetch exchange rate: {e!s}") from e


@dataclass
class PriceStatistics:
    min_price: float
    q1_price: float
    median_price: float
    q3_price: float
    max_price: float
    total_listings: int


async def calculate_statistics(
    prices: list[float], exchange_service: ExchangeRateService
) -> PriceStatistics:
    if not prices:
        raise ValueError("No prices provided for statistics calculation")

    exchange_rate = await exchange_service.get_rate()
    df = pd.Series(prices) * exchange_rate

    return PriceStatistics(
        min_price=round(df.min(), 2),
        q1_price=round(df.quantile(0.25), 2),
        median_price=round(df.median(), 2),
        q3_price=round(df.quantile(0.75), 2),
        max_price=round(df.max(), 2),
        total_listings=len(df),
    )
