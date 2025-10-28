"""
Authentication and Authorization Models
"""

# datetime import not used; using server-side timestamps via SQLAlchemy func

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.session import Base

# Association table for user-role many-to-many relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)


class User(Base):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    token_version = Column(Integer, nullable=False, server_default="1")
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    tos_accepted_at = Column(DateTime(timezone=True), nullable=True)
    tos_version = Column(String(50), nullable=True)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    trainer_profile = relationship("Trainer", back_populates="user", uselist=False)
    client_profile = relationship("ClientProfile", back_populates="user", uselist=False)

    # OTP & lockout
    email_otp_hash = Column(String(255), nullable=True)
    email_otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, server_default="0")
    lockout_until = Column(DateTime(timezone=True), nullable=True)


class Role(Base):
    """Role model for role-based access control"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", back_populates="role")


class Permission(Base):
    """Permission model for fine-grained access control"""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    resource = Column(
        String(100), nullable=False
    )  # e.g., 'client', 'progress', 'exercise'
    action = Column(String(100), nullable=False)  # e.g., 'read', 'write', 'delete'
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    role = relationship("Role", back_populates="permissions")


class RefreshToken(Base):
    """Server-side stored refresh tokens for secure rotation and revocation."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(100), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
