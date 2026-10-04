import logging
from typing import Optional, Dict, Any
from fastapi import Request, Form, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import BASE_URL
from helpers.auth_helper import (
    AUTH_COOKIE_NAME,
    SESSION_DURATION_HOURS,
    authenticate_user,
    generate_session_token,
    verify_session_token,
    get_user_by_username,
    list_all_users,
    create_user,
    delete_user,
    get_distinct_movies,
    update_user_movies,
)

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Extracts and verifies the currently logged-in user from request cookie."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None
    session_data = verify_session_token(token)
    if not session_data:
        return None
    user = await get_user_by_username(session_data["username"])
    if not user or not user.get("is_active", True):
        return None
    return user

async def login_view(request: Request):
    """Renders the login page if not already authenticated."""
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/dcrextracter", status_code=302)

    error = request.query_params.get("error")
    context = {
        "BASE_URL": BASE_URL,
        "error": error
    }
    return templates.TemplateResponse(request=request, name="login.html", context=context)

async def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Processes login credentials, generates signed session cookie."""
    user = await authenticate_user(username, password)
    if not user:
        return RedirectResponse(url="/login?error=Invalid+username+or+password", status_code=302)

    token = generate_session_token(user["username"], user.get("role", "user"))
    response = RedirectResponse(url="/dcrextracter", status_code=302)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=SESSION_DURATION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=False  # Works on HTTP localhost as well as HTTPS
    )
    logger.info("[AUTH] User '%s' (%s) logged in successfully.", user['username'], user.get('role'))
    return response

async def logout_action(request: Request):
    """Clears session cookie and redirects to login."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=AUTH_COOKIE_NAME)
    return response

async def users_view(request: Request):
    """Renders User Management page (Super Admin only)."""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    if current_user.get("role") != "super_admin":
        return RedirectResponse(url="/dcrextracter", status_code=302)

    users = await list_all_users()
    distinct_movies = await get_distinct_movies()
    context = {
        "BASE_URL": BASE_URL,
        "current_user": current_user,
        "users": users,
        "distinct_movies": distinct_movies
    }
    return templates.TemplateResponse(request=request, name="users.html", context=context)

async def create_user_action(request: Request):
    """API for Super Admin to create a new user with optional movie assignments."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    try:
        data = await request.json()
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        full_name = data.get("full_name", "").strip()
        role = data.get("role", "user").strip()
        raw_movies = data.get("assigned_movies", [])
        assigned_movies = [str(m).strip() for m in raw_movies if str(m).strip()] if isinstance(raw_movies, list) else []

        clean_username = username.strip().lower()
        if not clean_username or not password:
            return JSONResponse({"status": False, "message": "Username and Password are required."}, status_code=400)
        if " " in clean_username:
            return JSONResponse({"status": False, "message": "Username cannot contain spaces."}, status_code=400)
        if len(password) < 4:
            return JSONResponse({"status": False, "message": "Password must be at least 4 characters long."}, status_code=400)
        if role not in ("user", "super_admin"):
            role = "user"

        new_user = await create_user(
            username=clean_username,
            password=password,
            full_name=full_name,
            role=role,
            assigned_movies=assigned_movies,
            created_by=current_user["username"]
        )
        logger.info("[AUTH] Super Admin '%s' created new user '%s' (%s) with movies: %s", current_user['username'], username, role, assigned_movies)
        return JSONResponse({
            "status": True,
            "message": f"User '{username}' created successfully.",
            "user": {
                "id": new_user["id"],
                "username": new_user["username"],
                "full_name": new_user["full_name"],
                "role": new_user["role"],
                "assigned_movies": new_user.get("assigned_movies", [])
            }
        })
    except ValueError as ve:
        return JSONResponse({"status": False, "message": str(ve)}, status_code=400)
    except Exception as e:
        logger.exception("Error creating user: %s", e)
        return JSONResponse({"status": False, "message": f"Server error: {str(e)}"}, status_code=500)

async def update_user_movies_action(request: Request, user_id: str):
    """API for Super Admin to update movie mappings for an existing user."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    try:
        data = await request.json()
        raw_movies = data.get("assigned_movies", [])
        assigned_movies = [str(m).strip() for m in raw_movies if str(m).strip()] if isinstance(raw_movies, list) else []
        success = await update_user_movies(user_id, assigned_movies)
        if success:
            logger.info("[AUTH] Super Admin '%s' updated movies for user ID '%s' to: %s", current_user['username'], user_id, assigned_movies)
            return JSONResponse({"status": True, "message": "User movie access updated successfully."})
        return JSONResponse({"status": False, "message": "User not found or update failed."}, status_code=404)
    except Exception as e:
        logger.exception("Error updating user movies: %s", e)
        return JSONResponse({"status": False, "message": f"Server error: {str(e)}"}, status_code=500)

async def delete_user_action(request: Request, user_id: str):
    """API for Super Admin to delete a user."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    try:
        success = await delete_user(user_id, current_user["username"])
        if success:
            logger.info("[AUTH] Super Admin '%s' deleted user ID '%s'.", current_user['username'], user_id)
            return JSONResponse({"status": True, "message": "User deleted successfully."})
        return JSONResponse({"status": False, "message": "User not found."}, status_code=404)
    except ValueError as ve:
        return JSONResponse({"status": False, "message": str(ve)}, status_code=400)
    except Exception as e:
        logger.exception("Error deleting user: %s", e)
        return JSONResponse({"status": False, "message": str(e)}, status_code=500)
