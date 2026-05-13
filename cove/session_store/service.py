import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from cove.config import settings
from cove.session_store.models import Base, EventModel, SessionModel


class SessionStoreService:
    def __init__(self, db_url: str | None = None):
        self.engine = create_async_engine(db_url or settings.database_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._tables_created = False

    async def _ensure_tables(self):
        if not self._tables_created:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._tables_created = True

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def create_session(self, project_key: str, config: dict | None = None) -> dict:
        await self._ensure_tables()
        async with self.session_factory() as session:
            model = SessionModel(
                id=str(uuid.uuid4()),
                project_key=project_key,
                config=config or {},
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return {
                "session_id": model.id,
                "project_key": model.project_key,
                "status": model.status,
                "created_at": model.created_at.isoformat(),
            }

    def _is_valid_uuid(self, s: str) -> bool:
        try:
            uuid.UUID(s)
            return True
        except (ValueError, AttributeError):
            return False

    async def get_session(self, session_id: str) -> dict | None:
        await self._ensure_tables()
        if not self._is_valid_uuid(session_id):
            return None
        async with self.session_factory() as session:
            result = await session.get(SessionModel, session_id)
            if not result:
                return None
            return {
                "session_id": result.id,
                "project_key": result.project_key,
                "status": result.status,
                "config": result.config,
                "created_at": result.created_at.isoformat(),
            }

    async def list_sessions(self, project_key: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
        await self._ensure_tables()
        async with self.session_factory() as session:
            stmt = select(SessionModel).order_by(SessionModel.created_at.desc()).limit(limit).offset(offset)
            if project_key:
                stmt = stmt.where(SessionModel.project_key == project_key)
            results = await session.execute(stmt)
            return [
                {
                    "session_id": s.id,
                    "project_key": s.project_key,
                    "status": s.status,
                    "created_at": s.created_at.isoformat(),
                }
                for s in results.scalars().all()
            ]

    async def emit_event(
        self,
        session_id: str,
        kind: str,
        data: dict[str, Any],
        parent_uuid: str | None = None,
        agent_id: str | None = None,
        cost_tokens: int | None = None,
        cost_usd: float | None = None,
    ) -> dict:
        async with self.session_factory() as session:
            max_seq = await session.scalar(
                select(func.coalesce(func.max(EventModel.sequence), 0)).where(
                    EventModel.session_id == session_id
                )
            )
            event = EventModel(
                uuid=str(uuid.uuid4()),
                session_id=session_id,
                sequence=(max_seq or 0) + 1,
                kind=kind,
                data=data,
                parent_uuid=parent_uuid,
                agent_id=agent_id,
                cost_tokens=cost_tokens,
                cost_usd=cost_usd,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return {
                "uuid": event.uuid,
                "session_id": event.session_id,
                "sequence": event.sequence,
                "kind": event.kind,
                "data": event.data,
                "created_at": event.created_at.isoformat(),
            }

    async def update_session_config(self, session_id: str, config_updates: dict) -> dict | None:
        """Merge config_updates into the session's existing config dict."""
        await self._ensure_tables()
        async with self.session_factory() as session:
            model = await session.get(SessionModel, session_id)
            if not model:
                return None
            merged = dict(model.config)
            merged.update(config_updates)
            model.config = merged
            await session.commit()
            await session.refresh(model)
            return {
                "session_id": model.id,
                "project_key": model.project_key,
                "status": model.status,
                "config": model.config,
                "created_at": model.created_at.isoformat(),
            }

    async def get_events(
        self, session_id: str, offset: int = 0, limit: int = 100
    ) -> list[dict]:
        async with self.session_factory() as session:
            stmt = (
                select(EventModel)
                .where(EventModel.session_id == session_id)
                .order_by(EventModel.sequence)
                .limit(limit)
                .offset(offset)
            )
            results = await session.execute(stmt)
            return [
                {
                    "uuid": e.uuid,
                    "session_id": e.session_id,
                    "sequence": e.sequence,
                    "kind": e.kind,
                    "data": e.data,
                    "parent_uuid": e.parent_uuid,
                    "agent_id": e.agent_id,
                    "created_at": e.created_at.isoformat(),
                }
                for e in results.scalars().all()
            ]
