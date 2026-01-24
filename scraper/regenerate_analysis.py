
import sys
import os

# Add current dir to path to import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrape_and_upload import generate_analysis_json

print("Regenerating analysis.json...")
try:
    generate_analysis_json()
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
