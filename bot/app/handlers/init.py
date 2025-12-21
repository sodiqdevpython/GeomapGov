from .start import router as start_router
from .report import router as report_router
from .my_reports import router as my_reports_router
from .guide import router as guide_router

def get_routers():
    return [start_router, report_router, my_reports_router, guide_router]
