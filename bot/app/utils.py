import mimetypes
from io import BytesIO
from typing import Tuple

def guess_content_type(filename: str) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or "application/octet-stream"

def safe_filename(default_name: str) -> str:
    # juda oddiy sanitizatsiya
    return default_name.replace("/", "_").replace("\\", "_")
