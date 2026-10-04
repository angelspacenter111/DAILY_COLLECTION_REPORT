import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId
from database import db
try:
    from config import SECRET_KEY
except ImportError:
    SECRET_KEY = "aerodata_dcr_secret_key_2026"

logger = logging.getLogger(__name__)

AUTH_COOKIE_NAME = "dcr_session"
SESSION_DURATION_HOURS = 24

def hash_password(password: str) -> str:
    """Hashes a password securely using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}:{key.hex()}"

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifies a provided password against a stored PBKDF2 hash."""
    if not stored_hash or ":" not in stored_hash:
        return False
    try:
        salt, expected_hex = stored_hash.split(":", 1)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False

def generate_session_token(username: str, role: str) -> str:
    """Generates a signed session token containing username, role, and expiry timestamp."""
    secret = str(getattr(__import__('config'), 'SECRET_KEY', "aerodata_dcr_secret_key_2026")).encode('utf-8')
    expires_at = int((datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)).timestamp())
    payload = f"{username}:{role}:{expires_at}"
    signature = hmac.new(secret, payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Verifies signature and expiration of a session token."""
    if not token or token.count(":") != 3:
        return None
    try:
        secret = str(getattr(__import__('config'), 'SECRET_KEY', "aerodata_dcr_secret_key_2026")).encode('utf-8')
        username, role, expires_at_str, signature = token.split(":", 3)
        expires_at = int(expires_at_str)
        
        # Check expiry
        if datetime.utcnow().timestamp() > expires_at:
            return None
        
        # Verify HMAC
        payload = f"{username}:{role}:{expires_at_str}"
        expected_sig = hmac.new(secret, payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        return {
            "username": username,
            "role": role,
            "expires_at": expires_at
        }
    except Exception:
        return None

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetches user document by username from MongoDB."""
    user = await db.users.find_one({"username": username.strip().lower()})
    if user:
        user["id"] = str(user["_id"])
    return user

async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates username and password. Returns user document if valid, else None."""
    user = await get_user_by_username(username)
    if not user:
        return None
    if not verify_password(user.get("password_hash", ""), password):
        return None
    return user

async def get_distinct_movies() -> List[str]:
    """Returns sorted list of distinct non-empty movie names from dcr_reports."""
    try:
        raw_movies = await db.dcr_reports.distinct("movie_name")
        seen = {}
        for m in raw_movies:
            if not m:
                continue
            cleaned = str(m).strip().rstrip(" .")
            if not cleaned:
                continue
            key = cleaned.upper()
            if key not in seen:
                seen[key] = cleaned.upper()
        return sorted(list(seen.values()))
    except Exception as e:
        logger.warning("Error fetching distinct movies: %s", e)
        return []

def build_movie_filter_query(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Constructs a MongoDB filter query for DCR reports based on user role and assigned movies.
    Super Admin sees all movies (empty query {}).
    Normal user sees ONLY their assigned movies (using regex $or matching).
    """
    import re
    if not user or user.get("role") == "super_admin":
        return {}

    assigned = user.get("assigned_movies", [])
    if not assigned:
        # User has no movies assigned yet, return impossible query so no other movies leak
        return {"_id": {"$exists": False}}

    or_clauses = []
    for m in assigned:
        m_clean = str(m).strip()
        if m_clean:
            or_clauses.append({"movie_name": {"$regex": re.escape(m_clean), "$options": "i"}})

    if or_clauses:
        return {"$or": or_clauses}
    return {"_id": {"$exists": False}}

def user_can_access_movie(user: Optional[Dict[str, Any]], movie_name: str) -> bool:
    """Checks whether the user has permission to view a specific movie's report."""
    if not user:
        return False
    if user.get("role") == "super_admin":
        return True
    assigned = user.get("assigned_movies", [])
    clean_movie = (movie_name or "").strip().lower()
    for m in assigned:
        m_clean = str(m).strip().lower()
        if m_clean and (m_clean in clean_movie or clean_movie in m_clean):
            return True
    return False

async def create_user(
    username: str,
    password: str,
    full_name: str,
    role: str = "user",
    assigned_movies: Optional[List[str]] = None,
    created_by: str = "system"
) -> Dict[str, Any]:
    """Creates a new user in MongoDB with optional movie mappings."""
    clean_username = username.strip().lower()
    existing = await db.users.find_one({"username": clean_username})
    if existing:
        raise ValueError(f"Username '@{clean_username}' already exists. Please choose a different username.")

    password_hash = hash_password(password)
    user_doc = {
        "username": clean_username,
        "password_hash": password_hash,
        "full_name": full_name.strip() or clean_username.title(),
        "role": role,  # 'super_admin' or 'user'
        "assigned_movies": assigned_movies or [],
        "created_by": created_by,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    result = await db.users.insert_one(user_doc)
    user_doc["id"] = str(result.inserted_id)
    return user_doc

async def update_user_movies(user_id: str, assigned_movies: List[str]) -> bool:
    """Updates the movie mappings for a specific user."""
    try:
        res = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"assigned_movies": assigned_movies}}
        )
        return res.matched_count > 0
    except Exception as e:
        logger.error("Error updating user movies %s: %s", user_id, e)
        return False

async def list_all_users() -> List[Dict[str, Any]]:
    """Returns all users from MongoDB sorted by created_at."""
    cursor = db.users.find({}).sort("created_at", -1)
    users = []
    async for u in cursor:
        u["id"] = str(u["_id"])
        u.pop("password_hash", None)
        u["assigned_movies"] = u.get("assigned_movies", [])
        if isinstance(u.get("created_at"), datetime):
            u["created_at_display"] = u["created_at"].strftime("%d %b %Y, %I:%M %p")
        users.append(u)
    return users

async def delete_user(user_id: str, requesting_username: str) -> bool:
    """Deletes a user by ID. Prevents deleting the last super_admin or oneself."""
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return False
        if user.get("username") == requesting_username.lower():
            raise ValueError("You cannot delete your own account.")
        if user.get("role") == "super_admin":
            admin_count = await db.users.count_documents({"role": "super_admin"})
            if admin_count <= 1:
                raise ValueError("Cannot delete the only Super Admin account.")

        res = await db.users.delete_one({"_id": ObjectId(user_id)})
        return res.deleted_count > 0
    except Exception as e:
        logger.error("Error deleting user %s: %s", user_id, e)
        raise

async def seed_default_super_admin():
    """Initializes default super admin (admin / admin123) if none exists."""
    try:
        admin_count = await db.users.count_documents({"role": "super_admin"})
        if admin_count == 0:
            logger.info("[AUTH] No Super Admin found. Seeding default super admin: 'admin'...")
            await create_user(
                username="admin",
                password="admin123",
                full_name="Super Admin",
                role="super_admin",
                created_by="system_seed"
            )
            logger.info("[AUTH] Default super admin created successfully (Username: admin | Password: admin123).")
    except Exception as e:
        logger.warning("[AUTH] Error checking/seeding super admin: %s", e)
