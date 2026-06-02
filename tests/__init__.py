# to run: python -m pytest -v
import sys, os
# sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Path to project root (where src/ is located)
project_root = os.path.dirname(os.path.dirname(__file__))

# Add src/ to Python path
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)