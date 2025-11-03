"""Research service for data anonymization and export."""

import csv
import json
from datetime import datetime
from io import StringIO
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from domain.models.admin import ResearchExportRequest, ResearchExportResponse
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository


class ResearchService:
    """Service for research data export with anonymization."""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.turn_repo = TurnRepository(db)
        self.feedback_repo = FeedbackRepository(db)
    
    async def export_research_data(
        self,
        export_request: ResearchExportRequest,
    ) -> ResearchExportResponse:
        """Export anonymized research data."""
        # Get sessions based on filters
        sessions = self._get_filtered_sessions(export_request)
        
        # Prepare export data
        export_data = []
        for session in sessions:
            session_data = self._anonymize_session(session, export_request)
            export_data.append(session_data)
        
        # Generate CSV
        csv_content = self._generate_csv(export_data)
        
        # In production, this would upload to storage and return presigned URL
        export_id = str(uuid4())
        download_url = f"/api/research/exports/{export_id}/download"
        
        return ResearchExportResponse(
            export_id=export_id,
            download_url=download_url,
            generated_at=datetime.utcnow(),
            record_count=len(export_data),
        )
    
    def _get_filtered_sessions(
        self,
        export_request: ResearchExportRequest,
    ) -> list:
        """Get sessions based on export filters."""
        # Basic implementation - would add date and case filters
        return self.session_repo.get_all(skip=0, limit=1000)
    
    def _anonymize_session(
        self,
        session,
        export_request: ResearchExportRequest,
    ) -> dict[str, Any]:
        """Anonymize session data for research."""
        data = {
            "session_id": f"anon_{session.id}" if export_request.anonymize else session.id,
            "case_id": session.case_id,
            "duration_seconds": session.duration_seconds,
            "state": session.state,
            "spikes_stage": session.current_spikes_stage,
        }
        
        if export_request.include_turns:
            turns = self.turn_repo.get_by_session(session.id)
            data["turn_count"] = len(turns)
            data["turns"] = [
                {
                    "turn_number": turn.turn_number,
                    "role": turn.role,
                    "text": self._anonymize_text(turn.text) if export_request.anonymize else turn.text,
                    "spikes_stage": turn.spikes_stage,
                }
                for turn in turns
            ]
        
        if export_request.include_feedback:
            feedback = self.feedback_repo.get_by_session(session.id)
            if feedback:
                data["feedback"] = {
                    "empathy_score": feedback.empathy_score,
                    "communication_score": feedback.communication_score,
                    "spikes_completion_score": feedback.spikes_completion_score,
                    "overall_score": feedback.overall_score,
                }
        
        return data
    
    def _anonymize_text(self, text: str) -> str:
        """Anonymize text by removing potential PII."""
        # Simple anonymization - in production would use NLP for PII detection
        return text  # Placeholder
    
    def _generate_csv(self, data: list[dict]) -> str:
        """Generate CSV from export data."""
        if not data:
            return ""
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()

