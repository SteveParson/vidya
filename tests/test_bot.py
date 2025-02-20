import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from discord import File

from vidya.bot import ebay_command, handle_moderation
from vidya.moderation import ModerationResult
from vidya.scraper import EbayListing


@pytest.mark.asyncio
async def test_handle_moderation_allowed(mock_ctx: MagicMock) -> None:
    with patch(
        "vidya.bot.moderator.check_content", return_value=ModerationResult(allowed=True)
    ):
        result = await handle_moderation(mock_ctx, "test query")
        assert result is True
        mock_ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_moderation_blocked(mock_ctx: MagicMock) -> None:
    mock_result = ModerationResult(
        allowed=False, message="Test blocked message", reason="Test reason"
    )
    with patch("vidya.bot.moderator.check_content", return_value=mock_result):
        result = await handle_moderation(mock_ctx, "bad query")
        assert result is False
        mock_ctx.send.assert_called_once_with("Test blocked message")


@pytest.mark.asyncio
async def test_ebay_command_success(mock_ctx: MagicMock) -> None:
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

    mock_buffer = io.BytesIO(b"fake image data")

    with (
        patch("vidya.bot.handle_moderation", return_value=True),
        patch("vidya.bot.scrape_ebay", AsyncMock(return_value=mock_listings)),
        patch("vidya.bot.calculate_statistics", AsyncMock(return_value=mock_stats)),
        patch(
            "vidya.bot.create_price_visualization", MagicMock(return_value=mock_buffer)
        ),
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
        assert "$150.00" in content
        assert "$300.00" in content
        assert isinstance(final_call_args[1]["file"], MagicMock)


@pytest.mark.asyncio
async def test_ebay_command_empty_query(mock_ctx: MagicMock) -> None:
    await ebay_command(mock_ctx, query="   ")
    mock_ctx.send.assert_called_once_with("❌ Please provide a search query.")


@pytest.mark.asyncio
async def test_ebay_command_no_results(mock_ctx: MagicMock) -> None:
    mock_message = MagicMock()
    mock_message.delete = AsyncMock()
    mock_ctx.send = AsyncMock(return_value=mock_message)

    with (
        patch("vidya.bot.handle_moderation", return_value=True),
        patch("vidya.bot.scrape_ebay", AsyncMock(return_value=[])),
    ):
        await ebay_command(mock_ctx, query="test")

        mock_message.delete.assert_called_once()
        mock_ctx.send.assert_any_call("📭 No listings found for your query.")
