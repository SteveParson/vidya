from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from vidya.utils import ExchangeRateService, calculate_statistics


@pytest.mark.asyncio
async def test_get_exchange_rate_success() -> None:
    mock_rate = 1.35

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"CAD": mock_rate}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get.return_value = mock_response

    service = ExchangeRateService()

    with patch("httpx.AsyncClient", return_value=mock_client):
        rate = await service.get_rate()
        assert rate == mock_rate


@pytest.mark.asyncio
async def test_get_exchange_rate_cache() -> None:
    mock_rate = 1.35

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"rates": {"CAD": mock_rate}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get.return_value = mock_response

    service = ExchangeRateService()

    with patch("httpx.AsyncClient", return_value=mock_client):
        rate1 = await service.get_rate()
        rate2 = await service.get_rate()
        assert rate1 == rate2 == mock_rate
        assert mock_client.__aenter__.return_value.get.call_count == 1


@pytest.mark.asyncio
async def test_calculate_statistics() -> None:
    prices = [100, 200, 300, 400, 500]
    mock_rate = 1.5

    class MockExchangeService:
        async def get_rate(self, *args: object, **kwargs: object) -> float:
            return mock_rate

    stats = await calculate_statistics(prices, MockExchangeService())

    assert stats.min_price == round(100 * mock_rate, 2)
    assert stats.max_price == round(500 * mock_rate, 2)
    assert stats.total_listings == 5
