"""Run one calculation in a process the API can terminate on timeout."""
import json
import logging
import sys
from contextlib import redirect_stdout
from pathlib import Path

from backend import app
from fastapi import HTTPException


def main():
    operation, job_id = sys.argv[1:]
    payload = json.load(sys.stdin)
    app.OUTPUT_DIR = Path(payload["output_dir"])
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("src.main").setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)
    try:
        # Scientific routines print diagnostics; reserve stdout for the result.
        with redirect_stdout(sys.stderr):
            if operation == "generate":
                result = app._generate_design(app.GenerateRequest(**payload["parameters"]), job_id).model_dump()
            elif operation == "preview":
                result = app._rerender_preview(job_id, **payload["parameters"])
            else:
                raise ValueError(f"Unknown operation: {operation}")
    except HTTPException as exc:
        result = {"error": exc.detail, "status_code": exc.status_code}
    except Exception:
        app.logger.exception("Calculation failed operation=%s job=%s", operation, job_id)
        result = {"error": "The calculation failed. Please check the parameters and try again.", "status_code": 500}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
