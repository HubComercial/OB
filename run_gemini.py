#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.gemini_advisor import run_analysis

if __name__ == "__main__":
    run_analysis()
