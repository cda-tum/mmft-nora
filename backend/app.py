import uuid
from pathlib import Path
import sys
import json
import pickle
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add repository root to path so the src package imports consistently.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.main import main as run_design_generator
from src.graph_output import plot_network

app = FastAPI(title="OoC Design Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


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
    paths["meta"].write_text(json.dumps(meta, indent=2))


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
    fig.savefig(paths["preview"], dpi=150, bbox_inches="tight")
    plt.close(fig)
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

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Design generation error: {str(e)}")


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
