"""Case management service."""

from typing import Optional

from sqlalchemy.orm import Session

from core.errors import NotFoundError
from domain.entities.case import Case
from domain.models.cases import CaseCreate, CaseListResponse, CaseResponse, CaseUpdate
from repositories.case_repo import CaseRepository


class CaseService:
    """Service for case operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.case_repo = CaseRepository(db)
    
    async def create_case(self, case_data: CaseCreate) -> CaseResponse:
        """Create a new case."""
        case = Case(
            title=case_data.title,
            description=case_data.description,
            script=case_data.script,
            objectives=case_data.objectives,
            difficulty_level=case_data.difficulty_level,
            category=case_data.category,
            patient_background=case_data.patient_background,
            expected_spikes_flow=case_data.expected_spikes_flow,
            evaluator_plugin=case_data.evaluator_plugin,
        )
        
        created_case = self.case_repo.create(case)
        return CaseResponse.model_validate(created_case)
    
    async def get_case(self, case_id: int) -> CaseResponse:
        """Get case by ID."""
        case = self.case_repo.get_by_id(case_id)
        if not case:
            raise NotFoundError(f"Case with ID {case_id} not found")
        
        return CaseResponse.model_validate(case)
    
    async def list_cases(
        self,
        skip: int = 0,
        limit: int = 100,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
    ) -> CaseListResponse:
        """List cases with optional filters."""
        cases = self.case_repo.get_all(
            skip=skip,
            limit=limit,
            difficulty=difficulty,
            category=category,
        )
        total = self.case_repo.count(difficulty=difficulty, category=category)

        
        return CaseListResponse(
            cases=[CaseResponse.model_validate(case) for case in cases],
            total=total,
        )
    
    async def update_case(self, case_id: int, case_data: CaseUpdate) -> CaseResponse:
        """Update a case."""
        case = self.case_repo.get_by_id(case_id)
        if not case:
            raise NotFoundError(f"Case with ID {case_id} not found")
        
        # Update fields
        update_data = case_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(case, field, value)
        
        updated_case = self.case_repo.update(case)
        return CaseResponse.model_validate(updated_case)
    
    async def delete_case(self, case_id: int) -> bool:
        """Delete a case."""
        success = self.case_repo.delete(case_id)
        if not success:
            raise NotFoundError(f"Case with ID {case_id} not found")
        return True

