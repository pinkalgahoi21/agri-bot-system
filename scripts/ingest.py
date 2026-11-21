import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from services.vector_rag import build, export_seed

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--export-seed", action="store_true", help="Package a completed index for offline deployment startup")
    args = parser.parse_args()
    build(reset=args.reset)
    if args.export_seed:
        export_seed()
