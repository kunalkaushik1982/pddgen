from __future__ import annotations

from typing import Protocol, TypeVar

RequestT = TypeVar("RequestT")
ResponseT = TypeVar("ResponseT")


class AISkill(Protocol[RequestT, ResponseT]):
    skill_id: str
    version: str

    def run(self, input: RequestT) -> ResponseT:
        ...
