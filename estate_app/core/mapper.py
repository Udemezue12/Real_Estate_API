from typing import Iterable, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ORMMapper:
    @staticmethod
    def one(item, schema: Type[T]) -> T:
        return schema.model_validate(item)

    @staticmethod
    def many(items: Iterable, schema: Type[T]) -> list[T]:
        return [schema.model_validate(item) for item in items]
