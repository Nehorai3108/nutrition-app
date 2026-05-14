"""Single shared image-data-uri helper used across pages."""

import base64
import os
from typing import Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def image_data_uri(rel_path: Optional[str], project_root: Optional[str] = None) -> str:
    """Return a ``data:image/jpeg;base64,...`` URI for a project-relative image.

    Returns an empty string when the path is missing or the file is unreadable.
    """
    if not rel_path:
        return ""
    root = project_root or _PROJECT_ROOT
    abs_path = rel_path if os.path.isabs(rel_path) else os.path.join(root, rel_path)
    if not os.path.isfile(abs_path):
        return ""
    try:
        with open(abs_path, "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        return f"data:image/jpeg;base64,{data}"
    except OSError:
        return ""
