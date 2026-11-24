from uuid import UUID

from sqlalchemy.orm import Session

from app.insidehubv2_ai.models import AiPromptLog


class AiPromptLogRepository:
    @staticmethod
    def create(db: Session, log: AiPromptLog) -> AiPromptLog:
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def list_for_organization(
        db: Session,
        organization_id: UUID,
        limit: int = 50,
    ) -> list[AiPromptLog]:
        return (
            db.query(AiPromptLog)
            .filter(AiPromptLog.organization_id == organization_id)
            .order_by(AiPromptLog.created_at.desc())
            .limit(limit)
            .all()
        )
