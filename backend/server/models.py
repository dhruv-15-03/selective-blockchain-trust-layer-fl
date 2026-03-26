from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum


class UserRole(str, enum.Enum):
    CLIENT = "client"
    FREELANCER = "freelancer"


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    PREMIUM = "premium"


class JobStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PROOF_SUBMITTED = "proof_submitted"
    AI_REVIEWED = "ai_reviewed"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.FREELANCER, nullable=False)
    wallet_address = Column(String(42), unique=True, nullable=True, index=True)
    trust_score = Column(Integer, default=100)
    skills = Column(Text, nullable=True)  # comma-separated skills
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("Subscription", back_populates="user", uselist=False)
    posted_jobs = relationship("Job", back_populates="client", foreign_keys="Job.client_id")
    assigned_jobs = relationship("Job", back_populates="freelancer", foreign_keys="Job.freelancer_id")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    tier = Column(SAEnum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscription")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    requirements_text = Column(Text, nullable=True)
    budget = Column(Float, default=0.0)
    deadline_hours = Column(Float, default=72.0)
    status = Column(SAEnum(JobStatus), default=JobStatus.OPEN, nullable=False)
    skills_required = Column(Text, nullable=True)  # comma-separated

    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # AI analysis results
    github_repo_url = Column(String(500), nullable=True)
    ai_analysis_result = Column(Text, nullable=True)  # JSON string
    ai_risk_score = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("User", back_populates="posted_jobs", foreign_keys=[client_id])
    freelancer = relationship("User", back_populates="assigned_jobs", foreign_keys=[freelancer_id])
