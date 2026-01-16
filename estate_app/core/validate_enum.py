from enum import Enum
from typing import Type, TypeVar

E = TypeVar("E", bound=Enum)

def validate_enum(
    value: str | Enum,
    enum_cls: Type[E],
    *,
    field: str,
) -> E:
    if isinstance(value, enum_cls):
        return value

    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            pass

        try:
            return enum_cls[value]
        except KeyError:
            pass

    allowed = ", ".join(e.value for e in enum_cls)
    raise ValueError(
        f"Invalid {field}: {value}. Allowed values: {allowed}"
    )
