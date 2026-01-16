import re
from models.models import User


class NameMatcher:
    SPLIT_RE = re.compile(r"[\s\-]+")

    @classmethod
    def normalize(cls, val: str | None) -> list[str]:
        if not val:
            return []

        return [
            part.strip().lower() for part in cls.SPLIT_RE.split(val) if part.strip()
        ]

    @classmethod
    async def names_match(
        cls,
        user: User,
        first_name: str,
        last_name: str,
    ) -> bool:
        db_tokens = set(cls.normalize(user.first_name) + cls.normalize(user.last_name))

        input_tokens = set(cls.normalize(first_name) + cls.normalize(last_name))

        if not db_tokens or not input_tokens:
            return False

        return db_tokens.issubset(input_tokens)
