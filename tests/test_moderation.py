from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vidya.moderation import ContentModerator, SuspendedUser


@pytest.mark.asyncio
async def test_check_content_suspended_user() -> None:
    moderator = ContentModerator()
    user_id = 12345
    reason = "test suspension"

    moderator.suspend_user(user_id, reason)

    result = await moderator.check_content("test query", user_id)
    assert result.allowed is False
    assert "suspended" in result.message.lower()
    assert result.reason == reason


@pytest.mark.asyncio
async def test_check_content_allowed() -> None:
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content="ALLOW"))]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        moderator = ContentModerator()
        moderator.client = mock_client

        result = await moderator.check_content("safe query", 12345)

        assert result.allowed is True
        assert result.message is None
        assert result.reason is None

        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o"
        assert len(call_args.kwargs["messages"]) == 2


@pytest.mark.asyncio
async def test_check_content_denied() -> None:
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="DENY: inappropriate content"))
    ]

    mock_suspension_completion = MagicMock()
    mock_suspension_completion.choices = [
        MagicMock(message=MagicMock(content="You've been suspended!"))
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[mock_completion, mock_suspension_completion]
    )

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        moderator = ContentModerator()
        moderator.client = mock_client

        result = await moderator.check_content("bad query", 12345)

        assert result.allowed is False
        assert result.message is not None
        assert result.reason == "inappropriate content"

        assert mock_client.chat.completions.create.call_count == 2


def test_suspended_user_expiry() -> None:
    now = datetime.now()
    user = SuspendedUser(
        user_id=12345, expiry=now + timedelta(minutes=10), reason="test"
    )

    assert not user.is_expired()
    assert 5 <= user.minutes_remaining <= 10

    expired_user = SuspendedUser(
        user_id=12345, expiry=now - timedelta(minutes=10), reason="test"
    )

    assert expired_user.is_expired()
    assert expired_user.minutes_remaining == 0
