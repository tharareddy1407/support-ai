import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(PROJECT_ROOT, "knowledge_base.json")

# In-memory sessions (MVP). Later: DB/Redis.
SESSIONS: Dict[str, Dict[str, Any]] = {}

def load_kb() -> Dict[str, Any]:
    if not os.path.exists(KB_PATH):
        raise FileNotFoundError(f"knowledge_base.json not found at: {KB_PATH}")
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())

def score_issue(user_text: str, issue: Dict[str, Any]) -> float:
    """
    Simple keyword overlap score (MVP).
    Later we can upgrade to embeddings / semantic search.
    """
    q = set(tokenize(user_text))
    if not q:
        return 0.0

    keywords = issue.get("symptoms_keywords", []) or []
    title = issue.get("title", "") or ""
    product = issue.get("product_area", "") or ""
    tags = issue.get("tags", []) or []

    corpus = " ".join([title, product, " ".join(keywords), " ".join(tags)])
    e = set(tokenize(corpus))
    if not e:
        return 0.0

    overlap = len(q.intersection(e))
    return overlap / max(6, len(q))  # stabilize for short messages

def best_match(user_text: str, issues: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], float]:
    best = None
    best_score = 0.0
    for issue in issues:
        s = score_issue(user_text, issue)
        if s > best_score:
            best = issue
            best_score = s
    return best, best_score

def format_steps(steps: List[str]) -> str:
    if not steps:
        return "No steps available."
    return "\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)])

CONFIDENCE_THRESHOLD = 0.22

app = FastAPI(title="Support Automation AI (Step 4)")

# Allow opening web/index.html directly (file://) and calling this backend.
# In production, restrict origins to your website domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    customer_id: Optional[str] = None
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    session_id: str
    status: str
    reply: str
    matched_issue_id: Optional[str] = None
    match_score: float = 0.0

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z"}

@app.post("/support/chat", response_model=ChatResponse)
def support_chat(payload: ChatRequest):
    msg = (payload.message or "").strip()
    if not msg:
        sid = payload.session_id or f"SESSION-{uuid.uuid4().hex[:8].upper()}"
        return ChatResponse(session_id=sid, status="NEED_MORE_INFO", reply="Please describe the issue.")

    sid = payload.session_id or f"SESSION-{uuid.uuid4().hex[:8].upper()}"

    # Create/update session
    session = SESSIONS.get(sid) or {
        "session_id": sid,
        "customer_id": payload.customer_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "history": [],
        "status": "NEW",
    }
    session["history"].append({"ts": datetime.utcnow().isoformat() + "Z", "from": "customer", "text": msg})
    SESSIONS[sid] = session

    kb = load_kb()
    issues = kb.get("issues", []) or []

    issue, score = best_match(msg, issues)

    if issue and score >= CONFIDENCE_THRESHOLD:
        session["status"] = "SELF_SERVE_IN_PROGRESS"
        reply = (
            f"✅ Found a known fix: {issue['issue_id']} — {issue['title']} (match {score:.2f})\n\n"
            f"Step-by-step:\n{format_steps(issue.get('resolution_steps', []))}\n\n"
            f"Validate:\n{format_steps(issue.get('validation_steps', []))}\n\n"
            "If it’s still not working, reply with the exact error text (and screenshot if possible)."
        )
        session["history"].append({"ts": datetime.utcnow().isoformat() + "Z", "from": "ai", "text": reply})
        return ChatResponse(
            session_id=sid,
            status=session["status"],
            reply=reply,
            matched_issue_id=issue.get("issue_id"),
            match_score=score,
        )

    # No confident match → create a “ticket” (MVP: same session)
    session["status"] = "ESCALATED_TO_HUMAN"
    ticket_id = f"CASE-{sid.split('-')[-1]}"
    reply = (
        f"🆕 I couldn’t find an exact match (best match {score:.2f}).\n"
        f"I created a support ticket: {ticket_id}\n\n"
        "To help resolve faster, please provide:\n"
        "1) Exact error text\n"
        "2) When it started\n"
        "3) Screenshot (if available)\n"
        "4) Device/browser/app version\n"
        "5) Impact (how many users / blocked task)"
    )
    session["history"].append({"ts": datetime.utcnow().isoformat() + "Z", "from": "ai", "text": reply})
    return ChatResponse(session_id=sid, status=session["status"], reply=reply, match_score=score)

@app.get("/support/session/{session_id}")
def get_session(session_id: str):
    s = SESSIONS.get(session_id)
    if not s:
        return {"ok": False, "error": "session not found"}
    return {"ok": True, "session": s}
