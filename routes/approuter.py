
from fastapi import APIRouter

from controllers.master_controller import (index, create, createprocessmethod)
from controllers.extracter_controller import (extracterindex, downloadExcel)

router = APIRouter()

router.get("/")(index)
router.get("/create")(create)
router.post("/createprocess")(createprocessmethod)
router.get("/dcrextracter")(extracterindex)
router.get("/downloadcdrexcel")(downloadExcel)

