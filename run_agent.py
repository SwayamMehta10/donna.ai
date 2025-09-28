"""
Entry point for running the AI Voice Agent
This file should be run from the project root directory
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import and run the main function
from src.main import run_example

if __name__ == "__main__":
    run_example()