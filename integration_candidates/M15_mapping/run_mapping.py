"""Standalone M15 delivery entry point; no scheduler or provider calls."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent/'runtime/V5/src'))
from v5_shadow.m15_delivery import main
if __name__ == '__main__':
    main()
