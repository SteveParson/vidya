from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord import File

from vidya.bot import ebay_command
from vidya.scraper import EbayListing


@pytest.mark.asyncio
async def test_ebay_command_success(mock_ctx: object) -> None:
    mock_message = MagicMock()
    mock_message.edit = AsyncMock()
    mock_message.delete = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=mock_message)

    mock_listings = [
        EbayListing(title="Test Item 1", price=100.0, url="http://test1.com"),
        EbayListing(title="Test Item 2", price=200.0, url="http://test2.com"),
    ]

    mock_stats = MagicMock()
    mock_stats.min_price = 150.0
    mock_stats.q1_price = 150.0
    mock_stats.median_price = 225.0
    mock_stats.q3_price = 300.0
    mock_stats.max_price = 300.0
    mock_stats.total_listings = 2

    mock_buffer = BytesIO(b"fake image data")

    with (
        patch("vidya.bot.scrape_ebay", AsyncMock(return_value=mock_listings)),
        patch("vidya.bot.calculate_statistics", AsyncMock(return_value=mock_stats)),
        patch("vidya.bot.create_price_histogram", MagicMock(return_value=mock_buffer)),
        patch("discord.File", MagicMock(return_value=MagicMock(spec=File))),
    ):
        await ebay_command(mock_ctx, query="test")

        mock_ctx.typing.assert_called_once()

        mock_ctx.send.assert_any_call(
            "🔍 Fetching completed eBay listings for: test..."
        )

        mock_message.delete.assert_called_once()

        final_call_args = mock_ctx.send.call_args_list[-1]
        content = final_call_args[1]["content"]
        assert "test eBay Stats:" in content
        assert "Total Listings: 2" in content
        assert "$150.00 CAD" in content
        assert "$300.00 CAD" in content
        assert isinstance(final_call_args[1]["file"], MagicMock)


@pytest.mark.asyncio
async def test_ebay_command_with_special_characters(mock_ctx: object) -> None:
    mock_message = MagicMock()
    mock_message.edit = AsyncMock()
    mock_message.delete = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=mock_message)

    mock_listings = [EbayListing(title="Test Item", price=100.0, url="http://test.com")]
    mock_stats = MagicMock()
    mock_stats.min_price = 150.0
    mock_stats.q1_price = 150.0
    mock_stats.median_price = 150.0
    mock_stats.q3_price = 150.0
    mock_stats.max_price = 150.0
    mock_stats.total_listings = 1

    mock_buffer = BytesIO(b"fake image data")

    with (
        patch("vidya.bot.scrape_ebay", AsyncMock(return_value=mock_listings)),
        patch("vidya.bot.calculate_statistics", AsyncMock(return_value=mock_stats)),
        patch("vidya.bot.create_price_histogram", MagicMock(return_value=mock_buffer)),
        patch("discord.File", MagicMock(return_value=MagicMock(spec=File))),
    ):
        query = "test!@#$%^"
        await ebay_command(mock_ctx, query=query)

        mock_ctx.send.assert_any_call(
            f"🔍 Fetching completed eBay listings for: {query}..."
        )

        mock_message.delete.assert_called_once()

        final_call_args = mock_ctx.send.call_args_list[-1]
        content = final_call_args[1]["content"]
        assert query in content
        assert "$150.00 CAD" in content
        assert isinstance(final_call_args[1]["file"], MagicMock)
