from dataclasses import dataclass

from sqlalchemy import select

from infrastructure.db import SessionLocal
from models.orm import DeepSeekSummaryUsage


@dataclass(frozen=True)
class DeepSeekSummaryUsageRecord:
    chat_id: int
    last_summary_created_at: str
    last_summary_message_id: int | None


class DeepSeekSummaryUsageRepository:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def get_usage(self, chat_id: int) -> DeepSeekSummaryUsageRecord | None:
        session = self.session_factory()
        try:
            statement = select(DeepSeekSummaryUsage).where(DeepSeekSummaryUsage.chat_id == chat_id)
            row = session.execute(statement).scalar_one_or_none()
            if row is None:
                return None
            return DeepSeekSummaryUsageRecord(
                chat_id=row.chat_id,
                last_summary_created_at=row.last_summary_created_at or "",
                last_summary_message_id=row.last_summary_message_id,
            )
        finally:
            session.close()

    def save_usage(
        self,
        chat_id: int,
        last_summary_created_at: str,
        last_summary_message_id: int | None,
    ) -> None:
        session = self.session_factory()
        try:
            statement = select(DeepSeekSummaryUsage).where(DeepSeekSummaryUsage.chat_id == chat_id)
            row = session.execute(statement).scalar_one_or_none()
            if row is None:
                row = DeepSeekSummaryUsage(
                    chat_id=chat_id,
                    last_summary_created_at=last_summary_created_at,
                    last_summary_message_id=last_summary_message_id,
                )
                session.add(row)
            else:
                row.last_summary_created_at = last_summary_created_at
                row.last_summary_message_id = last_summary_message_id
            session.commit()
        finally:
            session.close()
