
from fastapi import APIRouter

from controllers.master_controller import (index, create, createprocessmethod)
from controllers.extracter_controller import (
    extracterindex,
    downloadExcel,
    delete_record,
    clear_all_records,
)

router = APIRouter()

router.get("/")(index)
router.get("/create")(create)
router.post("/createprocess")(createprocessmethod)
router.get("/dcrextracter")(extracterindex)
router.get("/downloadcdrexcel")(downloadExcel)
router.post("/api/records/delete/{record_id}")(delete_record)
router.post("/api/records/clear-all")(clear_all_records)

