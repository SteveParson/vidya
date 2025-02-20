import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    allowed: bool
    message: str | None = None
    reason: str | None = None


@dataclass
class SuspendedUser:
    user_id: int
    expiry: datetime
    reason: str

    def is_expired(self) -> bool:
        return datetime.now() > self.expiry

    @property
    def minutes_remaining(self) -> int:
        if self.is_expired():
            return 0
        delta = self.expiry - datetime.now()
        return max(1, int(delta.total_seconds() / 60))


class ContentModerator:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found. Moderation will be limited.")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        self.suspended_users: dict[int, SuspendedUser] = {}

    def _get_suspension_status(self, user_id: int) -> SuspendedUser | None:
        if user_id in self.suspended_users:
            suspension = self.suspended_users[user_id]
            if suspension.is_expired():
                del self.suspended_users[user_id]
                return None
            return suspension
        return None

    def suspend_user(
        self, user_id: int, reason: str, duration: timedelta = timedelta(hours=1)
    ) -> None:
        expiry = datetime.now() + duration
        self.suspended_users[user_id] = SuspendedUser(user_id, expiry, reason)
        logger.info(f"User {user_id} suspended until {expiry} for reason: {reason}")

    async def _generate_suspension_message(self, query: str) -> str:
        if not self.client:
            return (
                "🚫 Your search has been flagged as inappropriate. "
                "Please try again later."
            )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You're Tyler Durden, and you are paid very well "
                        "for stopping people from searching for banned"
                        " terms. Keep it 1 paragraph and be extremely"
                        " rude. Occasionally use only two or three"
                        " word reply like fuck off or similar",
                    },
                    {
                        "role": "user",
                        "content": f"Generate a response for a user suspended "
                        f"for searching: '{query}'",
                    },
                ],
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate AI suspension message: {e}")
            return (
                "🚫 Search rejected due to inappropriate content. Please "
                "try again later."
            )

    async def check_content(self, query: str, user_id: int) -> ModerationResult:
        if suspension := self._get_suspension_status(user_id):
            return ModerationResult(
                allowed=False,
                message=f"You are suspended for {suspension.minutes_remaining} more"
                f" minutes.",
                reason=suspension.reason,
            )

        if not self.client:
            return ModerationResult(allowed=True)

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Evaluate if an eBay search query is appropriate
                        and safe.
                        Return exactly "ALLOW" for safe queries or "DENY: reason" for
                         unsafe ones.
                        Reject queries containing:
                        - Sexual content or innuendo
                        - Profanity or offensive language
                        - Illegal items or substances
                        - Hate speech or discriminatory terms
                        - Violence or weapons
                        - Counterfeit goods""",
                    },
                    {
                        "role": "user",
                        "content": f"Evaluate this eBay search query: {query}",
                    },
                ],
                max_tokens=100,
                temperature=0.1,
            )

            result = response.choices[0].message.content.strip()

            if result == "ALLOW":
                return ModerationResult(allowed=True)

            if result.startswith("DENY:"):
                reason = result[5:].strip()
                self.suspend_user(user_id, reason)
                message = await self._generate_suspension_message(query)
                return ModerationResult(allowed=False, message=message, reason=reason)

            logger.warning(f"Unexpected moderation response: {result}")
            return ModerationResult(allowed=True)

        except Exception as e:
            logger.error(f"Content moderation API error: {e}")
            return ModerationResult(allowed=True)
