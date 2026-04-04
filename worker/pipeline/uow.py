from __future__ import annotations

from sqlalchemy.orm import Session

from worker.bootstrap import get_db_session


class SqlAlchemyWorkerUnitOfWork:
    def __init__(self, session_factory=get_db_session) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        assert self._session is not None
        return self._session

    def __enter__(self) -> SqlAlchemyWorkerUnitOfWork:
        self._session = self._session_factory()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        assert self._session is not None
        self._session.close()
        self._session = None
        return False
