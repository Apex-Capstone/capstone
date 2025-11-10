"""Case repository for database operations."""

from typing import Optional

from sqlalchemy.orm import Session

from domain.entities.case import Case


class CaseRepository:
    """Repository for Case entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, case_id: int) -> Optional[Case]:
        """Get case by ID."""
        return self.db.query(Case).filter(Case.id == case_id).first()
        
    def _base_query(self, difficulty: Optional[str], category: Optional[str]):
        q = self.db.query(Case)
        if difficulty:
            q = q.filter(Case.difficulty_level == difficulty)
        if category:
            q = q.filter(Case.category == category)
        return q

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[Case]:
        q = self._base_query(difficulty, category)
        return (
            q.order_by(Case.created_at.desc(), Case.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(
        self,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        return self._base_query(difficulty, category).count()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        difficulty: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[Case]:
        """Get all cases with optional filters and pagination."""
        query = self.db.query(Case)
        
        if difficulty:
            query = query.filter(Case.difficulty_level == difficulty)
        
        if category:
            query = query.filter(Case.category == category)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, case: Case) -> Case:
        """Create a new case."""
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case
    
    def update(self, case: Case) -> Case:
        """Update an existing case."""
        self.db.commit()
        self.db.refresh(case)
        return case
    
    def delete(self, case_id: int) -> bool:
        """Delete a case by ID."""
        case = self.get_by_id(case_id)
        if case:
            self.db.delete(case)
            self.db.commit()
            return True
        return False
    
