import os
import sys

# Add the project root and backend directory to sys.path so tests can import modules
BACKEND_ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))
sys.path.extend([PROJECT_ROOT, BACKEND_ROOT])
