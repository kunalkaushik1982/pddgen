from __future__ import annotations

from worker.bootstrap import get_db_session


class SqlAlchemyWorkerUnitOfWork:
    def __init__(self, session_factory=get_db_session) -> None:
        self._session_factory = session_factory
        self.session = None

    def __enter__(self) -> "SqlAlchemyWorkerUnitOfWork":
        self.session = self._session_factory()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        assert self.session is not None
        self.session.close()
        return False
