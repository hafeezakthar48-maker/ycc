from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router_registry import include_api_routers
from app.runtime_paths import get_frontend_dist_dir


app = FastAPI(title="China Finance AI Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

include_api_routers(app)


@app.get("/health")
def health():
    return {"status": "ok"}


def _mount_frontend_assets(application: FastAPI) -> None:
    frontend_dist = get_frontend_dist_dir()
    if frontend_dist is None:
        return

    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        application.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    index_file = frontend_dist / "index.html"
    if not index_file.exists():
        return

    @application.get("/", include_in_schema=False)
    def frontend_index():
        return FileResponse(index_file)

    @application.get("/{full_path:path}", include_in_schema=False)
    def frontend_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        requested_file = _safe_frontend_file(frontend_dist, full_path)
        if requested_file is not None:
            return FileResponse(requested_file)
        return FileResponse(index_file)


def _safe_frontend_file(frontend_dist: Path, request_path: str) -> Path | None:
    candidate = (frontend_dist / request_path).resolve()
    try:
        candidate.relative_to(frontend_dist.resolve())
    except ValueError:
        return None
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


_mount_frontend_assets(app)
