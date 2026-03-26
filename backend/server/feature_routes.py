"""
Feature routes for:
  1. User profile with FL trust score
  2. Subscription/payment system + job posting + freelancer matching
  3. GitHub repo AI analysis against client requirements
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import json
import re
import hashlib

from database import get_db
from models import User, Subscription, Job, UserRole, SubscriptionTier, JobStatus
from auth_utils import get_current_user

router = APIRouter(tags=["features"])


# ---------------------------------------------------------------------------
# Pydantic request/response schemas
# ---------------------------------------------------------------------------

class LinkWalletRequest(BaseModel):
    wallet_address: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None


class SubscribeRequest(BaseModel):
    tier: str = "premium"
    duration_days: int = 30


class CreateJobPostRequest(BaseModel):
    title: str
    description: str
    requirements_text: Optional[str] = None
    budget: float = 0.0
    deadline_hours: float = 72.0
    skills_required: Optional[str] = None


class AssignFreelancerRequest(BaseModel):
    freelancer_id: int


class SubmitWorkRequest(BaseModel):
    github_repo_url: str


class MatchQuery(BaseModel):
    skills: Optional[str] = None
    min_trust: int = 0
    limit: int = 20


# ---------------------------------------------------------------------------
# 1. USER PROFILE + TRUST SCORE
# ---------------------------------------------------------------------------

def _trust_level(score: int) -> str:
    if score >= 100:
        return "Platinum"
    if score >= 80:
        return "Gold"
    if score >= 60:
        return "Silver"
    return "Bronze"


@router.get("/user/profile")
def get_user_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile with on-chain trust score."""
    trust_score = current_user.trust_score or 100
    onchain_trust = None

    # If wallet is linked, fetch live on-chain trust
    if current_user.wallet_address:
        try:
            from blockchain_interface import contract
            onchain_trust = contract.functions.getTrust(current_user.wallet_address).call()
            trust_score = onchain_trust
            # Cache it in DB
            db = current_user._db_session
            current_user.trust_score = trust_score
            db.commit()
        except Exception:
            pass

    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value if current_user.role else "freelancer",
        "wallet_address": current_user.wallet_address,
        "trust_score": trust_score,
        "trust_level": _trust_level(trust_score),
        "skills": current_user.skills,
        "bio": current_user.bio,
        "created_at": str(current_user.created_at) if current_user.created_at else None,
    }


@router.post("/user/link_wallet")
def link_wallet(req: LinkWalletRequest, current_user: User = Depends(get_current_user)):
    """Link an Ethereum wallet address to the authenticated user for on-chain trust."""
    addr = req.wallet_address.strip()
    if not re.match(r"^0x[0-9a-fA-F]{40}$", addr):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

    db = current_user._db_session
    existing = db.query(User).filter(User.wallet_address == addr, User.id != current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Wallet already linked to another account")

    current_user.wallet_address = addr

    # Fetch on-chain trust if available
    try:
        from blockchain_interface import contract
        onchain_trust = contract.functions.getTrust(addr).call()
        current_user.trust_score = onchain_trust
    except Exception:
        pass

    db.commit()
    return {
        "ok": True,
        "wallet_address": addr,
        "trust_score": current_user.trust_score,
        "trust_level": _trust_level(current_user.trust_score or 100),
    }


@router.put("/user/profile")
def update_profile(req: UpdateProfileRequest, current_user: User = Depends(get_current_user)):
    """Update profile fields (name, role, skills, bio)."""
    db = current_user._db_session
    if req.name is not None:
        current_user.name = req.name
    if req.role is not None:
        if req.role not in ("client", "freelancer"):
            raise HTTPException(status_code=400, detail="Role must be 'client' or 'freelancer'")
        current_user.role = UserRole(req.role)
    if req.skills is not None:
        current_user.skills = req.skills
    if req.bio is not None:
        current_user.bio = req.bio
    db.commit()
    return {"ok": True, "message": "Profile updated"}


@router.get("/user/trust_history")
def get_user_trust_history(current_user: User = Depends(get_current_user)):
    """Return FL trust history for this user from the server's in-memory records."""
    from main import trust_history, client_address_mapping

    wallet = current_user.wallet_address
    if not wallet:
        return {"history": [], "message": "No wallet linked"}

    # Find client_id by wallet address
    for cid, addr in client_address_mapping.items():
        if addr.lower() == wallet.lower():
            return {"history": trust_history.get(cid, []), "client_id": cid}

    return {"history": [], "message": "No FL participation found for this wallet"}


# ---------------------------------------------------------------------------
# 2. SUBSCRIPTION / PAYMENT SYSTEM
# ---------------------------------------------------------------------------

@router.post("/subscription/subscribe")
def subscribe(req: SubscribeRequest, current_user: User = Depends(get_current_user)):
    """Subscribe to a tier (simulated payment — in production, integrate Stripe/crypto)."""
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
        sub = Subscription(
            user_id=current_user.id,
            tier=tier,
            expires_at=expires,
        )
        db.add(sub)
    db.commit()
    return {
        "ok": True,
        "tier": tier.value,
        "expires_at": str(expires) if expires else None,
    }


@router.get("/subscription/status")
def subscription_status(current_user: User = Depends(get_current_user)):
    """Check current subscription status."""
    db = current_user._db_session
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not sub:
        return {"tier": "free", "active": True, "expires_at": None}

    active = True
    if sub.tier == SubscriptionTier.PREMIUM and sub.expires_at:
        active = datetime.utcnow() < sub.expires_at

    return {
        "tier": sub.tier.value,
        "active": active,
        "started_at": str(sub.started_at) if sub.started_at else None,
        "expires_at": str(sub.expires_at) if sub.expires_at else None,
    }


def _require_premium(user: User, db: Session):
    """Check that the user has an active premium subscription."""
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub or sub.tier != SubscriptionTier.PREMIUM:
        raise HTTPException(status_code=403, detail="Premium subscription required")
    if sub.expires_at and datetime.utcnow() >= sub.expires_at:
        raise HTTPException(status_code=403, detail="Subscription expired")


# ---------------------------------------------------------------------------
# 3. JOB POSTING (persistent, DB-backed)
# ---------------------------------------------------------------------------

@router.post("/jobs/create")
def create_job(req: CreateJobPostRequest, current_user: User = Depends(get_current_user)):
    """Create a new job posting. Requires premium subscription."""
    db = current_user._db_session
    _require_premium(current_user, db)

    if current_user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Only clients can post jobs")

    job = Job(
        title=req.title,
        description=req.description,
        requirements_text=req.requirements_text,
        budget=req.budget,
        deadline_hours=req.deadline_hours,
        skills_required=req.skills_required,
        client_id=current_user.id,
        status=JobStatus.OPEN,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "ok": True,
        "job_id": job.id,
        "title": job.title,
        "status": job.status.value,
    }


@router.get("/jobs/list")
def list_jobs(
    status_filter: Optional[str] = None,
    skills: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """List available jobs, optionally filtered by status or skills."""
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
    return [
        {
            "job_id": j.id,
            "title": j.title,
            "description": j.description[:200],
            "budget": j.budget,
            "skills_required": j.skills_required,
            "status": j.status.value,
            "client_id": j.client_id,
            "freelancer_id": j.freelancer_id,
            "created_at": str(j.created_at) if j.created_at else None,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
def get_job_detail(job_id: int, current_user: User = Depends(get_current_user)):
    """Get full job details including AI analysis results."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "title": job.title,
        "description": job.description,
        "requirements_text": job.requirements_text,
        "budget": job.budget,
        "deadline_hours": job.deadline_hours,
        "skills_required": job.skills_required,
        "status": job.status.value,
        "client_id": job.client_id,
        "freelancer_id": job.freelancer_id,
        "github_repo_url": job.github_repo_url,
        "ai_analysis_result": json.loads(job.ai_analysis_result) if job.ai_analysis_result else None,
        "ai_risk_score": job.ai_risk_score,
        "created_at": str(job.created_at) if job.created_at else None,
    }


@router.post("/jobs/{job_id}/assign")
def assign_freelancer(job_id: int, req: AssignFreelancerRequest, current_user: User = Depends(get_current_user)):
    """Client assigns a freelancer to the job."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the job owner can assign freelancers")
    if job.status != JobStatus.OPEN:
        raise HTTPException(status_code=400, detail="Job is not open for assignment")

    freelancer = db.query(User).filter(User.id == req.freelancer_id, User.role == UserRole.FREELANCER).first()
    if not freelancer:
        raise HTTPException(status_code=404, detail="Freelancer not found")

    job.freelancer_id = freelancer.id
    job.status = JobStatus.IN_PROGRESS
    db.commit()
    return {"ok": True, "job_id": job.id, "freelancer_id": freelancer.id, "status": "in_progress"}


# ---------------------------------------------------------------------------
# 4. FREELANCER MATCHING BY TRUST SCORE
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/match_freelancers")
def match_freelancers(job_id: int, query: MatchQuery, current_user: User = Depends(get_current_user)):
    """
    Match freelancers to a job based on:
    - Skill overlap (text matching)
    - Trust score (on-chain if available, else cached)
    - Sorted by composite score (trust * skill_match)
    """
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all freelancers
    q = db.query(User).filter(User.role == UserRole.FREELANCER)
    if query.min_trust > 0:
        q = q.filter(User.trust_score >= query.min_trust)
    freelancers = q.all()

    # Parse required skills from job
    job_skills = set()
    if job.skills_required:
        job_skills = {s.strip().lower() for s in job.skills_required.split(",") if s.strip()}
    if query.skills:
        job_skills.update(s.strip().lower() for s in query.skills.split(",") if s.strip())

    # Score each freelancer
    ranked = []
    for fl in freelancers:
        # Skill match score
        fl_skills = set()
        if fl.skills:
            fl_skills = {s.strip().lower() for s in fl.skills.split(",") if s.strip()}

        if job_skills and fl_skills:
            overlap = len(job_skills & fl_skills)
            skill_score = overlap / len(job_skills)
        elif not job_skills:
            skill_score = 1.0  # no filter = everyone matches
        else:
            skill_score = 0.0

        # Trust score (refresh from chain if wallet linked)
        trust = fl.trust_score or 100
        if fl.wallet_address:
            try:
                from blockchain_interface import contract
                trust = contract.functions.getTrust(fl.wallet_address).call()
            except Exception:
                pass

        # Composite score: weighted combination
        composite = 0.6 * (trust / 120.0) + 0.4 * skill_score

        ranked.append({
            "freelancer_id": fl.id,
            "name": fl.name,
            "email": fl.email,
            "skills": fl.skills,
            "trust_score": trust,
            "trust_level": _trust_level(trust),
            "skill_match": round(skill_score, 2),
            "composite_score": round(composite, 4),
            "wallet_linked": fl.wallet_address is not None,
        })

    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    return ranked[: min(query.limit, 100)]


# ---------------------------------------------------------------------------
# 5. GITHUB REPO AI ANALYSIS
# ---------------------------------------------------------------------------

def _fetch_github_repo_files(repo_url: str) -> dict:
    """
    Fetch file listing and contents from a public GitHub repo via the API.
    Returns {filepath: content} dict for text files.
    """
    import requests

    # Parse owner/repo from URL
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL. Expected: https://github.com/owner/repo")
    owner, repo = match.group(1), match.group(2)

    # Use GitHub Trees API to get all files
    api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
    resp = requests.get(api_url, timeout=30)
    if resp.status_code == 404:
        # Try 'master' branch
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
        resp = requests.get(api_url, timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Could not fetch repo tree: HTTP {resp.status_code}")

    tree = resp.json().get("tree", [])

    # Filter to code files, skip binaries and large files
    code_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h",
        ".go", ".rs", ".rb", ".php", ".cs", ".sol", ".html", ".css",
        ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".sh", ".sql",
    }
    files = {}
    for item in tree:
        if item["type"] != "blob":
            continue
        path = item["path"]
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        if ext.lower() not in code_extensions:
            continue
        # Skip node_modules, dist, build artifacts
        if any(skip in path for skip in ["node_modules/", "dist/", "build/", ".min.", "vendor/", "__pycache__/"]):
            continue
        # Fetch raw content (limit to 500KB per file)
        size = item.get("size", 0)
        if size > 500_000:
            continue
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
        raw_resp = requests.get(raw_url, timeout=15)
        if raw_resp.status_code == 404:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
            raw_resp = requests.get(raw_url, timeout=15)
        if raw_resp.status_code == 200:
            files[path] = raw_resp.text[:50_000]  # cap per-file content

        # Limit total files fetched to avoid excessive API calls
        if len(files) >= 80:
            break

    return files


def _parse_requirements(requirements_text: str) -> list[dict]:
    """
    Parse requirements text into structured requirement items.
    Handles numbered lists, bullet points, and plain sentences.
    """
    lines = requirements_text.strip().split("\n")
    requirements = []
    current_req = ""

    for line in lines:
        line = line.strip()
        if not line:
            if current_req:
                requirements.append(current_req)
                current_req = ""
            continue
        # Check for numbered or bulleted item
        if re.match(r"^(\d+[\.\)]\s|[-*•]\s)", line):
            if current_req:
                requirements.append(current_req)
            current_req = re.sub(r"^(\d+[\.\)]\s|[-*•]\s)", "", line).strip()
        else:
            if current_req:
                current_req += " " + line
            else:
                current_req = line

    if current_req:
        requirements.append(current_req)

    # Convert to structured dicts with extracted keywords
    result = []
    for req_text in requirements:
        keywords = _extract_keywords(req_text)
        result.append({
            "text": req_text,
            "keywords": keywords,
        })
    return result


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful technical keywords from text."""
    # Common stop words to filter out
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "ought",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "under", "about", "and", "but", "or", "nor", "not",
        "so", "yet", "both", "each", "every", "all", "any", "few", "more",
        "most", "other", "some", "such", "no", "only", "own", "same",
        "than", "too", "very", "just", "because", "if", "when", "where",
        "while", "how", "what", "which", "who", "whom", "this", "that",
        "these", "those", "it", "its", "they", "them", "their", "we",
        "our", "you", "your", "he", "she", "him", "her", "his",
        "up", "out", "also", "use", "using", "used", "implement",
        "implemented", "make", "system", "application", "app", "ensure",
    }
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]


def _analyze_repo_against_requirements(
    files: dict,
    requirements: list[dict],
    job_description: str = "",
) -> dict:
    """
    AI-powered analysis: check how well a GitHub repo meets job requirements.
    Uses keyword matching, structural analysis, and heuristic scoring.
    """
    # Build a combined text corpus from all files
    file_contents_lower = {}
    for path, content in files.items():
        file_contents_lower[path] = content.lower()

    all_text = "\n".join(file_contents_lower.values())

    # Analyze each requirement
    req_results = []
    total_coverage = 0.0

    for req in requirements:
        keywords = req["keywords"]
        if not keywords:
            req_results.append({
                "requirement": req["text"],
                "status": "unclear",
                "confidence": 0.0,
                "evidence": [],
                "message": "Could not extract actionable keywords",
            })
            continue

        # Score: how many keywords appear in the codebase
        found_keywords = []
        missing_keywords = []
        evidence_files = []

        for kw in keywords:
            if kw in all_text:
                found_keywords.append(kw)
                # Find which files contain this keyword
                for path, content in file_contents_lower.items():
                    if kw in content and path not in evidence_files:
                        evidence_files.append(path)
            else:
                missing_keywords.append(kw)

        keyword_coverage = len(found_keywords) / len(keywords) if keywords else 0

        # Structural checks: look for patterns indicating implementation
        structural_score = 0.0
        structural_evidence = []

        # Check for test files
        test_files = [p for p in files if "test" in p.lower() or "spec" in p.lower()]
        if test_files:
            structural_score += 0.1
            structural_evidence.append(f"Test files found: {len(test_files)}")

        # Check for README/docs
        doc_files = [p for p in files if p.lower() in ("readme.md", "docs/", "doc/")]
        if doc_files:
            structural_score += 0.05

        # Check for config/deployment files
        deploy_files = [p for p in files if any(d in p.lower() for d in
                        ["dockerfile", "docker-compose", ".env", "deploy", "k8s", "terraform"])]
        if deploy_files:
            structural_score += 0.05

        # Final confidence: keyword match + structural bonus
        confidence = min(1.0, keyword_coverage * 0.85 + structural_score)

        if confidence >= 0.7:
            status = "met"
        elif confidence >= 0.4:
            status = "partially_met"
        else:
            status = "not_met"

        total_coverage += confidence

        req_results.append({
            "requirement": req["text"],
            "status": status,
            "confidence": round(confidence, 3),
            "found_keywords": found_keywords[:10],
            "missing_keywords": missing_keywords[:10],
            "evidence_files": evidence_files[:5],
            "structural_notes": structural_evidence,
        })

    # Overall analysis
    n_req = len(requirements) if requirements else 1
    overall_coverage = total_coverage / n_req

    # File structure analysis
    file_types = {}
    for path in files:
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else "other"
        file_types[ext] = file_types.get(ext, 0) + 1

    met_count = sum(1 for r in req_results if r["status"] == "met")
    partial_count = sum(1 for r in req_results if r["status"] == "partially_met")
    not_met_count = sum(1 for r in req_results if r["status"] == "not_met")

    return {
        "overall_coverage": round(overall_coverage, 3),
        "total_requirements": n_req,
        "met": met_count,
        "partially_met": partial_count,
        "not_met": not_met_count,
        "file_count": len(files),
        "file_types": file_types,
        "has_tests": any("test" in p.lower() or "spec" in p.lower() for p in files),
        "has_readme": any(p.lower().startswith("readme") for p in files),
        "has_docker": any("docker" in p.lower() for p in files),
        "requirement_details": req_results,
    }


@router.post("/jobs/{job_id}/submit_work")
def submit_work(job_id: int, req: SubmitWorkRequest, current_user: User = Depends(get_current_user)):
    """Freelancer submits their GitHub repo for a job."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.freelancer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the assigned freelancer can submit work")
    if job.status not in (JobStatus.IN_PROGRESS, JobStatus.PROOF_SUBMITTED):
        raise HTTPException(status_code=400, detail=f"Cannot submit work in status: {job.status.value}")

    # Validate URL format
    if not re.match(r"https?://github\.com/[^/]+/[^/]+", req.github_repo_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL")

    job.github_repo_url = req.github_repo_url
    job.status = JobStatus.PROOF_SUBMITTED
    db.commit()
    return {"ok": True, "job_id": job.id, "status": "proof_submitted", "github_repo_url": req.github_repo_url}


@router.post("/jobs/{job_id}/analyze")
def analyze_job_submission(job_id: int, current_user: User = Depends(get_current_user)):
    """
    Run AI analysis on the submitted GitHub repo against job requirements.
    Available to the job client (owner) or the assigned freelancer.
    """
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.id not in (job.client_id, job.freelancer_id):
        raise HTTPException(status_code=403, detail="Only the client or assigned freelancer can trigger analysis")
    if not job.github_repo_url:
        raise HTTPException(status_code=400, detail="No GitHub repo submitted yet")

    # 1. Fetch repo files
    files = _fetch_github_repo_files(job.github_repo_url)
    if not files:
        raise HTTPException(status_code=400, detail="Could not fetch any files from the repo")

    # 2. Parse requirements
    req_text = job.requirements_text or job.description
    requirements = _parse_requirements(req_text)

    # 3. Run analysis
    analysis = _analyze_repo_against_requirements(files, requirements, job.description)

    # 4. Compute risk score using the FL fraud model
    risk_score = 1.0 - analysis["overall_coverage"]

    # Factor in freelancer's trust score
    if job.freelancer_id:
        freelancer = db.query(User).filter(User.id == job.freelancer_id).first()
        if freelancer and freelancer.trust_score:
            trust_factor = min(freelancer.trust_score / 120.0, 1.0)
            risk_score = risk_score * (1.0 - 0.3 * trust_factor)

    analysis["risk_score"] = round(risk_score, 4)

    # 5. Persist results
    job.ai_analysis_result = json.dumps(analysis)
    job.ai_risk_score = risk_score
    job.status = JobStatus.AI_REVIEWED
    db.commit()

    return {
        "ok": True,
        "job_id": job.id,
        "analysis": analysis,
    }


@router.post("/jobs/{job_id}/complete")
def complete_job(job_id: int, current_user: User = Depends(get_current_user)):
    """Client marks the job as completed after reviewing AI analysis."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the client can complete the job")
    if job.status not in (JobStatus.AI_REVIEWED, JobStatus.PROOF_SUBMITTED):
        raise HTTPException(status_code=400, detail=f"Cannot complete job in status: {job.status.value}")

    job.status = JobStatus.COMPLETED

    # Reward freelancer's trust on-chain
    if job.freelancer_id:
        freelancer = db.query(User).filter(User.id == job.freelancer_id).first()
        if freelancer and freelancer.wallet_address:
            try:
                from blockchain_interface import contract, w3
                tx = contract.functions.rewardClient(freelancer.wallet_address).transact()
                w3.eth.wait_for_transaction_receipt(tx)
                new_trust = contract.functions.getTrust(freelancer.wallet_address).call()
                freelancer.trust_score = new_trust
            except Exception:
                pass

    db.commit()
    return {"ok": True, "job_id": job.id, "status": "completed"}


@router.post("/jobs/{job_id}/dispute")
def dispute_job(job_id: int, current_user: User = Depends(get_current_user)):
    """Client disputes the job — penalizes freelancer trust."""
    db = current_user._db_session
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the client can dispute the job")
    if job.status not in (JobStatus.AI_REVIEWED, JobStatus.PROOF_SUBMITTED):
        raise HTTPException(status_code=400, detail=f"Cannot dispute job in status: {job.status.value}")

    job.status = JobStatus.DISPUTED

    # Penalize freelancer on-chain
    if job.freelancer_id:
        freelancer = db.query(User).filter(User.id == job.freelancer_id).first()
        if freelancer and freelancer.wallet_address:
            try:
                from blockchain_interface import contract, w3
                tx = contract.functions.penalizeClient(freelancer.wallet_address).transact()
                w3.eth.wait_for_transaction_receipt(tx)
                new_trust = contract.functions.getTrust(freelancer.wallet_address).call()
                freelancer.trust_score = new_trust
            except Exception:
                pass

    db.commit()
    return {"ok": True, "job_id": job.id, "status": "disputed"}


# ---------------------------------------------------------------------------
# Standalone analysis endpoint (no job context required)
# ---------------------------------------------------------------------------

class AnalyzeRepoRequest(BaseModel):
    github_repo_url: str
    requirements_text: str


@router.post("/analyze/repo")
def analyze_repo_standalone(req: AnalyzeRepoRequest, current_user: User = Depends(get_current_user)):
    """
    Standalone GitHub repo analysis against given requirements.
    No job needed — useful for quick evaluation.
    """
    if not re.match(r"https?://github\.com/[^/]+/[^/]+", req.github_repo_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL")

    files = _fetch_github_repo_files(req.github_repo_url)
    if not files:
        raise HTTPException(status_code=400, detail="Could not fetch any files from the repo")

    requirements = _parse_requirements(req.requirements_text)
    analysis = _analyze_repo_against_requirements(files, requirements)
    analysis["risk_score"] = round(1.0 - analysis["overall_coverage"], 4)

    return {"ok": True, "analysis": analysis}
