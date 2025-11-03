"""Cases controller/router."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.deps import get_current_instructor, get_current_user, get_db
from domain.entities.user import User
from domain.models.cases import (
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    CaseUpdate,
)
from services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=CaseListResponse)
async def list_cases(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
):
    """List all cases with optional filters."""
    case_service = CaseService(db)
    return await case_service.list_cases(skip, limit, difficulty, category)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a specific case by ID."""
    case_service = CaseService(db)
    return await case_service.get_case(case_id)


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(
    case_data: CaseCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_instructor)],
):
    """Create a new case (instructor/admin only)."""
    case_service = CaseService(db)
    return await case_service.create_case(case_data)


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_data: CaseUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_instructor)],
):
    """Update a case (instructor/admin only)."""
    case_service = CaseService(db)
    return await case_service.update_case(case_id, case_data)


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_instructor)],
):
    """Delete a case (instructor/admin only)."""
    case_service = CaseService(db)
    await case_service.delete_case(case_id)

