#!/usr/bin/env python3
"""Quick test to verify DXF generation works"""

import sys
sys.path.insert(0, '/Users/maria/Documents/GitHub/OoC_GG/src')

from config import Config
from main import main

# Create test config - using default params that are known to work
cfg = Config()
# Use defaults from Config class which should work

# Set output paths
cfg.output_dxf_path = "/Users/maria/Documents/GitHub/OoC_GG/backend/output/test_design.dxf"
cfg.output_preview_path = "/Users/maria/Documents/GitHub/OoC_GG/backend/output/test_preview.png"

print("Starting design generation...")
try:
    nodes, channels, exclusion_zones = main(cfg)
    print(f"Design generation completed successfully!")
    print(f"DXF should be at: {cfg.output_dxf_path}")
    print(f"Preview should be at: {cfg.output_preview_path}")
    
    # Check if files exist
    from pathlib import Path
    if Path(cfg.output_dxf_path).exists():
        print(f"✓ DXF file created! Size: {Path(cfg.output_dxf_path).stat().st_size} bytes")
    else:
        print("✗ DXF file NOT found")
        
    if Path(cfg.output_preview_path).exists():
        print(f"✓ Preview created! Size: {Path(cfg.output_preview_path).stat().st_size} bytes")
    else:
        print("✗ Preview NOT found")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
