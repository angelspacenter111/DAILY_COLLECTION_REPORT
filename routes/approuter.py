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
from controllers.cinema_controller import (
    cinemas_view,
    get_cinema_action,
    create_cinema_action,
    update_cinema_action,
    delete_cinema_action,
    download_cinemas_excel,
    download_cinema_template_excel,
    bulk_upload_cinemas_action,
)
from controllers.release_controller import (
    releases_view,
    get_release_action,
    create_release_action,
    update_release_action,
    delete_release_action,
    clear_all_releases_action,
    download_releases_excel,
    download_release_template_excel,
    bulk_upload_releases_action,
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

# Cinema Master Routes
router.get("/cinemas")(cinemas_view)
router.get("/cinemas/download-excel")(download_cinemas_excel)
router.get("/api/cinemas/download-excel")(download_cinemas_excel)
router.get("/api/cinemas/download-template")(download_cinema_template_excel)
router.post("/api/cinemas/bulk-upload")(bulk_upload_cinemas_action)
router.get("/api/cinemas/{cinema_id}")(get_cinema_action)
router.post("/api/cinemas/create")(create_cinema_action)
router.post("/api/cinemas/update/{cinema_id}")(update_cinema_action)
router.post("/api/cinemas/delete/{cinema_id}")(delete_cinema_action)

# Release Master Routes
router.get("/releases")(releases_view)
router.get("/releases/download-excel")(download_releases_excel)
router.get("/api/releases/download-excel")(download_releases_excel)
router.get("/api/releases/download-template")(download_release_template_excel)
router.post("/api/releases/bulk-upload")(bulk_upload_releases_action)
router.get("/api/releases/{release_id}")(get_release_action)
router.post("/api/releases/create")(create_release_action)
router.post("/api/releases/update/{release_id}")(update_release_action)
router.post("/api/releases/delete/{release_id}")(delete_release_action)
router.post("/api/releases/clear-all")(clear_all_releases_action)

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
