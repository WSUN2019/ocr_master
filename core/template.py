"""
Template save/load/list. Templates live as JSON files in the templates/ directory.
Each template maps field names to bounding boxes in PDF point coordinates.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _ensure_dir():
    TEMPLATES_DIR.mkdir(exist_ok=True)


def slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("/", "-")


def list_templates() -> list[dict]:
    """Return list of {name, slug, path} for all saved templates."""
    _ensure_dir()
    results = []
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            results.append({"name": data.get("name", f.stem), "slug": f.stem, "path": str(f)})
        except Exception:
            pass
    return results


def load_template(slug: str) -> Optional[dict]:
    _ensure_dir()
    path = TEMPLATES_DIR / f"{slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_template(template: dict) -> str:
    """Save template dict to disk. Returns slug."""
    _ensure_dir()
    slug = slugify(template["name"])
    template["slug"] = slug
    template.setdefault("version", 1)
    template.setdefault("created_at", datetime.now().isoformat())
    path = TEMPLATES_DIR / f"{slug}.json"
    path.write_text(json.dumps(template, indent=2))
    return slug


def delete_template(slug: str) -> bool:
    path = TEMPLATES_DIR / f"{slug}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def build_template(
    name: str,
    page_width_pts: float,
    page_height_pts: float,
    fields: list[dict],
    row_detection: dict,
    source_page: int = 0,
    sample_image_path: str = "",
) -> dict:
    """
    Construct a template dict ready for save_template().

    fields: list of {name, label, page, bbox:[x0,y0,x1,y1] in PDF pts}
    row_detection: {strategy, anchor_field, row_height_pts, start_y_pts, end_y_pts}
    """
    return {
        "name": name,
        "page_width_pts": page_width_pts,
        "page_height_pts": page_height_pts,
        "source_page": source_page,
        "fields": fields,
        "row_detection": row_detection,
        "sample_image_path": sample_image_path,
    }


def template_names() -> list[str]:
    return [t["name"] for t in list_templates()]


def template_slug_map() -> dict[str, str]:
    """Return {display_name: slug}"""
    return {t["name"]: t["slug"] for t in list_templates()}
