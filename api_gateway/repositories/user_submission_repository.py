# api_gateway/repositories/user_submission_repository.py
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from base_repository import BaseRepository
from database.models import UserSubmission


class UserSubmissionRepository(BaseRepository[UserSubmission]):
    def __init__(self, session: Session):
        super().__init__(UserSubmission, session)

    def get_by_submission_id(self, submission_id: str) -> Optional[UserSubmission]:
        return self.session.query(UserSubmission).filter(UserSubmission.submission_id == submission_id).first()

    def get_recent_submissions(self, limit: int = 10) -> List[UserSubmission]:
        return self.session.query(UserSubmission).order_by(desc(UserSubmission.created_at)).limit(limit).all()

    def search_submissions(self, query: str, limit: int = 20) -> List[UserSubmission]:
        search = f"%{query}%"
        return self.session.query(UserSubmission).filter(
            (UserSubmission.company_name.ilike(search)) |
            (UserSubmission.email.ilike(search)) |
            (UserSubmission.phone.ilike(search))
        ).limit(limit).all()