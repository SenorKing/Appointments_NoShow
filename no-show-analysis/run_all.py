"""Run the full pipeline: clean -> SQL -> charts -> model.   python run_all.py"""
import runpy
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))

for step in ["clean", "run_sql", "eda", "model", "export_dashboard_data"]:
    print(f"\n{'=' * 20} {step} {'=' * 20}")
    runpy.run_path(str(SRC / f"{step}.py"), run_name="__main__")
