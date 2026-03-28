from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum as SAEnum, Boolean
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
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class MilestoneStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    AI_REVIEWED = "ai_reviewed"
    PASSED = "passed"
    FAILED = "failed"
    DISPUTED = "disputed"


# ---------------------------------------------------------------------------
# User model (expanded for client + freelancer profiles)
# ---------------------------------------------------------------------------
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

    # --- Freelancer-specific profile fields ---
    hourly_rate = Column(Float, nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    github_username = Column(String(100), nullable=True)
    experience_years = Column(Integer, nullable=True)
    total_jobs_completed = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)

    # --- Client-specific profile fields ---
    company_name = Column(String(255), nullable=True)
    company_url = Column(String(500), nullable=True)
    total_jobs_posted = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)

    # --- Avatar / display ---
    avatar_url = Column(String(500), nullable=True)

    subscription = relationship("Subscription", back_populates="user", uselist=False)
    posted_jobs = relationship("Job", back_populates="client", foreign_keys="Job.client_id")
    assigned_jobs = relationship("Job", back_populates="freelancer", foreign_keys="Job.freelancer_id")
    worker_score = relationship("WorkerScore", back_populates="user", uselist=False)
    reviews_given = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    tier = Column(SAEnum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="subscription")


# ---------------------------------------------------------------------------
# Job (now with step-count and total budget split across milestones)
# ---------------------------------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    requirements_text = Column(Text, nullable=True)
    budget = Column(Float, default=0.0)
    status = Column(SAEnum(JobStatus), default=JobStatus.OPEN, nullable=False)
    skills_required = Column(Text, nullable=True)  # comma-separated
    total_steps = Column(Integer, default=1)
    current_step = Column(Integer, default=0)  # 0 = not started

    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    freelancer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # AI analysis results (overall job)
    github_repo_url = Column(String(500), nullable=True)
    ai_analysis_result = Column(Text, nullable=True)
    ai_risk_score = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    client = relationship("User", back_populates="posted_jobs", foreign_keys=[client_id])
    freelancer = relationship("User", back_populates="assigned_jobs", foreign_keys=[freelancer_id])
    milestones = relationship("Milestone", back_populates="job", order_by="Milestone.step_number")
    reviews = relationship("Review", back_populates="job")


# ---------------------------------------------------------------------------
# Milestone (each step in a job)
# ---------------------------------------------------------------------------
class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    step_number = Column(Integer, nullable=False)  # 1, 2, 3...
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    acceptance_criteria = Column(Text, nullable=False)  # what AI checks against
    deadline = Column(DateTime(timezone=True), nullable=False)
    payout_amount = Column(Float, default=0.0)  # budget per step
    status = Column(SAEnum(MilestoneStatus), default=MilestoneStatus.PENDING, nullable=False)

    # Freelancer submission
    github_repo_url = Column(String(500), nullable=True)
    github_commit_sha = Column(String(40), nullable=True)  # specific commit hash
    github_commit_time = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    proof_text = Column(Text, nullable=True)

    # AI analysis for this milestone
    ai_score = Column(Float, nullable=True)  # 0-100 quality score
    ai_analysis = Column(Text, nullable=True)  # JSON: detailed breakdown
    ai_checked_at = Column(DateTime(timezone=True), nullable=True)
    deadline_met = Column(Boolean, nullable=True)  # was commit within deadline?

    # Blockchain proof
    proof_hash = Column(String(66), nullable=True)  # on-chain hash
    payment_released = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="milestones")


# ---------------------------------------------------------------------------
# Worker confidence score (cumulative quality tracking)
# ---------------------------------------------------------------------------
class WorkerScore(Base):
    __tablename__ = "worker_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Cumulative scores
    total_milestones_completed = Column(Integer, default=0)
    total_milestones_failed = Column(Integer, default=0)
    total_milestones_late = Column(Integer, default=0)

    # Quality metrics (running averages)
    avg_quality_score = Column(Float, default=0.0)   # avg AI score across all milestones
    avg_deadline_adherence = Column(Float, default=1.0)  # % of milestones on time
    avg_client_rating = Column(Float, default=0.0)   # avg client review score

    # Overall confidence score (0-100, computed from above)
    confidence_score = Column(Float, default=50.0)

    # History tracking
    dispute_count = Column(Integer, default=0)
    on_time_streak = Column(Integer, default=0)  # consecutive on-time deliveries
    fraud_flags = Column(Integer, default=0)  # times MLP flagged as suspicious
    avg_fraud_risk = Column(Float, default=0.0)  # running avg of MLP risk scores
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="worker_score")


# ---------------------------------------------------------------------------
# Reviews (client ↔ freelancer)
# ---------------------------------------------------------------------------
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews_given", foreign_keys=[reviewer_id])
    reviewee = relationship("User", back_populates="reviews_received", foreign_keys=[reviewee_id])
