"""Sessions: store typing test results, list history, aggregate stats."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import io
import csv

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])

DAILY_GOAL = 3
DIFFICULTY_ORDER = ["Beginner", "Intermediate", "Advanced"]


class Keystroke(BaseModel):
    t: float  # ms since session start
    correct: bool


class SessionCreate(BaseModel):
    domain: str
    topic: str
    difficulty: str
    source_type: str = Field("ai", description="'ai' or 'document'")
    source_document_id: Optional[str] = None
    question: Optional[str] = None
    recall_ms: Optional[int] = None
    target_text: str
    typed_text: str
    duration_seconds: float
    wpm: float
    raw_wpm: float
    accuracy: float
    correct_chars: int
    incorrect_chars: int
    total_chars: int
    error_chars: List[str] = Field(default_factory=list)
    keystrokes: List[Keystroke] = Field(default_factory=list)


class SessionOut(BaseModel):
    id: str
    domain: str
    topic: str
    difficulty: str
    source_type: str = "ai"
    source_document_id: Optional[str] = None
    question: Optional[str] = None
    recall_ms: Optional[int] = None
    duration_seconds: float
    wpm: float
    raw_wpm: float
    accuracy: float
    correct_chars: int
    incorrect_chars: int
    total_chars: int
    error_chars: List[str]
    target_text: str
    typed_text: str
    created_at: str
    keystrokes: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("", response_model=SessionOut)
async def create_session(payload: SessionCreate, request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["user_id"] = user["id"]
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.sessions.insert_one(doc)
    return SessionOut(**{k: doc[k] for k in SessionOut.model_fields.keys()})


@router.get("", response_model=List[SessionOut])
async def list_sessions(request: Request, limit: int = 50, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    cursor = (
        db.sessions.find({"user_id": user["id"]}, {"_id": 0, "keystrokes": 0})
        .sort("created_at", -1)
        .limit(min(limit, 200))
    )
    items = await cursor.to_list(length=limit)
    out = []
    for it in items:
        kwargs = {k: it.get(k) for k in SessionOut.model_fields.keys() if it.get(k) is not None}
        out.append(SessionOut(**kwargs))
    return out


@router.get("/export")
async def export_sessions(request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    cursor = db.sessions.find({"user_id": user["id"]}, {"_id": 0, "keystrokes": 0}).sort("created_at", -1)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "created_at", "domain", "topic", "difficulty",
        "wpm", "raw_wpm", "accuracy", "duration_seconds",
        "correct_chars", "incorrect_chars", "total_chars"
    ])
    
    async for it in cursor:
        writer.writerow([
            it.get("id", ""), it.get("created_at", ""), it.get("domain", ""), it.get("topic", ""), it.get("difficulty", ""),
            it.get("wpm", ""), it.get("raw_wpm", ""), it.get("accuracy", ""), it.get("duration_seconds", ""),
            it.get("correct_chars", ""), it.get("incorrect_chars", ""), it.get("total_chars", "")
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=typeforge_export.csv"}
    )


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    doc = await db.sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut(**{k: doc.get(k) for k in SessionOut.model_fields.keys()})


class StreakOut(BaseModel):
    current: int
    longest: int
    today: int
    goal: int
    goal_met: bool


class RecommendationOut(BaseModel):
    difficulty: str
    length: str
    reason: str
    based_on_sessions: int


class StatsOut(BaseModel):
    total_sessions: int
    total_minutes: float
    avg_wpm: float
    best_wpm: float
    avg_accuracy: float
    last_30: list  # daily aggregates
    by_domain: list
    streak: StreakOut
    recommendation: RecommendationOut
    heatmap: Dict[str, int]


def _compute_streak(items: List[dict], goal: int = 3) -> StreakOut:
    if not items:
        return StreakOut(current=0, longest=0, today=0, goal=goal, goal_met=False)
    days_set = set()
    today = datetime.now(timezone.utc).date()
    today_count = 0
    for i in items:
        try:
            d = datetime.fromisoformat(i["created_at"]).date()
        except Exception:
            continue
        days_set.add(d)
        if d == today:
            today_count += 1
    if not days_set:
        return StreakOut(current=0, longest=0, today=0, goal=goal, goal_met=False)
    days_sorted = sorted(days_set, reverse=True)
    # current streak: starts at today or yesterday and counts consecutive days backwards
    first = days_sorted[0]
    if first == today or first == today - timedelta(days=1):
        current = 1
        for prev, curr in zip(days_sorted, days_sorted[1:]):
            if (prev - curr) == timedelta(days=1):
                current += 1
            else:
                break
    else:
        current = 0
    # longest streak across all days
    longest = 1
    cur_run = 1
    for prev, curr in zip(days_sorted, days_sorted[1:]):
        if (prev - curr) == timedelta(days=1):
            cur_run += 1
            longest = max(longest, cur_run)
        else:
            cur_run = 1
    return StreakOut(
        current=current,
        longest=max(longest, current),
        today=today_count,
        goal=goal,
        goal_met=today_count >= goal,
    )


def _compute_recommendation(items_desc: List[dict]) -> RecommendationOut:
    last5 = items_desc[:5]
    if not last5:
        return RecommendationOut(
            difficulty="Beginner",
            length="short",
            reason="Start easy and build a baseline. The forge needs raw iron.",
            based_on_sessions=0,
        )
    avg_wpm = sum(s.get("wpm", 0) for s in last5) / len(last5)
    avg_acc = sum(s.get("accuracy", 0) for s in last5) / len(last5)
    last_diff = last5[0].get("difficulty", "Intermediate")
    idx = DIFFICULTY_ORDER.index(last_diff) if last_diff in DIFFICULTY_ORDER else 1

    if avg_acc >= 95 and avg_wpm >= 50 and idx < 2:
        new_diff = DIFFICULTY_ORDER[idx + 1]
        reason = (
            f"Crushing {avg_acc:.0f}% accuracy at {avg_wpm:.0f} WPM. "
            f"Time to step up to {new_diff}."
        )
    elif avg_acc < 85 and idx > 0:
        new_diff = DIFFICULTY_ORDER[idx - 1]
        reason = (
            f"Build accuracy first ({avg_acc:.0f}%). "
            f"Drop to {new_diff} to lock in fundamentals."
        )
    else:
        new_diff = last_diff
        reason = (
            f"Stay the course at {last_diff}. "
            f"{avg_wpm:.0f} WPM at {avg_acc:.0f}% accuracy. Keep grinding."
        )

    if avg_acc >= 95:
        rec_len = "long"
    elif avg_acc >= 88:
        rec_len = "medium"
    else:
        rec_len = "short"

    return RecommendationOut(
        difficulty=new_diff,
        length=rec_len,
        reason=reason,
        based_on_sessions=len(last5),
    )


@router.get("/stats/overview", response_model=StatsOut)
async def stats(request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    user_id = user["id"]

    # 1. Total stats via aggregation
    total_cur = await db.sessions.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "total_seconds": {"$sum": "$duration_seconds"},
            "avg_wpm": {"$avg": "$wpm"},
            "best_wpm": {"$max": "$wpm"},
            "avg_accuracy": {"$avg": "$accuracy"},
        }}
    ]).to_list(1)

    if not total_cur:
        return StatsOut(
            total_sessions=0, total_minutes=0.0, avg_wpm=0.0, best_wpm=0.0,
            avg_accuracy=0.0, last_30=[], by_domain=[],
            streak=_compute_streak([], user.get("daily_goal", 3)),
            recommendation=_compute_recommendation([]),
            heatmap={},
        )

    t = total_cur[0]
    total = t.get("total", 0)
    total_seconds = t.get("total_seconds", 0)

    # 2. Last 30 days via aggregation
    days_cur = await db.sessions.aggregate([
        {"$match": {"user_id": user_id}},
        {"$project": {
            "date": {"$substr": ["$created_at", 0, 10]},
            "wpm": 1,
            "accuracy": 1
        }},
        {"$group": {
            "_id": "$date",
            "sessions": {"$sum": 1},
            "avg_wpm": {"$avg": "$wpm"},
            "avg_accuracy": {"$avg": "$accuracy"}
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 30}
    ]).to_list(30)

    last_30 = [
        {
            "date": d["_id"],
            "sessions": d["sessions"],
            "avg_wpm": round(d.get("avg_wpm", 0), 1),
            "avg_accuracy": round(d.get("avg_accuracy", 0), 1)
        }
        for d in days_cur
    ]

    # 3. By domain via aggregation
    domain_cur = await db.sessions.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$domain",
            "sessions": {"$sum": 1},
            "avg_wpm": {"$avg": "$wpm"},
            "avg_accuracy": {"$avg": "$accuracy"},
        }},
        {"$sort": {"sessions": -1}}
    ]).to_list(100)

    by_domain = [
        {
            "domain": d["_id"] or "Unknown",
            "sessions": d["sessions"],
            "avg_wpm": round(d.get("avg_wpm", 0), 1),
            "avg_accuracy": round(d.get("avg_accuracy", 0), 1)
        }
        for d in domain_cur
    ]

    # 4. Streak (needs dates) and Recommendation (needs last 5)
    dates_cur = await db.sessions.find(
        {"user_id": user_id},
        {"created_at": 1, "_id": 0}
    ).to_list(5000)

    recent_5 = await db.sessions.find(
        {"user_id": user_id},
        {"wpm": 1, "accuracy": 1, "difficulty": 1, "_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)

    # 5. Heatmap via aggregation
    heatmap_cur = await db.sessions.aggregate([
        {"$match": {"user_id": user_id}},
        {"$unwind": "$error_chars"},
        {"$group": {
            "_id": {"$toLower": "$error_chars"},
            "count": {"$sum": 1}
        }}
    ]).to_list(None)

    heatmap_data = {
        item["_id"]: item["count"]
        for item in heatmap_cur
        if isinstance(item.get("_id"), str) and item["_id"].isalpha()
    }

    return StatsOut(
        total_sessions=total,
        total_minutes=round(total_seconds / 60, 1),
        avg_wpm=round(t.get("avg_wpm", 0), 1),
        best_wpm=round(t.get("best_wpm", 0), 1),
        avg_accuracy=round(t.get("avg_accuracy", 0), 1),
        last_30=last_30,
        by_domain=by_domain,
        streak=_compute_streak(dates_cur, user.get("daily_goal", 3)),
        recommendation=_compute_recommendation(recent_5),
        heatmap=heatmap_data,
    )
