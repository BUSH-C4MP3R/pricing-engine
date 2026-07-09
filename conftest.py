"""Ensures the project root is on sys.path for all tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))