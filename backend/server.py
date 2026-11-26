from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env", override=True)

import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from limiter import limiter
from auth import router as auth_router, hash_password, verify_password, ensure_indexes
from sessions_router import router as sessions_router
from topics_router import router as topics_router
from ai_service import router as ai_router
from document_router import router as document_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("typeforge")

from contextlib import asynccontextmanager

client = None
db = None


def _init_db():
    """Initialize MongoDB client and database handle lazily or at startup."""
    global client, db
    if db is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url)
        db = client[os.environ.get("DB_NAME", "typeforge")]
    return db


try:
    _init_db()
except Exception as e:
    logger.warning("Deferred MongoDB client initialization: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        active_db = app.state.db or _init_db()
        app.state.db = active_db
        await ensure_indexes(active_db)
        await active_db.documents.create_index([("user_id", 1), ("uploaded_at", -1)])
        await active_db.document_chunks.create_index([("document_id", 1), ("index", 1)])
        await active_db.generation_cache.create_index("created_at", expireAfterSeconds=86400)
        await seed_admin()
    except Exception as e:
        logger.warning("Startup DB initialization skipped/deferred: %s", e)
    yield
    if client is not None:
        client.close()


app = FastAPI(title="TypeForge API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api")


@app.middleware("http")
async def ensure_db_middleware(request, call_next):
    if getattr(app.state, "db", None) is None and not request.url.path.endswith(("/health", "/topics", "/api", "/api/")):
        try:
            app.state.db = _init_db()
        except Exception as e:
            logger.warning("Lazy MongoDB connection failed: %s", e)
    return await call_next(request)


@api_router.get("/")
async def root():
    return {"app": "TypeForge", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}


api_router.include_router(auth_router)
api_router.include_router(sessions_router)
api_router.include_router(topics_router)
api_router.include_router(ai_router)
api_router.include_router(document_router)
app.include_router(api_router)

# Inject db into app state for dependency access
app.state.db = db


# Removed deprecated on_event handlers in favor of lifespan


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@typeforge.app").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        logger.warning("ADMIN_PASSWORD not set. Skipping admin seeding.")
        return
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one(
            {
                "email": admin_email,
                "password_hash": hash_password(admin_password),
                "name": "Admin",
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("Seeded admin user %s", admin_email)
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )
        logger.info("Updated admin password for %s", admin_email)


frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allowed = (
    [o.strip() for o in os.environ.get("CORS_ORIGINS", frontend_url).split(",")]
    if os.environ.get("CORS_ORIGINS")
    else [frontend_url]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
