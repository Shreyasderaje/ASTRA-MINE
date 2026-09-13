"""Make the astra package importable when pytest runs from anywhere."""
import os
import sys

SOFTWARE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SOFTWARE_DIR not in sys.path:
    sys.path.insert(0, SOFTWARE_DIR)
