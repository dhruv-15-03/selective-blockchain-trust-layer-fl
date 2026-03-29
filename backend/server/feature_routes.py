"""
Feature routes — Milestone-based step workflow with AI quality scoring.

1. User profiles (client + freelancer, different views)
2. Subscription system
3. Job posting with step-based milestones
4. GitHub-verified AI quality checker per milestone
5. Worker confidence score system
6. Reviews
7. Freelancer matching
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import json
import re
import hashlib
import math
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from database import get_db
from models import (
    User, Subscription, Job, Milestone, WorkerScore, Review,
    UserRole, SubscriptionTier, JobStatus, MilestoneStatus,
)
from auth_utils import get_current_user

router = APIRouter(tags=["features"])

# --- LLM Configuration (GitHub Models API) ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://models.inference.ai.github.com/chat/completions")
LLM_ENABLED = bool(GITHUB_TOKEN)


# --- JobLedger contract (complete job blocks on-chain) ---
try:
    from job_ledger_interface import (
        ledger_create_job, ledger_commit_requirements, ledger_commit_submission,
        ledger_commit_ai_review, ledger_commit_decision,
        ledger_get_job, ledger_get_milestone,
    )
    LEDGER_AVAILABLE = True
except ImportError:
    LEDGER_AVAILABLE = False

# --- Blockchain on-chain commit helpers ---
def _milestone_round(job_id: int, step: int, phase: int) -> int:
    """
    Unique round number for each milestone phase on-chain.
    Phase 0: requirements, 1: submission, 2: AI analysis, 3: decision
    """
    return job_id * 1000 + step * 10 + phase


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _commit_hash_onchain(round_number: int, data_str: str, sender_addr: str) -> dict:
    """
    Commit a SHA256 hash on-chain via TrustLayer.submitHash().
    Returns {ok, hash_hex, round, tx_hash} or {ok: False, error}.
    """
    try:
        from blockchain_interface import contract, w3
        from eth_utils import to_checksum_address

        hash_hex = _sha256_hex(data_str)
        hash_bytes = bytes.fromhex(hash_hex)
        addr = to_checksum_address(sender_addr)

        previous = w3.eth.default_account
        try:
            w3.eth.default_account = addr
            # Ensure registered
            try:
                tx_reg = contract.functions.registerClient().transact()
                w3.eth.wait_for_transaction_receipt(tx_reg)
            except Exception:
                pass
            # Submit hash
            try:
                tx = contract.functions.submitHash(round_number, hash_bytes).transact()
                receipt = w3.eth.wait_for_transaction_receipt(tx)
                return {
                    "ok": True,
                    "hash_hex": hash_hex,
                    "round": round_number,
                    "tx_hash": receipt.transactionHash.hex(),
                    "block": receipt.blockNumber,
                }
            except Exception as e:
                return {"ok": False, "hash_hex": hash_hex, "round": round_number, "error": str(e)[:200]}
        finally:
            w3.eth.default_account = previous
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _verify_hash_onchain(round_number: int, sender_addr: str, expected_hash_hex: str) -> dict:
    """Verify an on-chain hash matches the expected value."""
    try:
        from blockchain_interface import contract, w3
        from eth_utils import to_checksum_address

        addr = to_checksum_address(sender_addr)
        onchain = contract.functions.updateHashes(round_number, addr).call()
        onchain_hex = bytes(onchain).hex()
        expected_clean = expected_hash_hex.replace("0x", "")
        matches = onchain_hex == expected_clean and onchain_hex != "0" * 64

        return {
            "verified": matches,
            "onchain_hash": "0x" + onchain_hex,
            "expected_hash": "0x" + expected_clean,
            "round": round_number,
            "address": addr,
        }
    except Exception as e:
        return {"verified": False, "error": str(e)[:200]}


# ===================================================================
# Pydantic Schemas
# ===================================================================

class LinkWalletRequest(BaseModel):
    wallet_address: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None
    hourly_rate: Optional[float] = None
    portfolio_url: Optional[str] = None
    github_username: Optional[str] = None
    experience_years: Optional[int] = None
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    avatar_url: Optional[str] = None


class SubscribeRequest(BaseModel):
    tier: str = "premium"
    duration_days: int = 30


class MilestoneStep(BaseModel):
    title: str
    description: Optional[str] = None
    acceptance_criteria: str
    deadline_hours: float  # hours from job start
    payout_amount: float


class CreateJobPostRequest(BaseModel):
    title: str
    description: str
    requirements_text: Optional[str] = None
    budget: float = 0.0
    skills_required: Optional[str] = None
    milestones: List[MilestoneStep]  # at least 1 step required


class ApplyJobRequest(BaseModel):
    cover_letter: Optional[str] = None


class SubmitMilestoneRequest(BaseModel):
    github_repo_url: str
    proof_text: Optional[str] = None


class ReviewRequest(BaseModel):
    rating: int  # 1-5
    comment: Optional[str] = None


class MatchQuery(BaseModel):
    skills: Optional[str] = None
    min_trust: int = 0
    limit: int = 20


# ===================================================================
# Helpers
# ===================================================================

def _trust_level(score: int) -> str:
    if score >= 100:
        return "Platinum"
    if score >= 80:
        return "Gold"
    if score >= 60:
        return "Silver"
    return "Bronze"


def _require_premium(user: User, db: Session):
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub or sub.tier != SubscriptionTier.PREMIUM:
        raise HTTPException(status_code=403, detail="Premium subscription required")
    if sub.expires_at and datetime.utcnow() >= sub.expires_at:
        raise HTTPException(status_code=403, detail="Subscription expired")


def _get_worker_score(db: Session, user_id: int) -> WorkerScore:
    ws = db.query(WorkerScore).filter(WorkerScore.user_id == user_id).first()
    if not ws:
        ws = WorkerScore(user_id=user_id, confidence_score=50.0)
        db.add(ws)
        db.commit()
        db.refresh(ws)
    return ws


# ===================================================================
# 1. USER PROFILES (Client + Freelancer, different views)
# ===================================================================

@router.get("/user/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    trust_score = current_user.trust_score or 100

    if current_user.wallet_address:
        try:
            from blockchain_interface import contract
            onchain_trust = contract.functions.getTrust(current_user.wallet_address).call()
            trust_score = onchain_trust
            db = current_user._db_session
            current_user.trust_score = trust_score
            db.commit()
        except Exception:
            pass

    db = current_user._db_session
    ws = _get_worker_score(db, current_user.id)

    base = {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value if current_user.role else "freelancer",
        "wallet_address": current_user.wallet_address,
        "trust_score": trust_score,
        "trust_level": _trust_level(trust_score),
        "skills": current_user.skills,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "created_at": str(current_user.created_at) if current_user.created_at else None,
    }

    if current_user.role == UserRole.FREELANCER:
        # Compute unified project trust score:
        # Combines blockchain trust (on-chain) + AI confidence + quality avg
        blockchain_trust = trust_score  # 0-120
        ai_confidence = ws.confidence_score  # 0-100
        ai_quality = ws.avg_quality_score  # 0-100
        fraud_risk = ws.avg_fraud_risk or 0  # 0-1

        # Unified score: 40% blockchain + 35% AI confidence + 25% quality - fraud penalty
        unified = (0.40 * min(blockchain_trust, 100) +
                   0.35 * ai_confidence +
                   0.25 * ai_quality -
                   min(fraud_risk * 30, 20))
        unified = max(0, min(100, round(unified, 2)))

        base.update({
            "hourly_rate": current_user.hourly_rate,
            "portfolio_url": current_user.portfolio_url,
            "github_username": current_user.github_username,
            "experience_years": current_user.experience_years,
            "total_jobs_completed": current_user.total_jobs_completed or 0,
            "total_earnings": current_user.total_earnings or 0.0,
            "project_trust_score": unified,
            "worker_score": {
                "confidence_score": round(ws.confidence_score, 2),
                "avg_quality_score": round(ws.avg_quality_score, 2),
                "avg_deadline_adherence": round(ws.avg_deadline_adherence, 2),
                "avg_client_rating": round(ws.avg_client_rating, 2),
                "total_milestones_completed": ws.total_milestones_completed,
                "total_milestones_failed": ws.total_milestones_failed,
                "total_milestones_late": ws.total_milestones_late,
                "on_time_streak": ws.on_time_streak,
                "dispute_count": ws.dispute_count,
                "fraud_flags": ws.fraud_flags or 0,
                "avg_fraud_risk": round(ws.avg_fraud_risk or 0, 4),
            },
            "score_breakdown": {
                "blockchain_trust": trust_score,
                "ai_confidence": round(ai_confidence, 2),
                "ai_quality_avg": round(ai_quality, 2),
                "fraud_risk": round(fraud_risk, 4),
                "formula": "40% blockchain + 35% confidence + 25% quality - fraud_penalty",
            },
        })
    else:
        base.update({
            "company_name": current_user.company_name,
            "company_url": current_user.company_url,
            "total_jobs_posted": current_user.total_jobs_posted or 0,
            "total_spent": current_user.total_spent or 0.0,
        })

    # Reviews received
    reviews = db.query(Review).filter(Review.reviewee_id == current_user.id).all()
    base["reviews"] = [
        {"rating": r.rating, "comment": r.comment, "created_at": str(r.created_at)}
        for r in reviews
    ]
    base["avg_rating"] = round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0.0

    return base


@router.get("/user/profile/{user_id}")
def get_public_profile(user_id: int, current_user: User = Depends(get_current_user)):
    db = current_user._db_session
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = {
        "id": user.id,
        "name": user.name,
        "role": user.role.value if user.role else "freelancer",
        "trust_score": user.trust_score or 100,
        "trust_level": _trust_level(user.trust_score or 100),
        "skills": user.skills,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "created_at": str(user.created_at) if user.created_at else None,
    }

    if user.role == UserRole.FREELANCER:
        ws = _get_worker_score(db, user.id)
        u_trust = user.trust_score or 100
        unified = (0.40 * min(u_trust, 100) +
                   0.35 * ws.confidence_score +
                   0.25 * ws.avg_quality_score -
                   min((ws.avg_fraud_risk or 0) * 30, 20))
        unified = max(0, min(100, round(unified, 2)))
        result.update({
            "hourly_rate": user.hourly_rate,
            "portfolio_url": user.portfolio_url,
            "github_username": user.github_username,
            "experience_years": user.experience_years,
            "total_jobs_completed": user.total_jobs_completed or 0,
            "project_trust_score": unified,
            "confidence_score": round(ws.confidence_score, 2),
            "avg_quality_score": round(ws.avg_quality_score, 2),
            "avg_deadline_adherence": round(ws.avg_deadline_adherence, 2),
            "on_time_streak": ws.on_time_streak,
            "fraud_flags": ws.fraud_flags or 0,
        })
    else:
        result.update({
            "company_name": user.company_name,
            "company_url": user.company_url,
            "total_jobs_posted": user.total_jobs_posted or 0,
        })

    reviews = db.query(Review).filter(Review.reviewee_id == user.id).all()
    result["reviews"] = [
        {"rating": r.rating, "comment": r.comment, "created_at": str(r.created_at)}
        for r in reviews
    ]
    result["avg_rating"] = round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0.0
    return result


@router.post("/user/link_wallet")
def link_wallet(req: LinkWalletRequest, current_user: User = Depends(get_current_user)):
    addr = req.wallet_address.strip()
    if not re.match(r"^0x[0-9a-fA-F]{40}$", addr):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

    db = current_user._db_session
    existing = db.query(User).filter(User.wallet_address == addr, User.id != current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Wallet already linked to another account")

    current_user.wallet_address = addr
    try:
        from blockchain_interface import contract
        current_user.trust_score = contract.functions.getTrust(addr).call()
    except Exception:
        pass
    db.commit()
    return {"ok": True, "wallet_address": addr, "trust_score": current_user.trust_score}


@router.put("/user/profile")
def update_profile(req: UpdateProfileRequest, current_user: User = Depends(get_current_user)):
    db = current_user._db_session
    for field in ["name", "skills", "bio", "hourly_rate", "portfolio_url",
                   "github_username", "experience_years", "company_name",
                   "company_url", "avatar_url"]:
        val = getattr(req, field, None)
        if val is not None:
            setattr(current_user, field, val)
    if req.role is not None:
        if req.role not in ("client", "freelancer"):
            raise HTTPException(status_code=400, detail="Role must be 'client' or 'freelancer'")
        current_user.role = UserRole(req.role)
    db.commit()
    return {"ok": True, "message": "Profile updated"}


# ===================================================================
# 2. SUBSCRIPTIONS
# ===================================================================

@router.post("/subscription/subscribe")
def subscribe(req: SubscribeRequest, current_user: User = Depends(get_current_user)):
    if req.tier not in ("free", "premium"):
        raise HTTPException(status_code=400, detail="Tier must be 'free' or 'premium'")
    db = current_user._db_session
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    tier = SubscriptionTier(req.tier)
    expires = datetime.utcnow() + timedelta(days=req.duration_days) if tier == SubscriptionTier.PREMIUM else None
    if sub:
        sub.tier = tier
        sub.started_at = datetime.utcnow()
        sub.expires_at = expires
    else:
        sub = Subscription(user_id=current_user.id, tier=tier, expires_at=expires)
        db.add(sub)
    db.commit()
    return {"ok": True, "tier": tier.value, "expires_at": str(expires) if expires else None}


@router.get("/subscription/status")
def subscription_status(current_user: User = Depends(get_current_user)):
    db = current_user._db_session
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not sub:
        return {"tier": "free", "active": True, "expires_at": None}
    active = True
    if sub.tier == SubscriptionTier.PREMIUM and sub.expires_at:
        active = datetime.utcnow() < sub.expires_at
    return {"tier": sub.tier.value, "active": active, "expires_at": str(sub.expires_at) if sub.expires_at else None}


# ===================================================================
# 3. JOB POSTING WITH MILESTONES
# ===================================================================

@router.post("/jobs/create")
def create_job(req: CreateJobPostRequest, current_user: User = Depends(get_current_user)):
    """Create a job with one or more milestone steps. Client only, premium required."""
    db = current_user._db_session
    _require_premium(current_user, db)
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Only clients can post jobs")
    if not req.milestones or len(req.milestones) == 0:
        raise HTTPException(status_code=400, detail="At least one milestone step is required")

    total_payout = sum(m.payout_amount for m in req.milestones)
    if total_payout > req.budget * 1.01:
        raise HTTPException(status_code=400, detail="Milestone payouts exceed total budget")

    job = Job(
        title=req.title,
        description=req.description,
        requirements_text=req.requirements_text,
        budget=req.budget,
        status=JobStatus.OPEN,
        skills_required=req.skills_required,
        total_steps=len(req.milestones),
        current_step=0,
        client_id=current_user.id,
    )
    db.add(job)
    db.flush()

    now = datetime.utcnow()
    for i, ms in enumerate(req.milestones, start=1):
        milestone = Milestone(
            job_id=job.id,
            step_number=i,
            title=ms.title,
            description=ms.description,
            acceptance_criteria=ms.acceptance_criteria,
            deadline=now + timedelta(hours=ms.deadline_hours),
            payout_amount=ms.payout_amount,
            status=MilestoneStatus.PENDING,
        )
        db.add(milestone)

    current_user.total_jobs_posted = (current_user.total_jobs_posted or 0) + 1
    db.commit()
    db.refresh(job)

    # ── BLOCKCHAIN: Create complete job block + commit requirements ──
    blockchain_commits = []
    ledger_result = None

    # 1. Create job in JobLedger (complete block)
    if LEDGER_AVAILABLE:
        client_addr = current_user.wallet_address or "0x0000000000000000000000000000000000000000"
        ledger_result = ledger_create_job(
            job.id, client_addr, job.title, job.description,
            job.budget, job.total_steps,
        )

    # 2. Commit each milestone's requirements (full text on-chain via events)
    if LEDGER_AVAILABLE:
        for i, ms in enumerate(req.milestones, start=1):
            data_hash = bytes.fromhex(_sha256_hex(json.dumps({
                "job_id": job.id, "step": i,
                "title": ms.title,
                "acceptance_criteria": ms.acceptance_criteria,
                "budget": ms.payout_amount,
            }, sort_keys=True)))
            bc = ledger_commit_requirements(
                job.id, i, ms.title, ms.acceptance_criteria,
                ms.payout_amount, int(ms.deadline_hours * 3600), data_hash,
            )
            blockchain_commits.append({"step": i, "phase": "requirements", **bc})

    return {
        "ok": True,
        "job_id": job.id,
        "title": job.title,
        "total_steps": job.total_steps,
        "budget": job.budget,
        "milestones": [
            {
                "step": i + 1,
                "title": req.milestones[i].title,
                "acceptance_criteria": req.milestones[i].acceptance_criteria,
                "deadline_hours": req.milestones[i].deadline_hours,
                "payout": req.milestones[i].payout_amount,
            }
            for i in range(len(req.milestones))
        ],
        "blockchain_job": ledger_result,
        "blockchain_commits": blockchain_commits,
    }


@router.get("/jobs/list")
def list_jobs(
    status_filter: Optional[str] = None,
    skills: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    db = current_user._db_session
    q = db.query(Job)
    if status_filter:
        q = q.filter(Job.status == JobStatus(status_filter))
    if skills:
        for skill in skills.split(","):
            skill = skill.strip()
            if skill:
                q = q.filter(Job.skills_required.ilike(f"%{skill}%"))
    jobs = q.order_by(Job.created_at.desc()).limit(min(limit, 100)).all()
    result = []
    for j in jobs:
        milestones = [
            {"step": m.step_number, "title": m.title, "status": m.status.value,
             "deadline": str(m.deadline), "payout": m.payout_amount}
            for m in j.milestones
        ]
        result.append({
            "job_id": j.id, "title": j.title, "description": j.description[:300],
            "budget": j.budget, "skills_required": j.skills_required,
            "status": j.status.value, "total_steps": j.total_steps,
            "current_step": j.current_step, "client_id": j.client_id,
            "freelancer_id": j.freelancer_id, "milestones": milestones,
            "created_at": str(j.created_at) if j.created_at else None,
        })
    return result


@router.get("/jobs/{job_id}")
def get_job_detail(job_id: int, current_user: User = Depends(get_current_user)):
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    milestones = []
    for m in job.milestones:
        milestones.append({
            "id": m.id, "step": m.step_number, "title": m.title,
            "description": m.description, "acceptance_criteria": m.acceptance_criteria,
            "deadline": str(m.deadline), "payout": m.payout_amount,
            "status": m.status.value, "github_repo_url": m.github_repo_url,
            "github_commit_sha": m.github_commit_sha,
            "deadline_met": m.deadline_met, "ai_score": m.ai_score,
            "ai_analysis": json.loads(m.ai_analysis) if m.ai_analysis else None,
            "payment_released": m.payment_released,
            "submitted_at": str(m.submitted_at) if m.submitted_at else None,
        })

    return {
        "job_id": job.id, "title": job.title, "description": job.description,
        "requirements_text": job.requirements_text, "budget": job.budget,
        "skills_required": job.skills_required, "status": job.status.value,
        "total_steps": job.total_steps, "current_step": job.current_step,
        "client_id": job.client_id, "freelancer_id": job.freelancer_id,
        "milestones": milestones,
        "created_at": str(job.created_at) if job.created_at else None,
    }


@router.post("/jobs/{job_id}/apply")
def apply_for_job(job_id: int, current_user: User = Depends(get_current_user)):
    """Freelancer applies for a job. Checks premium/blacklist gating."""
    db = current_user._db_session
    if current_user.role != UserRole.FREELANCER:
        raise HTTPException(status_code=403, detail="Only freelancers can apply")

    # --- Premium gating for blacklisted/low-confidence freelancers ---
    ws = _get_worker_score(db, current_user.id)
    total_jobs = (current_user.total_jobs_completed or 0)
    is_blacklisted = False
    if current_user.wallet_address:
        from blockchain_interface import safe_is_blacklisted
        is_blacklisted = safe_is_blacklisted(current_user.wallet_address)

    if total_jobs >= 3 and (ws.confidence_score < 30 or is_blacklisted):
        # Must have premium to apply
        sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
        has_premium = (sub and sub.tier == SubscriptionTier.PREMIUM and
                       (not sub.expires_at or datetime.utcnow() < sub.expires_at))
        if not has_premium:
            raise HTTPException(
                status_code=403,
                detail=f"Your confidence score ({ws.confidence_score:.1f}) is below 30 "
                       f"{'and you are blacklisted ' if is_blacklisted else ''}"
                       f"after {total_jobs} jobs. Premium subscription required to apply."
            )

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.OPEN:
        raise HTTPException(status_code=400, detail="Job is not open")
    if job.freelancer_id:
        raise HTTPException(status_code=400, detail="Job already assigned")

    # --- FL fraud model pre-check on applicant ---
    fraud_pre = _run_fraud_precheck(current_user, job, db)
    
    job.freelancer_id = current_user.id
    job.status = JobStatus.IN_PROGRESS
    job.current_step = 1
    first_ms = db.query(Milestone).filter(
        Milestone.job_id == job.id, Milestone.step_number == 1
    ).first()
    if first_ms:
        first_ms.status = MilestoneStatus.IN_PROGRESS
    db.commit()
    return {"ok": True, "job_id": job.id, "message": "Applied and assigned!", "current_step": 1}


# ===================================================================
# 4. MILESTONE SUBMISSION + AI VERIFICATION
# ===================================================================

@router.post("/jobs/{job_id}/milestones/{step}/submit")
def submit_milestone(
    job_id: int, step: int, req: SubmitMilestoneRequest,
    current_user: User = Depends(get_current_user),
):
    """Freelancer submits work for a specific milestone step via GitHub repo."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.freelancer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the assigned freelancer can submit")

    ms = db.query(Milestone).filter(
        Milestone.job_id == job_id, Milestone.step_number == step
    ).first()
    if not ms:
        raise HTTPException(status_code=404, detail=f"Milestone step {step} not found")
    if ms.status not in (MilestoneStatus.IN_PROGRESS, MilestoneStatus.FAILED):
        raise HTTPException(status_code=400, detail=f"Cannot submit in status: {ms.status.value}")

    if not re.match(r"https?://github\.com/[^/]+/[^/]+", req.github_repo_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL")

    ms.github_repo_url = req.github_repo_url
    ms.proof_text = req.proof_text
    ms.submitted_at = datetime.utcnow()
    ms.status = MilestoneStatus.SUBMITTED

    # Fetch latest commit for timestamp verification
    commit_info = _fetch_latest_commit(req.github_repo_url)
    if commit_info:
        ms.github_commit_sha = commit_info["sha"]
        ms.github_commit_time = commit_info["date"]
        ms.deadline_met = commit_info["date"] <= ms.deadline if commit_info["date"] else None
    else:
        ms.deadline_met = ms.submitted_at <= ms.deadline

    # Hash proof on-chain
    proof_data = json.dumps({
        "job_id": job_id, "step": step,
        "repo": req.github_repo_url,
        "commit_sha": ms.github_commit_sha,
        "submitted_at": str(ms.submitted_at),
    }, sort_keys=True)
    ms.proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

    # Commit submission to JobLedger (Phase 1) — full data on-chain
    bc_submit = {"ok": False}
    if LEDGER_AVAILABLE:
        fl_addr = current_user.wallet_address or "0x0000000000000000000000000000000000000000"
        bc_submit = ledger_commit_submission(
            job_id, step, fl_addr,
            req.github_repo_url, ms.github_commit_sha or "",
            bytes.fromhex(ms.proof_hash),
        )

    db.commit()
    return {
        "ok": True, "job_id": job_id, "step": step,
        "status": "submitted",
        "deadline_met": ms.deadline_met,
        "commit_sha": ms.github_commit_sha,
        "commit_time": str(ms.github_commit_time) if ms.github_commit_time else None,
        "proof_hash": ms.proof_hash,
        "blockchain": bc_submit,
    }


@router.post("/jobs/{job_id}/milestones/{step}/ai_review")
def ai_review_milestone(
    job_id: int, step: int,
    current_user: User = Depends(get_current_user),
):
    """
    Hybrid AI review: MLP fraud model + LLM/static code analysis.

    Scoring breakdown:
      60% — Acceptance criteria pass/fail (did the freelancer meet requirements?)
      40% — Code quality composite (structure, tests, docs, error handling, complexity)

    Also runs the FL-trained MLP fraud model on submission metadata to detect
    suspicious patterns (fake submissions, plagiarism signals, etc).

    Updates the freelancer's worker profile with the AI score.
    """
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.id not in (job.client_id, job.freelancer_id):
        raise HTTPException(status_code=403, detail="Access denied")

    ms = db.query(Milestone).filter(
        Milestone.job_id == job_id, Milestone.step_number == step
    ).first()
    if not ms:
        raise HTTPException(status_code=404, detail=f"Milestone step {step} not found")
    if ms.status != MilestoneStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail=f"Milestone not in submitted state: {ms.status.value}")
    if not ms.github_repo_url:
        raise HTTPException(status_code=400, detail="No GitHub repo submitted")

    # ── 1. Fetch repo files ──
    files = _fetch_github_repo_files(ms.github_repo_url)
    if not files:
        raise HTTPException(status_code=400, detail="Could not fetch repo files")

    # ── 2. Full quality analysis against acceptance criteria ──
    analysis = _analyze_code_quality(
        files=files,
        acceptance_criteria=ms.acceptance_criteria,
        milestone_description=ms.description or ms.title,
        job_description=job.description,
    )

    # ── 3. Deadline scoring ──
    deadline_score = 100.0 if ms.deadline_met else max(0.0, 50.0)
    if ms.github_commit_time and ms.deadline:
        if ms.github_commit_time > ms.deadline:
            hours_late = (ms.github_commit_time - ms.deadline).total_seconds() / 3600
            deadline_score = max(0.0, 50.0 - hours_late * 5)

    # ── 4. MLP Fraud Model Check ──
    # Uses the FL-trained fraud detection model from main.py to score submission
    fraud_result = _run_fraud_model_on_submission(job, ms, db)

    # ── 5. Scoring: 60% criteria + 40% code quality ──
    criteria_score = analysis["criteria_coverage"] * 100  # 0-100
    code_quality = analysis["overall_score"]               # 0-100 (structure+tests+docs+errors+complexity)

    # Apply deadline penalty to criteria score
    if not ms.deadline_met:
        criteria_score *= (deadline_score / 100.0)

    # Apply fraud penalty (if MLP flags it as suspicious, reduce score)
    fraud_penalty = 0.0
    if fraud_result and fraud_result.get("risk_score", 0) >= 0.6:
        fraud_penalty = min(25.0, fraud_result["risk_score"] * 30)

    final_score = (0.60 * criteria_score + 0.40 * code_quality) - fraud_penalty
    final_score = max(0.0, min(100.0, final_score))

    passed = final_score >= 60.0

    analysis["criteria_score"] = round(criteria_score, 2)
    analysis["code_quality_score"] = round(code_quality, 2)
    analysis["deadline_score"] = round(deadline_score, 2)
    analysis["deadline_met"] = ms.deadline_met
    analysis["fraud_check"] = fraud_result
    analysis["fraud_penalty"] = round(fraud_penalty, 2)
    analysis["final_score"] = round(final_score, 2)
    analysis["pass"] = passed
    analysis["scoring_breakdown"] = {
        "criteria_weight": "60%",
        "quality_weight": "40%",
        "criteria_raw": round(analysis["criteria_coverage"] * 100, 2),
        "criteria_after_deadline": round(criteria_score, 2),
        "code_quality": round(code_quality, 2),
        "fraud_penalty": round(fraud_penalty, 2),
        "formula": "0.6 * criteria + 0.4 * quality - fraud_penalty",
    }

    # ── 6. Save to milestone ──
    ms.ai_score = round(final_score, 2)
    ms.ai_analysis = json.dumps(analysis)
    ms.ai_checked_at = datetime.utcnow()
    ms.status = MilestoneStatus.AI_REVIEWED

    # ── 7. Update freelancer worker profile immediately ──
    if job.freelancer_id:
        _update_worker_profile_from_review(db, job.freelancer_id, ms, final_score, passed)

    # ── 8. Commit AI review to JobLedger (Phase 2) ──
    bc_ai = {"ok": False}
    if LEDGER_AVAILABLE:
        ai_commit_data = json.dumps({
            "job_id": job_id, "step": step,
            "ai_score": ms.ai_score,
            "pass": passed,
            "criteria_coverage": analysis.get("criteria_coverage"),
            "code_quality": analysis.get("code_quality_score"),
            "fraud_verdict": analysis.get("fraud_check", {}).get("verdict"),
            "analysis_method": analysis.get("analysis_method"),
        }, sort_keys=True)
        bc_ai = ledger_commit_ai_review(
            job_id, step, ms.ai_score or 0, passed,
            analysis.get("analysis_method", "static_analysis"),
            bytes.fromhex(_sha256_hex(ai_commit_data)),
        )

    db.commit()

    return {
        "ok": True, "job_id": job_id, "step": step,
        "ai_score": ms.ai_score,
        "pass": passed,
        "analysis": analysis,
        "blockchain": bc_ai,
    }


@router.post("/jobs/{job_id}/milestones/{step}/approve")
def approve_milestone(
    job_id: int, step: int,
    current_user: User = Depends(get_current_user),
):
    """Client approves milestone -> releases payment, moves to next step."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the client can approve")

    ms = db.query(Milestone).filter(
        Milestone.job_id == job_id, Milestone.step_number == step
    ).first()
    if not ms or ms.status != MilestoneStatus.AI_REVIEWED:
        raise HTTPException(status_code=400, detail="Milestone not ready for approval")

    ms.status = MilestoneStatus.PASSED
    ms.payment_released = True

    _update_worker_score_on_pass(db, job.freelancer_id, ms)

    # Reward on-chain trust (with confirmation tracking)
    reward_result = {"ok": False}
    freelancer = db.query(User).filter(User.id == job.freelancer_id).first()
    if freelancer and freelancer.wallet_address:
        from blockchain_interface import safe_reward
        reward_result = safe_reward(freelancer.wallet_address)
        if reward_result["ok"]:
            freelancer.trust_score = reward_result["trust"]

    if freelancer:
        freelancer.total_earnings = (freelancer.total_earnings or 0) + ms.payout_amount

    # Move to next step or complete job
    next_step = step + 1
    if next_step <= job.total_steps:
        job.current_step = next_step
        next_ms = db.query(Milestone).filter(
            Milestone.job_id == job_id, Milestone.step_number == next_step
        ).first()
        if next_ms:
            next_ms.status = MilestoneStatus.IN_PROGRESS
    else:
        job.status = JobStatus.COMPLETED
        job.current_step = job.total_steps
        if freelancer:
            freelancer.total_jobs_completed = (freelancer.total_jobs_completed or 0) + 1
        current_user.total_spent = (current_user.total_spent or 0) + job.budget

    db.commit()

    # Commit approval to JobLedger (Phase 3)
    bc_decision = {"ok": False}
    if LEDGER_AVAILABLE:
        decision_data = json.dumps({
            "job_id": job_id, "step": step,
            "decision": "APPROVED",
            "payment_released": ms.payout_amount,
            "ai_score": ms.ai_score,
            "freelancer_id": job.freelancer_id,
        }, sort_keys=True)
        bc_decision = ledger_commit_decision(
            job_id, step, True, ms.payout_amount,
            bytes.fromhex(_sha256_hex(decision_data)),
        )

    return {
        "ok": True, "step": step, "status": "passed",
        "payment_released": ms.payout_amount,
        "next_step": next_step if next_step <= job.total_steps else None,
        "job_completed": next_step > job.total_steps,
        "blockchain_reward": reward_result,
        "blockchain_decision": bc_decision,
    }


@router.post("/jobs/{job_id}/milestones/{step}/fail")
def fail_milestone(
    job_id: int, step: int,
    current_user: User = Depends(get_current_user),
):
    """Client rejects milestone -> freelancer can resubmit."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the client can fail a milestone")

    ms = db.query(Milestone).filter(
        Milestone.job_id == job_id, Milestone.step_number == step
    ).first()
    if not ms or ms.status != MilestoneStatus.AI_REVIEWED:
        raise HTTPException(status_code=400, detail="Milestone not in review state")

    ms.status = MilestoneStatus.FAILED
    _update_worker_score_on_fail(db, job.freelancer_id, ms)

    # Penalize on-chain (with confirmation tracking)
    penalty_result = {"ok": False}
    freelancer = db.query(User).filter(User.id == job.freelancer_id).first()
    if freelancer and freelancer.wallet_address:
        from blockchain_interface import safe_penalize
        penalty_result = safe_penalize(freelancer.wallet_address)
        if penalty_result["ok"]:
            freelancer.trust_score = penalty_result["trust"]

    db.commit()

    # Commit rejection to JobLedger (Phase 3)
    bc_fail = {"ok": False}
    if LEDGER_AVAILABLE:
        fail_data = json.dumps({
            "job_id": job_id, "step": step,
            "decision": "REJECTED",
            "ai_score": ms.ai_score,
            "freelancer_id": job.freelancer_id,
        }, sort_keys=True)
        bc_fail = ledger_commit_decision(
            job_id, step, False, 0,
            bytes.fromhex(_sha256_hex(fail_data)),
        )

    return {
        "ok": True, "step": step, "status": "failed",
        "message": "Freelancer can resubmit this milestone",
        "blockchain_penalty": penalty_result,
        "blockchain_decision": bc_fail,
    }


# ===================================================================
# BLOCKCHAIN VERIFICATION ENDPOINT
# ===================================================================

@router.get("/jobs/{job_id}/milestones/{step}/blockchain")
def get_milestone_blockchain_proof(
    job_id: int, step: int,
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the COMPLETE on-chain block for a milestone from JobLedger.
    Returns the full stored record + event data for all 4 phases.
    """
    db = current_user._db_session
    ms = db.query(Milestone).filter(
        Milestone.job_id == job_id, Milestone.step_number == step
    ).first()
    if not ms:
        raise HTTPException(status_code=404, detail="Milestone not found")

    job = db.query(Job).filter(Job.id == job_id).first()

    # Read from JobLedger contract
    onchain_job = None
    onchain_milestone = None
    if LEDGER_AVAILABLE:
        onchain_job = ledger_get_job(job_id)
        onchain_milestone = ledger_get_milestone(job_id, step)

    # Determine verification status per phase
    phases = {}
    if onchain_milestone:
        null_hash = "0x" + "00" * 32
        phases["requirements"] = {
            "committed": onchain_milestone.get("requirementsHash", null_hash) != null_hash,
            "hash": onchain_milestone.get("requirementsHash"),
            "timestamp": onchain_milestone.get("requirementsTimestamp"),
        }
        phases["submission"] = {
            "committed": onchain_milestone.get("submissionHash", null_hash) != null_hash,
            "hash": onchain_milestone.get("submissionHash"),
            "timestamp": onchain_milestone.get("submissionTimestamp"),
        }
        phases["ai_review"] = {
            "committed": onchain_milestone.get("aiHash", null_hash) != null_hash,
            "hash": onchain_milestone.get("aiHash"),
            "ai_score": onchain_milestone.get("aiScore"),
            "ai_pass": onchain_milestone.get("aiPass"),
            "timestamp": onchain_milestone.get("aiTimestamp"),
        }
        phases["decision"] = {
            "committed": onchain_milestone.get("decided", False),
            "approved": onchain_milestone.get("approved"),
            "payment": onchain_milestone.get("paymentAmount"),
            "hash": onchain_milestone.get("decisionHash"),
            "timestamp": onchain_milestone.get("decisionTimestamp"),
        }

    all_committed = all(p.get("committed", False) for p in phases.values()) if phases else False

    return {
        "job_id": job_id,
        "step": step,
        "milestone_title": ms.title,
        "status": ms.status.value,
        "all_phases_committed": all_committed,
        "onchain_job": onchain_job,
        "onchain_milestone": onchain_milestone,
        "phases": phases,
    }

# ===================================================================
# 4b. FRAUD MODEL INTEGRATION + WORKER PROFILE UPDATE
# ===================================================================

def _run_fraud_precheck(user: User, job: Job, db: Session) -> dict:
    """
    Quick FL fraud model check on an applicant before job assignment.
    Uses the freelancer's trust + confidence + historical fraud rate.
    """
    try:
        from main import fraud_model_weights, fraud_feature_dim
        from main import _dataset_mean, _dataset_std, _dataset_feature_cols
        import numpy as np

        if fraud_model_weights is None or fraud_feature_dim <= 0:
            return {"risk_score": 0.0, "verdict": "NO_MODEL"}

        d = int(fraud_feature_dim)
        HIDDEN = 32
        expected_mlp = d * HIDDEN + HIDDEN + HIDDEN + 1
        w = fraud_model_weights

        ws = _get_worker_score(db, user.id)
        fl_trust = user.trust_score or 100
        trust_ratio = min(fl_trust / 100.0, 1.2)
        confidence_ratio = ws.confidence_score / 100.0

        raw = np.zeros(d, dtype=float)
        feature_map = {
            "buyer_hire_rate_pct": trust_ratio * 70.0,
            "client_total_spent": job.budget * 5,
            "client_hires": max(1, user.total_jobs_completed or 0),
            "buyer_avgHourlyJobsRate_amount": job.budget / max(1, job.total_steps or 1),
            "fixed_budget_amount": job.budget / max(1, job.total_steps or 1),
            "client_rating": confidence_ratio * 5.0,
            "client_reviews": max(1, user.total_jobs_completed or 0),
            "phone_verified": 1.0 if trust_ratio > 0.6 else 0.0,
            "payment_verified": 1.0 if trust_ratio > 0.4 else 0.0,
            "isContractToHire": 0.0,
        }

        # Lower signals if user has fraud history
        if ws.fraud_flags and ws.fraud_flags > 0:
            feature_map["phone_verified"] = 0.0
            feature_map["buyer_hire_rate_pct"] *= 0.3

        for i, col in enumerate(_dataset_feature_cols or []):
            if i >= d:
                break
            raw[i] = feature_map.get(col, 0.0)

        if _dataset_mean is not None and _dataset_std is not None:
            x = (raw - _dataset_mean) / (_dataset_std + 1e-12)
        else:
            x = raw

        if len(w) == expected_mlp and len(x) == d:
            idx = 0
            W1 = w[idx:idx + d * HIDDEN].reshape(d, HIDDEN); idx += d * HIDDEN
            b1 = w[idx:idx + HIDDEN]; idx += HIDDEN
            W2 = w[idx:idx + HIDDEN].reshape(HIDDEN, 1); idx += HIDDEN
            b2 = w[idx:idx + 1]
            z1 = x @ W1 + b1
            a1 = np.maximum(0.0, z1)
            z2 = (a1 @ W2 + b2).item()
            risk_score = float(1.0 / (1.0 + np.exp(-z2)) if z2 >= 0 else np.exp(z2) / (1.0 + np.exp(z2)))
        else:
            risk_score = 0.3

        return {
            "risk_score": round(risk_score, 4),
            "verdict": "HIGH_RISK" if risk_score >= 0.7 else ("MEDIUM_RISK" if risk_score >= 0.5 else "LOW_RISK"),
            "model_type": "MLP_FL_precheck",
        }
    except Exception:
        return {"risk_score": 0.0, "verdict": "SKIP"}

def _run_fraud_model_on_submission(job: Job, milestone: Milestone, db: Session) -> dict:
    """
    Run the FL-trained MLP fraud model on the job submission metadata.
    This catches suspicious patterns: fake submissions, bot behavior, etc.

    Features are built from:
    - Freelancer's trust score + confidence score
    - Job metadata (budget, deadline adherence)
    - Submission timing patterns
    """
    try:
        # Import the fraud model from main.py
        from main import fraud_model_weights, fraud_feature_dim
        from main import _dataset_mean, _dataset_std, _dataset_feature_cols
        import numpy as np

        if fraud_model_weights is None or fraud_feature_dim <= 0:
            return {"risk_score": 0.0, "verdict": "NO_MODEL", "message": "Fraud model not loaded"}

        d = int(fraud_feature_dim)
        HIDDEN = 32
        expected_mlp = d * HIDDEN + HIDDEN + HIDDEN + 1
        w = fraud_model_weights

        # Build feature vector from job + milestone + freelancer data
        raw = np.zeros(d, dtype=float)

        # Map real job data to training feature positions
        freelancer = db.query(User).filter(User.id == job.freelancer_id).first() if job.freelancer_id else None
        fl_trust = 100
        fl_confidence = 50.0
        if freelancer:
            fl_trust = freelancer.trust_score or 100
            ws = _get_worker_score(db, freelancer.id)
            fl_confidence = ws.confidence_score

            if freelancer.wallet_address:
                try:
                    from blockchain_interface import contract
                    fl_trust = contract.functions.getTrust(freelancer.wallet_address).call()
                except Exception:
                    pass

        trust_ratio = min(fl_trust / 100.0, 1.2)
        confidence_ratio = fl_confidence / 100.0

        # Map features using dataset column names
        feature_map = {
            "buyer_hire_rate_pct": trust_ratio * 70.0,
            "client_total_spent": job.budget * 5,
            "client_hires": max(1, freelancer.total_jobs_completed or 0) if freelancer else 1,
            "buyer_avgHourlyJobsRate_amount": job.budget / max(1, job.total_steps),
            "fixed_budget_amount": milestone.payout_amount,
            "client_rating": confidence_ratio * 5.0,
            "client_reviews": max(1, freelancer.total_jobs_completed or 0) if freelancer else 1,
            "phone_verified": 1.0 if trust_ratio > 0.6 else 0.0,
            "payment_verified": 1.0 if trust_ratio > 0.4 else 0.0,
            "isContractToHire": 0.0,
        }

        # Deadline adherence signal
        if milestone.deadline_met is False:
            feature_map["phone_verified"] = 0.0
            feature_map["buyer_hire_rate_pct"] *= 0.5

        for i, col in enumerate(_dataset_feature_cols or []):
            if i >= d:
                break
            raw[i] = feature_map.get(col, 0.0)

        # Normalize using training stats
        if _dataset_mean is not None and _dataset_std is not None:
            x = (raw - _dataset_mean) / (_dataset_std + 1e-12)
        else:
            x = raw

        # MLP forward pass
        if len(w) == expected_mlp and len(x) == d:
            idx = 0
            W1 = w[idx:idx + d * HIDDEN].reshape(d, HIDDEN); idx += d * HIDDEN
            b1 = w[idx:idx + HIDDEN]; idx += HIDDEN
            W2 = w[idx:idx + HIDDEN].reshape(HIDDEN, 1); idx += HIDDEN
            b2 = w[idx:idx + 1]
            z1 = x @ W1 + b1
            a1 = np.maximum(0.0, z1)
            z2 = (a1 @ W2 + b2).item()
            risk_score = float(1.0 / (1.0 + np.exp(-z2)) if z2 >= 0 else np.exp(z2) / (1.0 + np.exp(z2)))
        else:
            risk_score = 0.3  # fallback

        verdict = "SUSPICIOUS" if risk_score >= 0.6 else "CLEAN"
        return {
            "risk_score": round(risk_score, 4),
            "verdict": verdict,
            "freelancer_trust": fl_trust,
            "freelancer_confidence": round(fl_confidence, 2),
            "deadline_met": milestone.deadline_met,
            "model_type": "MLP_FL_trained",
        }

    except Exception as e:
        return {"risk_score": 0.0, "verdict": "ERROR", "message": str(e)}


def _update_worker_profile_from_review(db: Session, user_id: int, milestone: Milestone, ai_score: float, passed: bool):
    """Update the freelancer's worker profile immediately after AI review, including fraud tracking."""
    ws = _get_worker_score(db, user_id)

    # Update running average quality score
    total_reviewed = ws.total_milestones_completed + ws.total_milestones_failed + 1
    ws.avg_quality_score = ((ws.avg_quality_score * (total_reviewed - 1)) + ai_score) / total_reviewed

    # Deadline adherence update
    if milestone.deadline_met is False:
        ws.total_milestones_late += 1

    # Track fraud signals from this review
    if milestone.ai_analysis:
        try:
            analysis = json.loads(milestone.ai_analysis)
            fraud_check = analysis.get("fraud_check", {})
            fraud_risk = fraud_check.get("risk_score", 0)
            if fraud_risk >= 0.6:
                ws.fraud_flags = (ws.fraud_flags or 0) + 1
            # Running avg of fraud risk
            ws.avg_fraud_risk = ((ws.avg_fraud_risk or 0) * (total_reviewed - 1) + fraud_risk) / total_reviewed
        except Exception:
            pass

    # Recompute confidence
    ws.confidence_score = _compute_confidence(ws)
    ws.last_updated = datetime.utcnow()


# ===================================================================
# 5. WORKER CONFIDENCE SCORE SYSTEM
# ===================================================================

def _update_worker_score_on_pass(db: Session, user_id: int, milestone: Milestone):
    ws = _get_worker_score(db, user_id)
    ws.total_milestones_completed += 1

    ai_score = milestone.ai_score or 50.0
    total = ws.total_milestones_completed
    ws.avg_quality_score = ((ws.avg_quality_score * (total - 1)) + ai_score) / total

    if milestone.deadline_met:
        ws.on_time_streak += 1
    else:
        ws.total_milestones_late += 1
        ws.on_time_streak = 0

    total_attempts = ws.total_milestones_completed + ws.total_milestones_failed
    on_time = total_attempts - ws.total_milestones_late
    ws.avg_deadline_adherence = on_time / total_attempts if total_attempts > 0 else 1.0

    ws.confidence_score = _compute_confidence(ws)
    ws.last_updated = datetime.utcnow()


def _update_worker_score_on_fail(db: Session, user_id: int, milestone: Milestone):
    ws = _get_worker_score(db, user_id)
    ws.total_milestones_failed += 1
    ws.on_time_streak = 0

    if not milestone.deadline_met:
        ws.total_milestones_late += 1

    total_attempts = ws.total_milestones_completed + ws.total_milestones_failed
    on_time = total_attempts - ws.total_milestones_late
    ws.avg_deadline_adherence = on_time / total_attempts if total_attempts > 0 else 1.0

    ws.confidence_score = _compute_confidence(ws)
    ws.last_updated = datetime.utcnow()


def _compute_confidence(ws: WorkerScore) -> float:
    """
    Confidence = weighted combination:
      30% avg quality score (0-100)
      25% deadline adherence (0-1 -> 0-100)
      20% client rating (0-5 -> 0-100)
      10% completion ratio
      10% streak bonus
      5% fraud signal (lower = better)
      minus dispute penalties
    """
    total = ws.total_milestones_completed + ws.total_milestones_failed
    if total == 0:
        return 50.0

    quality = min(ws.avg_quality_score, 100.0)
    deadline = ws.avg_deadline_adherence * 100.0
    rating = (ws.avg_client_rating / 5.0) * 100.0 if ws.avg_client_rating > 0 else 50.0
    completion_ratio = (ws.total_milestones_completed / total) * 100.0
    streak_bonus = min(ws.on_time_streak * 5, 100.0)
    dispute_penalty = min(ws.dispute_count * 10, 30.0)

    # Fraud penalty: higher avg_fraud_risk = lower confidence
    fraud_penalty = min((ws.avg_fraud_risk or 0) * 40, 20.0)  # max 20pt penalty
    fraud_flags_penalty = min((ws.fraud_flags or 0) * 8, 15.0)

    score = (0.30 * quality + 0.25 * deadline + 0.20 * rating +
             0.10 * completion_ratio + 0.10 * streak_bonus +
             0.05 * max(0, 100.0 - fraud_penalty * 5)
             - dispute_penalty - fraud_flags_penalty)

    return max(0.0, min(100.0, round(score, 2)))


@router.get("/worker/score/{user_id}")
def get_worker_score_endpoint(user_id: int, current_user: User = Depends(get_current_user)):
    db = current_user._db_session
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != UserRole.FREELANCER:
        raise HTTPException(status_code=404, detail="Freelancer not found")
    ws = _get_worker_score(db, user_id)

    u_trust = user.trust_score or 100
    unified = (0.40 * min(u_trust, 100) +
               0.35 * ws.confidence_score +
               0.25 * ws.avg_quality_score -
               min((ws.avg_fraud_risk or 0) * 30, 20))
    unified = max(0, min(100, round(unified, 2)))

    return {
        "user_id": user_id,
        "project_trust_score": unified,
        "blockchain_trust": u_trust,
        "confidence_score": round(ws.confidence_score, 2),
        "avg_quality_score": round(ws.avg_quality_score, 2),
        "avg_deadline_adherence": round(ws.avg_deadline_adherence, 2),
        "avg_client_rating": round(ws.avg_client_rating, 2),
        "total_milestones_completed": ws.total_milestones_completed,
        "total_milestones_failed": ws.total_milestones_failed,
        "total_milestones_late": ws.total_milestones_late,
        "on_time_streak": ws.on_time_streak,
        "dispute_count": ws.dispute_count,
        "fraud_flags": ws.fraud_flags or 0,
        "avg_fraud_risk": round(ws.avg_fraud_risk or 0, 4),
        "score_breakdown": {
            "blockchain_weight": "40%",
            "confidence_weight": "35%",
            "quality_weight": "25%",
            "formula": "40% blockchain + 35% confidence + 25% quality - fraud_penalty",
        },
    }


@router.get("/worker/{user_id}/milestone_history")
def get_milestone_history(user_id: int, current_user: User = Depends(get_current_user)):
    """Get a freelancer's complete milestone history with AI scores."""
    db = current_user._db_session
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all milestones where this user is the freelancer
    milestones = (
        db.query(Milestone)
        .join(Job, Milestone.job_id == Job.id)
        .filter(Job.freelancer_id == user_id)
        .order_by(Milestone.created_at.desc())
        .limit(50)
        .all()
    )

    history = []
    for m in milestones:
        job = db.query(Job).filter(Job.id == m.job_id).first()
        entry = {
            "milestone_id": m.id,
            "job_id": m.job_id,
            "job_title": job.title if job else "Unknown",
            "step": m.step_number,
            "title": m.title,
            "status": m.status.value,
            "ai_score": m.ai_score,
            "deadline_met": m.deadline_met,
            "payout": m.payout_amount,
            "payment_released": m.payment_released,
            "submitted_at": str(m.submitted_at) if m.submitted_at else None,
            "reviewed_at": str(m.ai_checked_at) if m.ai_checked_at else None,
        }
        # Extract fraud check from stored analysis
        if m.ai_analysis:
            try:
                analysis = json.loads(m.ai_analysis)
                entry["fraud_verdict"] = analysis.get("fraud_check", {}).get("verdict")
                entry["fraud_risk"] = analysis.get("fraud_check", {}).get("risk_score")
                entry["criteria_score"] = analysis.get("criteria_score")
                entry["code_quality"] = analysis.get("code_quality_score")
                entry["analysis_method"] = analysis.get("analysis_method")
            except Exception:
                pass
        history.append(entry)

    return {"user_id": user_id, "total": len(history), "milestones": history}


# ===================================================================
# 6. REVIEWS
# ===================================================================

@router.post("/jobs/{job_id}/review")
def submit_review(job_id: int, req: ReviewRequest, current_user: User = Depends(get_current_user)):
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.id not in (job.client_id, job.freelancer_id):
        raise HTTPException(status_code=403, detail="Only participants can review")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job must be completed before reviewing")
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    reviewee_id = job.freelancer_id if current_user.id == job.client_id else job.client_id

    existing = db.query(Review).filter(
        Review.job_id == job_id, Review.reviewer_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already reviewed this job")

    review = Review(
        job_id=job_id, reviewer_id=current_user.id,
        reviewee_id=reviewee_id, rating=req.rating, comment=req.comment,
    )
    db.add(review)

    if current_user.id == job.client_id and job.freelancer_id:
        ws = _get_worker_score(db, job.freelancer_id)
        all_reviews = db.query(Review).filter(Review.reviewee_id == job.freelancer_id).all()
        total_rating = sum(r.rating for r in all_reviews) + req.rating
        ws.avg_client_rating = total_rating / (len(all_reviews) + 1)
        ws.confidence_score = _compute_confidence(ws)

    db.commit()
    return {"ok": True, "message": "Review submitted"}


# ===================================================================
# 7. FREELANCER MATCHING
# ===================================================================

@router.post("/jobs/{job_id}/match_freelancers")
def match_freelancers(job_id: int, query: MatchQuery, current_user: User = Depends(get_current_user)):
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    q = db.query(User).filter(User.role == UserRole.FREELANCER)
    if query.min_trust > 0:
        q = q.filter(User.trust_score >= query.min_trust)
    freelancers = q.all()

    job_skills = set()
    if job.skills_required:
        job_skills = {s.strip().lower() for s in job.skills_required.split(",") if s.strip()}
    if query.skills:
        job_skills.update(s.strip().lower() for s in query.skills.split(",") if s.strip())

    ranked = []
    for fl in freelancers:
        fl_skills = set()
        if fl.skills:
            fl_skills = {s.strip().lower() for s in fl.skills.split(",") if s.strip()}
        skill_score = len(job_skills & fl_skills) / len(job_skills) if job_skills and fl_skills else (1.0 if not job_skills else 0.0)

        trust = fl.trust_score or 100
        ws = _get_worker_score(db, fl.id)
        confidence = ws.confidence_score

        composite = (0.30 * (trust / 120.0) + 0.30 * (confidence / 100.0) +
                     0.25 * skill_score + 0.15 * (ws.avg_client_rating / 5.0 if ws.avg_client_rating > 0 else 0.5))

        ranked.append({
            "freelancer_id": fl.id, "name": fl.name, "skills": fl.skills,
            "trust_score": trust, "trust_level": _trust_level(trust),
            "confidence_score": round(confidence, 2),
            "skill_match": round(skill_score, 2),
            "composite_score": round(composite, 4),
            "hourly_rate": fl.hourly_rate,
            "total_jobs_completed": fl.total_jobs_completed or 0,
        })

    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    return ranked[:min(query.limit, 100)]


# ===================================================================
# GITHUB + AI ANALYSIS ENGINE
# ===================================================================

def _fetch_latest_commit(repo_url: str) -> Optional[dict]:
    """Fetch latest commit SHA + timestamp from GitHub for deadline verification."""
    import requests as req_lib
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    try:
        resp = req_lib.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1",
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        commits = resp.json()
        if not commits:
            return None
        c = commits[0]
        date_str = c["commit"]["committer"]["date"]
        commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        return {"sha": c["sha"], "date": commit_date}
    except Exception:
        return None


def _fetch_github_repo_files(repo_url: str) -> dict:
    """Fetch code files from a public GitHub repo."""
    import requests as req_lib
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if not match:
        return {}
    owner, repo = match.group(1), match.group(2)

    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    resp = req_lib.get(api_url, timeout=30)
    if resp.status_code == 404:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
        resp = req_lib.get(api_url, timeout=30)
    if resp.status_code != 200:
        return {}

    tree = resp.json().get("tree", [])
    code_exts = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h",
        ".go", ".rs", ".rb", ".php", ".cs", ".sol", ".html", ".css",
        ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".sh", ".sql",
    }
    skip_patterns = ["node_modules/", "dist/", "build/", ".min.", "vendor/", "__pycache__/"]
    files = {}
    for item in tree:
        if item["type"] != "blob":
            continue
        path = item["path"]
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        if ext.lower() not in code_exts:
            continue
        if any(s in path for s in skip_patterns):
            continue
        if item.get("size", 0) > 500_000:
            continue
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
        raw_resp = req_lib.get(raw_url, timeout=15)
        if raw_resp.status_code == 404:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
            raw_resp = req_lib.get(raw_url, timeout=15)
        if raw_resp.status_code == 200:
            files[path] = raw_resp.text[:50_000]
        if len(files) >= 80:
            break
    return files


def _analyze_code_quality(
    files: dict,
    acceptance_criteria: str,
    milestone_description: str = "",
    job_description: str = "",
) -> dict:
    """
    Hybrid AI code quality analysis.
    - If GITHUB_TOKEN is set: uses LLM (GitHub Models GPT-4o) for deep semantic analysis
    - Fallback: rule-based static analysis (regex, pattern matching, heuristics)
    Both layers always run; LLM enriches the result when available.
    """
    all_text_lower = "\n".join(c.lower() for c in files.values())
    all_text = "\n".join(files.values())

    # --- 1. Acceptance Criteria Analysis (rule-based) ---
    criteria_items = _parse_criteria(acceptance_criteria)
    criteria_results = []
    total_criteria_score = 0.0

    for item in criteria_items:
        keywords = item["keywords"]
        patterns = item.get("patterns", [])

        found_kw = [kw for kw in keywords if kw.lower() in all_text_lower]
        kw_coverage = len(found_kw) / len(keywords) if keywords else 0

        pattern_found = 0
        pattern_evidence = []
        for pattern in patterns:
            for path, content in files.items():
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    pattern_found += 1
                    pattern_evidence.append(path)
                    break
        pattern_score = pattern_found / len(patterns) if patterns else kw_coverage

        score = 0.5 * kw_coverage + 0.5 * pattern_score
        total_criteria_score += score

        criteria_results.append({
            "criterion": item["text"],
            "score": round(score * 100, 1),
            "keywords_found": found_kw[:8],
            "keywords_missing": [k for k in keywords if k.lower() not in all_text_lower][:8],
            "evidence_files": pattern_evidence[:5],
            "status": "met" if score >= 0.7 else ("partial" if score >= 0.4 else "not_met"),
        })

    criteria_coverage = total_criteria_score / len(criteria_items) if criteria_items else 0

    # --- 2-6: Structure, Tests, Docs, Error handling, Complexity ---
    # These form the CODE QUALITY score (the 40% component)
    structure = _analyze_structure(files)
    test_score = _analyze_tests(files)
    doc_score = _analyze_documentation(files)
    error_handling_score = _analyze_error_handling(files)
    complexity_score = _analyze_complexity(files)

    # Code quality composite (0-100) — pure quality, no criteria
    code_quality_score = (
        0.30 * structure["score"] +
        0.25 * test_score +
        0.15 * doc_score +
        0.15 * error_handling_score +
        0.15 * complexity_score
    )

    # Overall = 60% criteria + 40% code quality (same weights as ai_review uses)
    static_overall = 0.60 * (criteria_coverage * 100) + 0.40 * code_quality_score

    # --- 7. LLM Deep Analysis (if GitHub token available) ---
    llm_analysis = None
    analysis_method = "static_analysis"
    overall_score = static_overall

    if LLM_ENABLED:
        llm_analysis = _llm_code_review(files, acceptance_criteria, milestone_description, job_description)
        if llm_analysis and llm_analysis.get("llm_score") is not None:
            analysis_method = "hybrid_llm_static"
            llm_score = llm_analysis["llm_score"]
            # Hybrid: 60% LLM + 40% static analysis
            overall_score = 0.60 * llm_score + 0.40 * static_overall

            # Enrich criteria results with LLM feedback
            llm_criteria = llm_analysis.get("criteria_feedback", [])
            for i, cr in enumerate(criteria_results):
                if i < len(llm_criteria):
                    cr["llm_feedback"] = llm_criteria[i].get("feedback", "")
                    cr["llm_met"] = llm_criteria[i].get("met", None)

    return {
        "overall_score": round(overall_score, 2),
        "analysis_method": analysis_method,
        "criteria_coverage": round(criteria_coverage, 3),
        "code_quality_score": round(code_quality_score, 2),
        "criteria_details": criteria_results,
        "structure": structure,
        "test_score": round(test_score, 2),
        "documentation_score": round(doc_score, 2),
        "error_handling_score": round(error_handling_score, 2),
        "complexity_score": round(complexity_score, 2),
        "static_score": round(static_overall, 2),
        "llm_analysis": llm_analysis,
        "file_count": len(files),
        "file_types": _count_file_types(files),
    }


# ===================================================================
# LLM-POWERED CODE REVIEW (GitHub Models API)
# ===================================================================

def _llm_code_review(
    files: dict,
    acceptance_criteria: str,
    milestone_description: str = "",
    job_description: str = "",
) -> Optional[dict]:
    """
    Use GitHub Models API (GPT-4o-mini) for deep semantic code review.
    Returns structured scores and per-criteria feedback.
    Falls back to None if token missing or API fails.
    """
    if not GITHUB_TOKEN:
        return None

    import requests as req_lib

    # Build a compact code summary (max ~12k chars to fit in context)
    code_summary = ""
    for path, content in sorted(files.items()):
        # Include first 150 lines of each file (enough for structure analysis)
        truncated = "\n".join(content.split("\n")[:150])
        code_summary += f"\n--- FILE: {path} ---\n{truncated}\n"
        if len(code_summary) > 12000:
            code_summary += "\n... (more files truncated) ..."
            break

    # Parse criteria into list for structured response
    criteria_list = [c.strip() for c in re.split(r"\n\d+[\.\)]\s*|\n[-*]\s+", acceptance_criteria) if c.strip()]
    if not criteria_list:
        criteria_list = [acceptance_criteria.strip()]

    criteria_json = json.dumps(criteria_list)

    prompt = f"""You are a senior code reviewer evaluating a freelancer's work submission.

## Job Description
{job_description[:500] if job_description else "N/A"}

## Milestone
{milestone_description[:300] if milestone_description else "N/A"}

## Acceptance Criteria
{acceptance_criteria}

## Code Submitted
{code_summary}

## Your Task
Evaluate the code against the acceptance criteria. Return a JSON object with:
1. "llm_score": Overall quality score 0-100
2. "summary": 2-3 sentence summary of code quality
3. "strengths": List of 2-3 things done well
4. "weaknesses": List of 2-3 things missing or poor
5. "criteria_feedback": Array (one per criterion) with {{"criterion": "...", "met": true/false, "feedback": "1 sentence"}}

Return ONLY valid JSON, no markdown formatting."""

    try:
        resp = req_lib.post(
            LLM_ENDPOINT,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a code quality reviewer. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 1500,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"LLM API error: {resp.status_code} {resp.text[:200]}")
            return None

        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content.strip())

        result = json.loads(content)

        # Validate score is in range
        if "llm_score" in result:
            result["llm_score"] = max(0, min(100, float(result["llm_score"])))

        result["model_used"] = LLM_MODEL
        return result

    except Exception as e:
        print(f"LLM review failed: {e}")
        return None


def _parse_criteria(text: str) -> list[dict]:
    """Parse acceptance criteria into items with keywords + code patterns."""
    lines = text.strip().split("\n")
    items = []
    current = ""
    for line in lines:
        line = line.strip()
        if not line:
            if current:
                items.append(current)
                current = ""
            continue
        if re.match(r"^(\d+[\.\)]\s|[-*]\s)", line):
            if current:
                items.append(current)
            current = re.sub(r"^(\d+[\.\)]\s|[-*]\s)", "", line).strip()
        else:
            current = (current + " " + line) if current else line
    if current:
        items.append(current)

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "have",
        "has", "had", "do", "does", "did", "will", "would", "could", "should",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "and", "but", "or", "not", "so", "yet", "both", "each", "every",
        "all", "any", "some", "no", "only", "than", "too", "very", "just",
        "if", "when", "where", "while", "how", "what", "which", "who",
        "this", "that", "these", "those", "it", "its", "they", "them",
        "we", "our", "you", "your", "he", "she", "up", "out", "also",
        "use", "using", "used", "implement", "make", "ensure", "must",
        "should", "need", "can", "may", "able", "into", "about", "more",
    }
    result = []
    for text_item in items:
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text_item.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        patterns = _generate_code_patterns(text_item, keywords)
        result.append({"text": text_item, "keywords": keywords, "patterns": patterns})
    return result


def _generate_code_patterns(criterion_text: str, keywords: list) -> list[str]:
    """Generate regex patterns that indicate actual code implementation."""
    patterns = []
    text_lower = criterion_text.lower()

    if any(w in text_lower for w in ["api", "endpoint", "route", "rest"]):
        patterns.append(r"(app\.(get|post|put|delete|patch)|@router\.|@app\.)")
    if any(w in text_lower for w in ["database", "db", "sql", "query", "table", "model"]):
        patterns.append(r"(CREATE TABLE|db\.query|\.filter\(|Column\(|ForeignKey)")
    if any(w in text_lower for w in ["auth", "login", "signup", "jwt", "token", "password"]):
        patterns.append(r"(jwt\.|token|password|authenticate|login|signup|bcrypt|hash_password)")
    if any(w in text_lower for w in ["test", "testing", "unit test", "spec"]):
        patterns.append(r"(def test_|it\(|describe\(|assert|expect\(|pytest|unittest)")
    if any(w in text_lower for w in ["frontend", "ui", "component", "page", "react", "vue"]):
        patterns.append(r"(function\s+\w+|const\s+\w+\s*=|export\s+default|useState|useEffect)")
    if any(w in text_lower for w in ["blockchain", "smart contract", "solidity", "web3"]):
        patterns.append(r"(contract\s+\w+|function\s+\w+.*public|web3\.|pragma\s+solidity)")
    if any(w in text_lower for w in ["error handling", "validation", "error", "exception"]):
        patterns.append(r"(try\s*[:{]|catch\s*\(|except\s|raise\s|throw\s|HTTPException)")

    for kw in keywords[:5]:
        if len(kw) >= 4:
            patterns.append(rf"(def\s+\w*{re.escape(kw)}|class\s+\w*{re.escape(kw)}|{re.escape(kw)}\s*[=(:])")

    return patterns


def _analyze_structure(files: dict) -> dict:
    total_files = len(files)
    if total_files == 0:
        return {"score": 0, "details": "No files found"}

    py_files = {p: c for p, c in files.items() if p.endswith(".py")}
    js_files = {p: c for p, c in files.items() if p.endswith((".js", ".jsx", ".ts", ".tsx"))}

    total_functions = 0
    total_classes = 0
    func_lengths = []

    for content in py_files.values():
        funcs = re.findall(r"^def \w+", content, re.MULTILINE)
        classes = re.findall(r"^class \w+", content, re.MULTILINE)
        total_functions += len(funcs)
        total_classes += len(classes)
        lines = content.split("\n")
        in_func = False
        func_len = 0
        for line in lines:
            if re.match(r"^def \w+", line):
                if in_func and func_len > 0:
                    func_lengths.append(func_len)
                in_func = True
                func_len = 0
            elif in_func:
                func_len += 1
        if in_func and func_len > 0:
            func_lengths.append(func_len)

    for content in js_files.values():
        funcs = re.findall(r"(function\s+\w+|const\s+\w+\s*=\s*(\(|async))", content)
        total_functions += len(funcs)

    avg_func_length = sum(func_lengths) / len(func_lengths) if func_lengths else 0

    modularity_score = 100.0
    if avg_func_length > 50:
        modularity_score -= min(30, (avg_func_length - 50) * 0.5)
    if total_functions < 3 and total_files > 3:
        modularity_score -= 20

    has_subdirs = any("/" in p for p in files)
    dir_score = 80.0 if has_subdirs else 60.0

    score = 0.6 * modularity_score + 0.4 * dir_score

    return {
        "score": round(score, 2),
        "total_functions": total_functions,
        "total_classes": total_classes,
        "avg_function_length": round(avg_func_length, 1),
        "has_subdirectories": has_subdirs,
    }


def _analyze_tests(files: dict) -> float:
    test_files = {p: c for p, c in files.items()
                  if "test" in p.lower() or "spec" in p.lower()}
    if not test_files:
        return 15.0

    total_test_funcs = 0
    for content in test_files.values():
        total_test_funcs += len(re.findall(r"(def test_|it\(|test\(|describe\()", content, re.IGNORECASE))

    has_assertions = any(
        re.search(r"(assert |expect\(|assertEqual|should\.|\.toBe|\.toEqual)", c, re.IGNORECASE)
        for c in test_files.values()
    )

    score = 40.0
    score += min(30.0, total_test_funcs * 5)
    if has_assertions:
        score += 20.0
    if len(test_files) >= 3:
        score += 10.0

    return min(100.0, score)


def _analyze_documentation(files: dict) -> float:
    score = 20.0
    readme_files = {p: c for p, c in files.items() if p.lower().startswith("readme")}
    if readme_files:
        readme_content = list(readme_files.values())[0]
        score += 25.0
        if len(readme_content) > 500:
            score += 15.0
        if any(h in readme_content for h in ["## ", "### ", "# "]):
            score += 10.0

    py_files = [c for p, c in files.items() if p.endswith(".py")]
    if py_files:
        total_docstrings = sum(c.count('"""') for c in py_files) // 2
        if total_docstrings >= 3:
            score += 15.0
        elif total_docstrings >= 1:
            score += 8.0

    js_files = [c for p, c in files.items() if p.endswith((".js", ".ts", ".jsx", ".tsx"))]
    if js_files:
        total_jsdoc = sum(c.count("/**") for c in js_files)
        if total_jsdoc >= 3:
            score += 15.0

    return min(100.0, score)


def _analyze_error_handling(files: dict) -> float:
    score = 30.0
    all_code = "\n".join(files.values())

    try_catch_count = len(re.findall(r"(try\s*[:{]|try:)", all_code))
    validation_count = len(re.findall(r"(raise\s|throw\s|HTTPException|ValueError|TypeError)", all_code))
    input_validation = len(re.findall(r"(if not\s|if\s+\w+\s+is\s+None|\.strip\(\)|\.validate)", all_code))

    if try_catch_count >= 3:
        score += 20.0
    elif try_catch_count >= 1:
        score += 10.0
    if validation_count >= 3:
        score += 20.0
    elif validation_count >= 1:
        score += 10.0
    if input_validation >= 2:
        score += 15.0

    bare_except = len(re.findall(r"except\s*:", all_code))
    if bare_except > 2:
        score -= 15.0

    return max(0.0, min(100.0, score))


def _analyze_complexity(files: dict) -> float:
    py_files = {p: c for p, c in files.items() if p.endswith(".py")}
    if not py_files:
        return 70.0

    total_nesting = 0
    long_functions = 0

    for content in py_files.values():
        lines = content.split("\n")
        max_indent = 0
        func_line_count = 0
        in_func = False
        for line in lines:
            stripped = line.lstrip()
            if not stripped:
                continue
            indent = len(line) - len(stripped)
            if indent > max_indent:
                max_indent = indent
            if re.match(r"def \w+", stripped):
                if in_func and func_line_count > 60:
                    long_functions += 1
                in_func = True
                func_line_count = 0
            elif in_func:
                func_line_count += 1
        if in_func and func_line_count > 60:
            long_functions += 1
        total_nesting += max_indent

    avg_nesting = total_nesting / len(py_files) if py_files else 0

    score = 90.0
    if avg_nesting > 20:
        score -= min(30, (avg_nesting - 20) * 1.5)
    if long_functions > 3:
        score -= min(20, long_functions * 5)

    return max(0.0, min(100.0, score))


def _count_file_types(files: dict) -> dict:
    types = {}
    for p in files:
        ext = "." + p.rsplit(".", 1)[-1] if "." in p else "other"
        types[ext] = types.get(ext, 0) + 1
    return types


# ===================================================================
# STANDALONE ANALYSIS ENDPOINT
# ===================================================================

class AnalyzeRepoRequest(BaseModel):
    github_repo_url: str
    acceptance_criteria: str


@router.post("/analyze/repo")
def analyze_repo_standalone(req: AnalyzeRepoRequest, current_user: User = Depends(get_current_user)):
    if not re.match(r"https?://github\.com/[^/]+/[^/]+", req.github_repo_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL")

    files = _fetch_github_repo_files(req.github_repo_url)
    if not files:
        raise HTTPException(status_code=400, detail="Could not fetch repo files")

    analysis = _analyze_code_quality(files, req.acceptance_criteria)
    return {"ok": True, "analysis": analysis}


# ===================================================================
# BLOCKCHAIN-VERIFIED RESUME / CREDENTIALS
# ===================================================================

@router.get("/user/resume")
def get_verified_resume(current_user: User = Depends(get_current_user)):
    """
    Generate a blockchain-verified resume for the freelancer.
    Every skill, project, and score is backed by on-chain proof.
    """
    if current_user.role != UserRole.FREELANCER:
        raise HTTPException(status_code=400, detail="Resume available for freelancers only")

    db = current_user._db_session
    ws = _get_worker_score(db, current_user.id)

    declared_skills = []
    if current_user.skills:
        declared_skills = [s.strip() for s in current_user.skills.split(",") if s.strip()]

    # Get all completed milestones with AI scores
    completed_milestones = (
        db.query(Milestone)
        .join(Job, Milestone.job_id == Job.id)
        .filter(Job.freelancer_id == current_user.id)
        .filter(Milestone.status == MilestoneStatus.PASSED)
        .order_by(Milestone.ai_checked_at.desc())
        .all()
    )

    # Build verified skills from actual project work
    verified_skills = {}
    projects = []
    for ms in completed_milestones:
        job = db.query(Job).filter(Job.id == ms.job_id).first()
        if not job:
            continue

        # Track skills used in real projects
        if job.skills_required:
            for skill in job.skills_required.split(","):
                skill = skill.strip().lower()
                if not skill:
                    continue
                if skill not in verified_skills:
                    verified_skills[skill] = {
                        "skill": skill,
                        "projects_count": 0,
                        "avg_score": 0,
                        "total_score": 0,
                        "verified": True,
                        "proof_hashes": [],
                    }
                verified_skills[skill]["projects_count"] += 1
                verified_skills[skill]["total_score"] += (ms.ai_score or 0)
                if ms.proof_hash:
                    verified_skills[skill]["proof_hashes"].append(ms.proof_hash[:16])

        # Check if this project is already tracked
        existing = next((p for p in projects if p["job_id"] == job.id), None)
        if not existing:
            projects.append({
                "job_id": job.id,
                "title": job.title,
                "description": job.description[:200] if job.description else "",
                "full_description": job.description or "",
                "requirements_text": job.requirements_text,
                "skills": job.skills_required,
                "budget": job.budget,
                "status": job.status.value,
                "milestones_completed": 0,
                "total_milestones": job.total_steps,
                "avg_ai_score": 0,
                "scores": [],
                "blockchain_verified": False,
                "milestone_titles": [],
                "acceptance_points": [],
                "github_repos": [],
                "proof_hashes": [],
                "timeline": {
                    "submitted_at": str(ms.submitted_at) if ms.submitted_at else None,
                    "reviewed_at": str(ms.ai_checked_at) if ms.ai_checked_at else None,
                },
            })
            existing = projects[-1]

        existing["milestones_completed"] += 1
        if ms.ai_score:
            existing["scores"].append(ms.ai_score)
        if ms.proof_hash:
            existing["blockchain_verified"] = True
            existing["proof_hashes"].append(ms.proof_hash)
        if ms.title and ms.title not in existing["milestone_titles"]:
            existing["milestone_titles"].append(ms.title)
        if ms.acceptance_criteria and len(existing["acceptance_points"]) < 4:
            existing["acceptance_points"].append(ms.acceptance_criteria)
        if ms.github_repo_url and ms.github_repo_url not in existing["github_repos"]:
            existing["github_repos"].append(ms.github_repo_url)

    # Compute averages
    for skill_data in verified_skills.values():
        if skill_data["projects_count"] > 0:
            skill_data["avg_score"] = round(skill_data["total_score"] / skill_data["projects_count"], 2)
        del skill_data["total_score"]
        skill_data["proof_hashes"] = skill_data["proof_hashes"][:3]

    for proj in projects:
        if proj["scores"]:
            proj["avg_ai_score"] = round(sum(proj["scores"]) / len(proj["scores"]), 2)
        del proj["scores"]
        proj["proof_hashes"] = proj["proof_hashes"][:3]
        proj["github_repos"] = proj["github_repos"][:2]

    # Get reviews
    reviews = db.query(Review).filter(Review.reviewee_id == current_user.id).all()
    review_summary = []
    for r in reviews:
        job = db.query(Job).filter(Job.id == r.job_id).first()
        reviewer = db.query(User).filter(User.id == r.reviewer_id).first()
        review_summary.append({
            "rating": r.rating,
            "comment": r.comment,
            "project": job.title if job else "Unknown",
            "from": reviewer.name if reviewer else "Anonymous",
            "date": str(r.created_at) if r.created_at else None,
        })

    # Trust score
    trust_score = current_user.trust_score or 100
    if current_user.wallet_address:
        try:
            from blockchain_interface import contract
            trust_score = contract.functions.getTrust(current_user.wallet_address).call()
        except Exception:
            pass

    # Compute unified project trust
    unified = (0.40 * min(trust_score, 100) +
               0.35 * ws.confidence_score +
               0.25 * ws.avg_quality_score -
               min((ws.avg_fraud_risk or 0) * 30, 20))
    unified = max(0, min(100, round(unified, 2)))

    verified_skill_list = sorted(
        verified_skills.values(),
        key=lambda x: x["avg_score"],
        reverse=True,
    )
    verified_skill_names = [skill["skill"] for skill in verified_skill_list]
    declared_only_skills = [skill for skill in declared_skills if skill.lower() not in verified_skill_names]

    primary_skills = verified_skill_names[:6] if verified_skill_names else declared_skills[:6]
    headline_parts = []
    if primary_skills:
        headline_parts.append(" | ".join(skill.title() for skill in primary_skills[:3]))
    if current_user.experience_years:
        headline_parts.append(f"{current_user.experience_years}+ years experience")
    if unified >= 80:
        headline_parts.append(f"{_trust_level(trust_score)} trust-tier contributor")
    professional_headline = " • ".join(headline_parts) if headline_parts else "Blockchain-verified freelancer profile"

    summary_lines = []
    if current_user.bio:
        summary_lines.append(current_user.bio.strip())
    if verified_skill_names:
        summary_lines.append(
            "Verified delivery across "
            + ", ".join(skill.title() for skill in verified_skill_names[:5])
            + " with milestone outcomes anchored on-chain."
        )
    elif declared_skills:
        summary_lines.append(
            "Profile skills include "
            + ", ".join(skill.title() for skill in declared_skills[:5])
            + ". Verified project evidence will accumulate automatically as milestones pass review."
        )
    else:
        summary_lines.append(
            "This freelancer profile is ready to accumulate project evidence, verified skills, and AI-reviewed delivery history on-chain."
        )
    summary_lines.append(
        f"Current trust profile: {unified}/100 project trust, {_trust_level(trust_score)} blockchain trust tier, "
        f"{ws.total_milestones_completed} passed milestones, and ${round(current_user.total_earnings or 0, 2)} verified earnings."
    )
    professional_summary = " ".join(summary_lines)

    achievement_items = [
        {
            "title": "Project Trust Score",
            "value": unified,
            "description": "Composite score derived from on-chain trust, AI quality, deadline adherence, and fraud risk.",
        },
        {
            "title": "Blockchain Trust",
            "value": trust_score,
            "description": "Wallet-linked trust value read from the TrustLayer contract.",
        },
        {
            "title": "Milestones Passed",
            "value": ws.total_milestones_completed,
            "description": "Approved milestone deliveries recorded through the platform workflow.",
        },
        {
            "title": "Client Rating",
            "value": round(ws.avg_client_rating, 2) if ws.avg_client_rating else 0,
            "description": "Average rating from submitted client reviews.",
        },
    ]

    experience_entries = []
    for proj in projects:
        experience_entries.append({
            "title": proj["title"],
            "role": "Freelancer Delivery",
            "description": proj["full_description"] or proj["description"],
            "highlights": proj["milestone_titles"] or ["Milestone delivery verified through AI review and blockchain proofs."],
            "acceptance_criteria": proj["acceptance_points"],
            "skills": [s.strip() for s in (proj.get("skills") or "").split(",") if s.strip()],
            "budget": proj["budget"],
            "avg_ai_score": proj["avg_ai_score"],
            "milestones_completed": proj["milestones_completed"],
            "total_milestones": proj["total_milestones"],
            "github_repos": proj["github_repos"],
            "proof_hashes": proj["proof_hashes"],
            "blockchain_verified": proj["blockchain_verified"],
            "timeline": proj["timeline"],
        })

    if not experience_entries:
        experience_entries.append({
            "title": "Freelancer Profile Initialized",
            "role": "Freelancer Delivery",
            "description": current_user.bio or "Profile has been prepared for blockchain-verified milestone delivery. The next approved project will appear here automatically.",
            "highlights": [
                "Wallet-backed trust profile is active.",
                "Resume hash can be committed on-chain for tamper-proof verification.",
                "Skills and projects will convert into verified experience after approved milestone reviews.",
            ],
            "acceptance_criteria": [],
            "skills": declared_skills,
            "budget": 0,
            "avg_ai_score": 0,
            "milestones_completed": ws.total_milestones_completed,
            "total_milestones": ws.total_milestones_completed,
            "github_repos": [],
            "proof_hashes": [],
            "blockchain_verified": bool(current_user.wallet_address),
            "timeline": {"submitted_at": None, "reviewed_at": None},
        })

    # Generate resume hash for blockchain verification
    resume_data = json.dumps({
        "user_id": current_user.id,
        "name": current_user.name,
        "trust_score": trust_score,
        "confidence": ws.confidence_score,
        "quality_avg": ws.avg_quality_score,
        "milestones_completed": ws.total_milestones_completed,
        "skills": list(verified_skills.keys()),
        "projects": len(projects),
    }, sort_keys=True)
    resume_hash = hashlib.sha256(resume_data.encode()).hexdigest()

    # Commit resume hash on-chain for verification
    bc_result = None
    if LEDGER_AVAILABLE:
        try:
            bc_result = ledger_commit_requirements(
                0, current_user.id,  # job_id=0, step=user_id for resume
                f"Resume:{current_user.name}",
                json.dumps(list(verified_skills.keys())),
                unified, 0,
                bytes.fromhex(resume_hash),
            )
        except Exception:
            pass

    return {
        "resume": {
            "name": current_user.name,
            "email": current_user.email,
            "role": "Freelancer",
            "headline": professional_headline,
            "bio": current_user.bio,
            "github": current_user.github_username,
            "portfolio": current_user.portfolio_url,
            "hourly_rate": current_user.hourly_rate,
            "experience_years": current_user.experience_years,
            "member_since": str(current_user.created_at) if current_user.created_at else None,
        },
        "summary": {
            "professional_summary": professional_summary,
            "key_strengths": [
                f"{_trust_level(trust_score)} blockchain trust tier",
                f"{round(ws.confidence_score, 2)} confidence score",
                f"{ws.total_milestones_completed} milestone approvals",
                f"{len(verified_skill_names)} verified skills",
            ],
        },
        "trust": {
            "project_trust_score": unified,
            "blockchain_trust": trust_score,
            "trust_level": _trust_level(trust_score),
            "confidence_score": round(ws.confidence_score, 2),
            "avg_quality_score": round(ws.avg_quality_score, 2),
            "avg_deadline_adherence": round(ws.avg_deadline_adherence, 2),
            "on_time_streak": ws.on_time_streak,
            "fraud_flags": ws.fraud_flags or 0,
        },
        "stats": {
            "total_jobs_completed": current_user.total_jobs_completed or 0,
            "total_milestones_passed": ws.total_milestones_completed,
            "total_milestones_failed": ws.total_milestones_failed,
            "total_earnings": current_user.total_earnings or 0,
            "avg_client_rating": round(ws.avg_client_rating, 2) if ws.avg_client_rating else 0,
            "total_reviews": len(reviews),
        },
        "verified_skills": verified_skill_list,
        "declared_skills": declared_skills,
        "declared_only_skills": declared_only_skills,
        "competencies": {
            "primary": primary_skills,
            "verified": verified_skill_names,
            "declared": declared_skills,
        },
        "projects": projects,
        "experience": experience_entries,
        "achievements": achievement_items,
        "reviews": review_summary[:10],
        "verification": {
            "resume_hash": "0x" + resume_hash,
            "blockchain_committed": bc_result.get("ok", False) if bc_result else False,
            "blockchain_tx": bc_result.get("tx") if bc_result else None,
            "wallet_address": current_user.wallet_address,
            "message": "This resume is cryptographically verified. All skills and projects are backed by on-chain proof from completed milestone reviews.",
        },
    }


@router.get("/user/resume/{user_id}")
def get_public_resume(user_id: int, current_user: User = Depends(get_current_user)):
    """Public view of a freelancer's verified resume (no sensitive data)."""
    db = current_user._db_session
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != UserRole.FREELANCER:
        raise HTTPException(status_code=404, detail="Freelancer not found")

    ws = _get_worker_score(db, user.id)

    # Get completed milestones
    completed = (
        db.query(Milestone)
        .join(Job, Milestone.job_id == Job.id)
        .filter(Job.freelancer_id == user.id, Milestone.status == MilestoneStatus.PASSED)
        .all()
    )

    # Build verified skills
    verified_skills = {}
    project_titles = []
    for ms in completed:
        job = db.query(Job).filter(Job.id == ms.job_id).first()
        if not job:
            continue
        if job.title not in project_titles:
            project_titles.append(job.title)
        if job.skills_required:
            for skill in job.skills_required.split(","):
                skill = skill.strip().lower()
                if skill and skill not in verified_skills:
                    verified_skills[skill] = {"skill": skill, "verified": True, "projects": 0, "avg_score": 0, "scores": []}
                if skill in verified_skills:
                    verified_skills[skill]["projects"] += 1
                    if ms.ai_score:
                        verified_skills[skill]["scores"].append(ms.ai_score)

    for s in verified_skills.values():
        if s["scores"]:
            s["avg_score"] = round(sum(s["scores"]) / len(s["scores"]), 2)
        del s["scores"]

    trust = user.trust_score or 100
    unified = (0.40 * min(trust, 100) + 0.35 * ws.confidence_score +
               0.25 * ws.avg_quality_score - min((ws.avg_fraud_risk or 0) * 30, 20))
    unified = max(0, min(100, round(unified, 2)))

    reviews = db.query(Review).filter(Review.reviewee_id == user.id).all()

    return {
        "name": user.name,
        "bio": user.bio,
        "github": user.github_username,
        "experience_years": user.experience_years,
        "project_trust_score": unified,
        "trust_level": _trust_level(trust),
        "confidence_score": round(ws.confidence_score, 2),
        "total_jobs": user.total_jobs_completed or 0,
        "total_milestones": ws.total_milestones_completed,
        "avg_quality": round(ws.avg_quality_score, 2),
        "avg_rating": round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0,
        "on_time_streak": ws.on_time_streak,
        "verified_skills": sorted(verified_skills.values(), key=lambda x: x["avg_score"], reverse=True),
        "projects": project_titles[:20],
        "blockchain_verified": user.wallet_address is not None,
        "wallet": user.wallet_address,
    }
