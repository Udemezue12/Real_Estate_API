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
    def bank_normalize(self, name: str) -> list[str]:
        name = re.sub(r"[^\w\s]", "", name.lower())
        return name.split()

    async def bank_name_match(self, user:User, bank_name: str) -> bool:
        parts = filter(None, [
            user.first_name,
            user.middle_name,
            user.last_name,
        ])

        user_name = " ".join(parts)

        user_parts = set(self.bank_normalize(user_name))
        bank_parts = set(self.bank_normalize(bank_name))

        matches = user_parts & bank_parts

        return len(matches) >= 2
