"""Run from any directory: python -I -B /path/to/V5/run_standalone.py ..."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent/'src'))
from v5_shadow.standalone import main
if __name__ == '__main__':raise SystemExit(main())
