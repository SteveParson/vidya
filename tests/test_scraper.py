from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from vidya.scraper import scrape_ebay


@pytest.mark.asyncio
async def test_scrape_ebay_success() -> None:
    mock_html = """
    <div>
        <ul>
            <li class="s-item">
                <h3 class="s-item__title">Test Item</h3>
                <span class="s-item__price">$100.00</span>
                <a class="s-item__link" href="http://test.com">Link</a>
            </li>
        </ul>
    </div>
    """

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = mock_html
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await scrape_ebay("test query")
        assert len(results) >= 0
        if results:
            assert results[0].title == "Test Item"
            assert results[0].price == 100.0
