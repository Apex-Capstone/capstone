"""User repository for database operations."""

from typing import Optional

from sqlalchemy.orm import Session

from domain.entities.user import User


class UserRepository:
    """Repository for User entity operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def create(self, user: User) -> User:
        """Create a new user."""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update(self, user: User) -> User:
        """Update an existing user."""
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user_id: int) -> bool:
        """Delete a user by ID."""
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
    
    def count(self) -> int:
        """Count total users."""
        return self.db.query(User).count()
    
    def count_by_role(self) -> dict[str, int]:
        """Count users by role."""
        from sqlalchemy import func
        
        results = self.db.query(
            User.role,
            func.count(User.id)
        ).group_by(User.role).all()
        
        return {role: count for role, count in results}

