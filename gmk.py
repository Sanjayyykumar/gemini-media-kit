#!/usr/bin/env python3
"""Launcher: `python gmk.py <command>`  (see README.md, or `python gmk.py -h`)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gemini_media_kit.cli import main

if __name__ == "__main__":
    main()
