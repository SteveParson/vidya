from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vidya.bot import ebay_command
from vidya.scraper import EbayListing


@pytest.mark.asyncio
async def test_ebay_command_success(mock_ctx: object) -> None:
    mock_message = MagicMock()
    mock_message.edit = AsyncMock()
    mock_ctx.send.return_value = mock_message

    mock_listings = [
        EbayListing(title="Test Item 1", price=100.0),
        EbayListing(title="Test Item 2", price=200.0),
    ]

    mock_scrape = AsyncMock(return_value=mock_listings)

    mock_stats = MagicMock()
    mock_stats.min_price = 150.0
    mock_stats.q1_price = 150.0
    mock_stats.median_price = 225.0
    mock_stats.q3_price = 300.0
    mock_stats.max_price = 300.0
    mock_stats.total_listings = 2

    mock_calculate = AsyncMock(return_value=mock_stats)

    with (
        patch("vidya.bot.scrape_ebay", mock_scrape),
        patch("vidya.bot.calculate_statistics", mock_calculate),
    ):
        await ebay_command(mock_ctx, query="test")

        mock_ctx.typing.assert_called_once()

        mock_message.edit.assert_called()
        edited_content = mock_message.edit.call_args[1]["content"]
        assert "test eBay Stats" in edited_content
        assert "Total Listings: 2" in edited_content
        assert "$150.00 CAD" in edited_content
        assert "$300.00 CAD" in edited_content


@pytest.mark.asyncio
async def test_ebay_command_no_results(mock_ctx: object) -> None:
    mock_message = MagicMock()
    mock_message.edit = AsyncMock()
    mock_ctx.send.return_value = mock_message

    mock_scrape = AsyncMock(return_value=[])

    with patch("vidya.bot.scrape_ebay", mock_scrape):
        await ebay_command(mock_ctx, query="test")

        mock_message.edit.assert_called()
        edited_content = mock_message.edit.call_args[1]["content"]
        assert "No listings found" in edited_content


@pytest.mark.asyncio
async def test_ebay_command_error(mock_ctx: object) -> None:
    mock_message = MagicMock()
    mock_message.edit = AsyncMock()
    mock_ctx.send.return_value = mock_message

    mock_scrape = AsyncMock(side_effect=Exception("Test error"))

    with patch("vidya.bot.scrape_ebay", mock_scrape):
        await ebay_command(mock_ctx, query="test")

        error_message = mock_ctx.send.call_args_list[-1][0][0]
        assert "error occurred" in error_message.lower()


@pytest.mark.asyncio
async def test_ebay_command_with_special_characters(mock_ctx: object) -> None:
    mock_message = MagicMock()
    mock_message.edit = AsyncMock()
    mock_ctx.send.return_value = mock_message

    mock_listings = [EbayListing(title="Test Item", price=100.0)]

    mock_scrape = AsyncMock(return_value=mock_listings)

    mock_stats = MagicMock()
    mock_stats.min_price = 150.0
    mock_stats.q1_price = 150.0
    mock_stats.median_price = 150.0
    mock_stats.q3_price = 150.0
    mock_stats.max_price = 150.0
    mock_stats.total_listings = 1

    mock_calculate = AsyncMock(return_value=mock_stats)

    with (
        patch("vidya.bot.scrape_ebay", mock_scrape),
        patch("vidya.bot.calculate_statistics", mock_calculate),
    ):
        query = "test!@#$%^"
        await ebay_command(mock_ctx, query=query)

        mock_message.edit.assert_called()
        edited_content = mock_message.edit.call_args[1]["content"]
        assert query in edited_content


@pytest.mark.asyncio
async def test_ebay_command_with_empty_query(mock_ctx: object) -> None:
    mock_ctx.command = MagicMock()
    mock_ctx.command.qualified_name = "ebay"

    try:
        await ebay_command(mock_ctx)
        pytest.fail("Should have raised MissingRequiredArgument")
    except TypeError as e:
        assert "missing 1 required keyword-only argument: 'query'" in str(e)
