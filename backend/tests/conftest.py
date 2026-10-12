import os
import sys
from pathlib import Path

# Add backend to path for tests
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
