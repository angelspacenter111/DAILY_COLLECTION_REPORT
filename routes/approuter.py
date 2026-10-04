
from fastapi import APIRouter

from controllers.master_controller import (index, create, createprocessmethod)
from controllers.extracter_controller import (
    extracterindex,
    downloadExcel,
    download_single_report_pdf,
    delete_record,
    clear_all_records,
    sync_emails_action,
)
from controllers.auth_controller import (
    login_view,
    login_action,
    logout_action,
    users_view,
    create_user_action,
    update_user_movies_action,
    delete_user_action,
)

router = APIRouter()

# Authentication & User Management Routes
router.get("/login")(login_view)
router.post("/login")(login_action)
router.get("/logout")(logout_action)
router.post("/logout")(logout_action)
router.get("/users")(users_view)
router.post("/api/users/create")(create_user_action)
router.post("/api/users/update-movies/{user_id}")(update_user_movies_action)
router.post("/api/users/delete/{user_id}")(delete_user_action)

# DCR Core Routes
router.get("/")(index)
router.get("/create")(create)
router.post("/createprocess")(createprocessmethod)
router.get("/dcrextracter")(extracterindex)
router.get("/downloadcdrexcel")(downloadExcel)
router.get("/api/records/download-pdf/{record_id}")(download_single_report_pdf)
router.post("/api/records/delete/{record_id}")(delete_record)
router.post("/api/records/clear-all")(clear_all_records)
router.post("/api/emails/sync")(sync_emails_action)


