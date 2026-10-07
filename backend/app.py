import uuid
import os
from pathlib import Path
import sys
import json
import pickle
import asyncio
import logging
import math
import time
from contextlib import suppress
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Add repository root to path so the src package imports consistently.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.main import LayoutConvergenceError, main as run_design_generator
from src.graph_output import plot_network

app = FastAPI(title="OoC Design Generator API")

PUBLIC_PREFIXES = tuple(
    prefix.strip().rstrip("/")
    for prefix in os.getenv("NORA_PUBLIC_PREFIXES", "/app/mmft-nora,/mmft-nora").split(",")
    if prefix.strip()
)
GUI_DIST_DIR = Path(__file__).parent.parent / "gui" / "dist"
GUI_INDEX = GUI_DIST_DIR / "index.html"


@app.middleware("http")
async def strip_public_prefix(request, call_next):
    path = request.scope.get("path", "")
    for prefix in PUBLIC_PREFIXES:
        if path == prefix:
            return RedirectResponse(f"{prefix}/")
        if path.startswith(f"{prefix}/"):
            request.scope["path"] = path[len(prefix):] or "/"
            break
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("uvicorn.error")
JOB_TIMEOUT_SECONDS = float(os.getenv("NORA_JOB_TIMEOUT_SECONDS", "120"))
MAX_CONCURRENT_JOBS = int(os.getenv("NORA_MAX_CONCURRENT_JOBS", "1"))
if not math.isfinite(JOB_TIMEOUT_SECONDS) or JOB_TIMEOUT_SECONDS <= 0 or MAX_CONCURRENT_JOBS < 1:
    raise ValueError("NoRA job timeout and concurrency limit must be positive and finite")
WORKER_SLOTS = asyncio.Semaphore(MAX_CONCURRENT_JOBS)


async def _run_worker(operation: str, job_id: str, parameters: dict) -> dict:
    # ponytail: limit per API process; keep one Uvicorn worker for the configured server-wide limit.
    if WORKER_SLOTS.locked():
        raise HTTPException(503, "The design generator is busy. Please try again shortly.", headers={"Retry-After": "5"})

    async with WORKER_SLOTS:
        started = time.monotonic()
        process = None
        logger.info("Starting %s job=%s parameters=%s", operation, job_id, json.dumps(parameters, sort_keys=True))
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "backend.worker", operation, job_id,
                cwd=Path(__file__).resolve().parent.parent,
                env={**os.environ, "MPLBACKEND": "Agg"},
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                # Keep diagnostics in the service log, not the JSON response pipe.
            )
            payload = {"parameters": parameters, "output_dir": str(OUTPUT_DIR.resolve())}
            stdout, _ = await asyncio.wait_for(
                process.communicate(json.dumps(payload).encode()), timeout=JOB_TIMEOUT_SECONDS,
            )
            if process.returncode != 0:
                raise RuntimeError(f"Worker exited with status {process.returncode}")
            result = json.loads(stdout)
            if "error" in result:
                logger.warning("Failed %s job=%s: %s", operation, job_id, result["error"])
                raise HTTPException(result["status_code"], result["error"])
            logger.info("Completed %s job=%s elapsed=%.2fs", operation, job_id, time.monotonic() - started)
            return result
        except asyncio.TimeoutError:
            logger.warning("Timed out %s job=%s pid=%s after %.2fs", operation, job_id, process.pid, JOB_TIMEOUT_SECONDS)
            raise HTTPException(
                504, f"The calculation exceeded the {JOB_TIMEOUT_SECONDS:g}-second time limit. "
                "Try fewer modules or adjust the layout spacing.",
            )
        except asyncio.CancelledError:
            logger.info("Cancelled %s job=%s", operation, job_id)
            raise
        except HTTPException:
            raise
        except Exception:
            logger.exception("Worker failed %s job=%s", operation, job_id)
            raise HTTPException(500, "The calculation failed. Please check the parameters and try again.")
        finally:
            if process is not None:
                if process.returncode is None:
                    with suppress(ProcessLookupError):
                        process.kill()
                # Reap the worker even when its HTTP task is cancelled.
                await asyncio.shield(process.communicate())
                for key, suffix in (("preview", "png"), ("meta", "json")):
                    _job_paths(job_id)[key].with_suffix(f".{process.pid}.tmp.{suffix}").unlink(missing_ok=True)


def _job_paths(job_id: str) -> dict:
    return {
        "dxf_combined": OUTPUT_DIR / f"design_{job_id}.dxf",
        "preview": OUTPUT_DIR / f"preview_{job_id}.png",
        "pickle": OUTPUT_DIR / f"job_{job_id}.pkl",
        "meta": OUTPUT_DIR / f"job_{job_id}.json",
    }


def _list_job_dxfs(job_id: str) -> List[Path]:
    # Includes combined, layer/depth, vias.
    files = list(OUTPUT_DIR.glob(f"design_{job_id}*.dxf"))

    def sort_key(p: Path):
        name = p.name
        if name == f"design_{job_id}.dxf":
            return (0, 0, 0, name)
        if name.endswith("_vias.dxf"):
            return (9, 0, 0, name)
        # layer/depth
        # e.g. design_<id>_layer0_depth0.00015.dxf
        layer = 99
        depth = 99.0
        try:
            parts = name.split("_layer", 1)[1]
            layer_str, depth_part = parts.split("_depth", 1)
            layer = int(layer_str)
            depth = float(depth_part.replace(".dxf", ""))
        except Exception:
            pass
        return (1, layer, depth, name)

    return sorted(files, key=sort_key)


def _write_job_meta(job_id: str, color_by_flow: bool) -> None:
    paths = _job_paths(job_id)
    dxf_files = _list_job_dxfs(job_id)
    meta = {
        "jobId": job_id,
        "colorByFlow": bool(color_by_flow),
        "dxfFiles": [p.name for p in dxf_files],
        "combinedDxf": paths["dxf_combined"].name,
        "preview": paths["preview"].name,
    }
    temporary = paths["meta"].with_suffix(f".{os.getpid()}.tmp.json")
    temporary.write_text(json.dumps(meta, indent=2))
    temporary.replace(paths["meta"])


def _render_preview_png(*, job_id: str, nodes, channels, exclusion_zones, cfg: Config, color_by_flow: bool) -> Path:
    # Render plot without re-running the generator.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    paths = _job_paths(job_id)
    fig = plot_network(
        nodes,
        channels,
        cfg.organ_module["size_x"],
        cfg.organ_module["size_y"],
        exclusion_zones,
        cfg.channel_dim,
        color_by_flow=color_by_flow,
        chip_layout=cfg.chip_layout,
    )
    temporary = paths["preview"].with_suffix(f".{os.getpid()}.tmp.png")
    try:
        fig.savefig(temporary, dpi=150, bbox_inches="tight")
        temporary.replace(paths["preview"])
    finally:
        plt.close(fig)
        temporary.unlink(missing_ok=True)
    return paths["preview"]


class GenerateRequest(BaseModel):
    twoGradients: bool = True
    modulesX: int = Field(ge=1, le=50)
    modulesY: int = Field(ge=1, le=50)
    dilutionX: float = Field(gt=0, le=1)
    dilutionY: float = Field(gt=0, le=1)
    viscosity: float = Field(gt=0)
    channelWidth: float = Field(gt=0)
    channelHeight: float = Field(gt=0)
    viaDiameter: float = Field(gt=0)
    gridResolution: float = Field(gt=0)
    # Chip geometry & spacing (lengths in micrometers)
    layerSwitchDistance: float = Field(default=1162, gt=0)
    chipSizeX: float = Field(default=85480, gt=0)
    chipSizeY: float = Field(default=127760, gt=0)
    chipSideSpacing: float = Field(default=7000, gt=0)
    spacingX: float = Field(default=2000, gt=0)
    spacingY: float = Field(default=800, gt=0)
    spacingOut: float = Field(default=800, gt=0)
    colorByFlow: bool = False


class GenerateResponse(BaseModel):
    dxfUrl: str
    previewUrl: str
    jobId: str


class DxfFile(BaseModel):
    name: str
    url: str


class GenerateResponseV2(GenerateResponse):
    dxfFiles: List[DxfFile]
    colorByFlow: bool


@app.post("/api/generate", response_model=GenerateResponseV2)
async def generate_design(req: GenerateRequest):
    """Generate microfluidic design from GUI parameters."""
    job_id = str(uuid.uuid4())[:8]
    try:
        return await _run_worker("generate", job_id, req.model_dump())
    except (Exception, asyncio.CancelledError):
        # Failed jobs must not leave partially generated downloads behind.
        for prefix in ("design", "preview", "job"):
            for path in OUTPUT_DIR.glob(f"{prefix}_{job_id}*"):
                path.unlink(missing_ok=True)
        raise


def _generate_design(req: GenerateRequest, job_id: str):

    try:
        # Map GUI params to Config
        cfg = Config()
        cfg.two_gradients = req.twoGradients
        cfg.no_of_modules_x = req.modulesX
        cfg.no_of_modules_y = req.modulesY
        cfg.concentration_dilution_x = req.dilutionX
        cfg.concentration_dilution_y = req.dilutionY
        cfg.viscosity = req.viscosity

        # Convert micrometers to meters
        cfg.channel_dim["width"] = req.channelWidth * 1e-6
        cfg.channel_dim["height"] = req.channelHeight * 1e-6
        cfg.channel_dim["via_diameter"] = req.viaDiameter * 1e-6
        cfg.grid_resolution = req.gridResolution * 1e-6

        # Chip geometry & spacing (micrometers -> meters)
        cfg.channel_dim["layer_switch_distance"] = req.layerSwitchDistance * 1e-6
        cfg.chip_layout["size_x"] = req.chipSizeX * 1e-6
        cfg.chip_layout["size_y"] = req.chipSizeY * 1e-6
        cfg.chip_layout["spacing_side"] = req.chipSideSpacing * 1e-6
        cfg.spacing_x = req.spacingX * 1e-6
        cfg.spacing_y = req.spacingY * 1e-6
        cfg.spacing_out = req.spacingOut * 1e-6

        # Set output paths
        dxf_path = OUTPUT_DIR / f"design_{job_id}.dxf"
        preview_path = OUTPUT_DIR / f"preview_{job_id}.png"

        cfg.output_dxf_path = str(dxf_path)
        cfg.output_preview_path = str(preview_path)

        # print(f"[DEBUG] Output paths: DXF={dxf_path}, PNG={preview_path}")

        # Run design generator and keep objects for later preview toggles.
        nodes, channels, exclusion_zones, export_result = run_design_generator(cfg)

        # Persist job data for preview re-rendering.
        with (_job_paths(job_id)["pickle"]).open("wb") as f:
            pickle.dump(
                {
                    "nodes": nodes,
                    "channels": channels,
                    "exclusion_zones": exclusion_zones,
                    "cfg": cfg,
                },
                f,
            )

        # Ensure preview reflects requested mode (main.py currently renders a default preview; overwrite here).
        _render_preview_png(
            job_id=job_id,
            nodes=nodes,
            channels=channels,
            exclusion_zones=exclusion_zones,
            cfg=cfg,
            color_by_flow=req.colorByFlow,
        )

        _write_job_meta(job_id, req.colorByFlow)

        # print(f"[DEBUG] After generation - DXF exists: {dxf_path.exists()}, PNG exists: {preview_path.exists()}")

        # Verify outputs were created
        if not dxf_path.exists():
            raise HTTPException(500, f"DXF file not created at {dxf_path}")
        if not preview_path.exists():
            raise HTTPException(500, f"Preview PNG not created at {preview_path}")

        all_dxf_paths = [Path(p) for p in export_result["all"]]
        combined_path = Path(export_result["combined"])

        dxf_files = [
            DxfFile(
                name=p.name,
                url=f"api/download/dxf/{job_id}/{p.name}",
            )
            for p in all_dxf_paths
        ]

        return GenerateResponseV2(
            dxfUrl=f"api/download/dxf/{job_id}/{combined_path.name}",
            previewUrl=f"api/download/preview/{job_id}",
            jobId=job_id,
            dxfFiles=dxf_files,
            colorByFlow=req.colorByFlow,
        )

    except LayoutConvergenceError as e:
        raise HTTPException(422, str(e)) from e
    except HTTPException:
        raise


@app.get("/api/download/dxf/{job_id}")
async def download_dxf(job_id: str):
    """Download generated DXF file."""
    dxf_path = OUTPUT_DIR / f"design_{job_id}.dxf"
    if not dxf_path.exists():
        raise HTTPException(404, "DXF file not found")
    return FileResponse(dxf_path, media_type="application/dxf", filename=f"design_{job_id}.dxf")


@app.get("/api/download/dxf/{job_id}/{filename}")
async def download_dxf_file(job_id: str, filename: str):
    """Download a specific DXF file for a job (layer/depth/vias/combined)."""
    # basic safety: only allow files in OUTPUT_DIR with the expected prefix
    if not filename.startswith(f"design_{job_id}") or not filename.endswith(".dxf"):
        raise HTTPException(400, "Invalid filename")
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "DXF file not found")
    return FileResponse(path, media_type="application/dxf", filename=filename)


@app.get("/api/jobs/{job_id}/dxfs", response_model=List[DxfFile])
async def list_dxfs(job_id: str):
    files = _list_job_dxfs(job_id)
    if not files:
        raise HTTPException(404, "Job not found")
    return [DxfFile(name=p.name, url=f"api/download/dxf/{job_id}/{p.name}") for p in files]


@app.get("/api/download/preview/{job_id}")
async def download_preview(job_id: str):
    """Serve preview PNG."""
    preview_path = OUTPUT_DIR / f"preview_{job_id}.png"
    if not preview_path.exists():
        raise HTTPException(404, "Preview not found")
    return FileResponse(preview_path, media_type="image/png")


@app.post("/api/preview/{job_id}")
async def rerender_preview(job_id: str, colorByFlow: bool = False):
    if not _job_paths(job_id)["pickle"].exists():
        raise HTTPException(404, "Job data not found")
    return await _run_worker("preview", job_id, {"colorByFlow": colorByFlow})


def _rerender_preview(job_id: str, colorByFlow: bool = False):
    """Re-render preview for an existing job (fast), toggling layer vs flow-rate coloring."""
    paths = _job_paths(job_id)
    if not paths["pickle"].exists():
        raise HTTPException(404, "Job data not found")

    with paths["pickle"].open("rb") as f:
        data = pickle.load(f)

    cfg = data["cfg"]
    _render_preview_png(
        job_id=job_id,
        nodes=data["nodes"],
        channels=data["channels"],
        exclusion_zones=data["exclusion_zones"],
        cfg=cfg,
        color_by_flow=colorByFlow,
    )
    _write_job_meta(job_id, colorByFlow)
    return {"previewUrl": f"api/download/preview/{job_id}", "colorByFlow": bool(colorByFlow)}


@app.get("/health")
async def health():
    return {"status": "ok"}


if (GUI_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=GUI_DIST_DIR / "assets"), name="assets")


@app.get("/")
async def serve_gui():
    if not GUI_INDEX.exists():
        raise HTTPException(404, "GUI build not found. Run `npm run build` in gui/ first.")
    return FileResponse(GUI_INDEX)


@app.get("/{path:path}")
async def serve_gui_fallback(path: str):
    if path.startswith(("api/", "docs", "openapi.json", "redoc")):
        raise HTTPException(404, "Not found")
    if Path(path).suffix:
        raise HTTPException(404, "Static asset not found")
    return await serve_gui()
