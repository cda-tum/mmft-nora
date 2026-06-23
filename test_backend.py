from pathlib import Path

from src.config import Config
from src.main import main


def test_backend_mode_generates_design_files(tmp_path):
    cfg = Config(no_of_modules_x=1, no_of_modules_y=1)
    cfg.output_dxf_path = str(tmp_path / "test_design.dxf")
    cfg.output_preview_path = str(tmp_path / "test_preview.png")

    nodes, channels, exclusion_zones, export_result = main(cfg)

    assert nodes
    assert channels
    assert export_result["combined"] == cfg.output_dxf_path
    assert Path(cfg.output_dxf_path).exists()
    assert Path(cfg.output_preview_path).exists()
