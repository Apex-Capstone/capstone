"""Scoring service for empathy, communication, and SPIKES metrics."""

import json
from typing import Any

from sqlalchemy.orm import Session

from core.errors import NotFoundError
from domain.entities.feedback import Feedback
from domain.models.sessions import FeedbackResponse
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository


class ScoringService:
    """Service for calculating performance scores and feedback."""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.turn_repo = TurnRepository(db)
        self.feedback_repo = FeedbackRepository(db)
    
    async def generate_feedback(self, session_id: int) -> FeedbackResponse:
        """Generate comprehensive feedback for a session."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session {session_id} not found")
        
        turns = self.turn_repo.get_by_session(session_id)
        
        # Calculate scores
        empathy_score = self._calculate_empathy_score(turns)
        communication_score = self._calculate_communication_score(turns)
        spikes_score = self._calculate_spikes_completion(session, turns)
        overall_score = (empathy_score + communication_score + spikes_score) / 3
        
        # Generate detailed metrics
        empathy_spikes = self._identify_empathy_spikes(turns)
        question_ratios = self._calculate_question_ratios(turns)
        reassurance_moments = self._identify_reassurance_moments(turns)
        spikes_coverage = self._analyze_spikes_coverage(turns)
        
        # Generate textual feedback
        strengths, improvements = self._generate_textual_feedback(
            empathy_score,
            communication_score,
            spikes_score,
            question_ratios,
        )
        
        # Create or update feedback
        existing_feedback = self.feedback_repo.get_by_session(session_id)
        if existing_feedback:
            feedback = existing_feedback
        else:
            feedback = Feedback(session_id=session_id)
        
        feedback.empathy_score = empathy_score
        feedback.communication_score = communication_score
        feedback.spikes_completion_score = spikes_score
        feedback.overall_score = overall_score
        feedback.empathy_spikes = json.dumps(empathy_spikes)
        feedback.question_ratios = json.dumps(question_ratios)
        feedback.reassurance_moments = json.dumps(reassurance_moments)
        feedback.spikes_coverage = json.dumps(spikes_coverage)
        feedback.strengths = strengths
        feedback.areas_for_improvement = improvements
        feedback.detailed_feedback = f"Overall Score: {overall_score:.1f}/10"
        
        if existing_feedback:
            saved_feedback = self.feedback_repo.update(feedback)
        else:
            saved_feedback = self.feedback_repo.create(feedback)
        
        return FeedbackResponse.model_validate(saved_feedback)
    
    def _calculate_empathy_score(self, turns: list) -> float:
        """Calculate average empathy score from turns."""
        empathy_scores = []
        for turn in turns:
            if turn.role == "user" and turn.metrics_json:
                try:
                    metrics = json.loads(turn.metrics_json.replace("'", '"'))
                    if "empathy" in metrics:
                        empathy_scores.append(metrics["empathy"].get("empathy_score", 0))
                except:
                    pass
        
        return sum(empathy_scores) / len(empathy_scores) if empathy_scores else 5.0
    
    def _calculate_communication_score(self, turns: list) -> float:
        """Calculate communication effectiveness score."""
        # Placeholder: base score on question types and clarity
        return 7.0  # Default score
    
    def _calculate_spikes_completion(self, session, turns: list) -> float:
        """Calculate SPIKES protocol completion score."""
        # Check which stages were reached
        stages_reached = set()
        for turn in turns:
            if turn.spikes_stage:
                stages_reached.add(turn.spikes_stage)
        
        completion_ratio = len(stages_reached) / 6  # 6 SPIKES stages
        return completion_ratio * 10
    
    def _identify_empathy_spikes(self, turns: list) -> dict[str, Any]:
        """Identify moments of high empathy."""
        spikes = []
        for turn in turns:
            if turn.role == "user" and turn.metrics_json:
                try:
                    metrics = json.loads(turn.metrics_json.replace("'", '"'))
                    empathy = metrics.get("empathy", {})
                    if empathy.get("empathy_score", 0) >= 7:
                        spikes.append({
                            "turn_number": turn.turn_number,
                            "score": empathy.get("empathy_score"),
                            "timestamp": str(turn.timestamp),
                        })
                except:
                    pass
        return {"count": len(spikes), "moments": spikes}
    
    def _calculate_question_ratios(self, turns: list) -> dict[str, Any]:
        """Calculate open vs closed question ratios."""
        open_count = 0
        closed_count = 0
        
        for turn in turns:
            if turn.role == "user" and turn.metrics_json:
                try:
                    metrics = json.loads(turn.metrics_json.replace("'", '"'))
                    q_type = metrics.get("question_type")
                    if q_type == "open":
                        open_count += 1
                    elif q_type == "closed":
                        closed_count += 1
                except:
                    pass
        
        total = open_count + closed_count
        return {
            "open": open_count,
            "closed": closed_count,
            "open_ratio": open_count / total if total > 0 else 0,
        }
    
    def _identify_reassurance_moments(self, turns: list) -> dict[str, Any]:
        """Identify reassurance statements."""
        # Placeholder implementation
        return {"count": 0, "moments": []}
    
    def _analyze_spikes_coverage(self, turns: list) -> dict[str, Any]:
        """Analyze coverage of SPIKES stages."""
        stages = {}
        for turn in turns:
            if turn.spikes_stage:
                stages[turn.spikes_stage] = stages.get(turn.spikes_stage, 0) + 1
        return stages
    
    def _generate_textual_feedback(
        self,
        empathy_score: float,
        communication_score: float,
        spikes_score: float,
        question_ratios: dict,
    ) -> tuple[str, str]:
        """Generate strengths and improvement areas."""
        strengths = []
        improvements = []
        
        if empathy_score >= 7:
            strengths.append("Excellent use of empathetic language")
        else:
            improvements.append("Consider using more empathetic phrases")
        
        if question_ratios.get("open_ratio", 0) > 0.6:
            strengths.append("Good use of open-ended questions")
        else:
            improvements.append("Try asking more open-ended questions")
        
        if spikes_score >= 8:
            strengths.append("Comprehensive coverage of SPIKES protocol")
        else:
            improvements.append("Work on covering all SPIKES protocol stages")
        
        return "\n".join(strengths), "\n".join(improvements)

