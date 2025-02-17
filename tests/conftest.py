from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands


@pytest.fixture
def mock_ctx() -> object:
    ctx = MagicMock(spec=commands.Context)
    message = MagicMock()
    message.edit = AsyncMock()
    ctx.send = AsyncMock(return_value=message)
    ctx.typing = MagicMock()
    ctx.typing.return_value = AsyncMock(
        __aenter__=AsyncMock(),
        __aexit__=AsyncMock(),
    )
    return ctx


@pytest.fixture
def mock_message() -> MagicMock:
    return MagicMock(spec=discord.Message)
