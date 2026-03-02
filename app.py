import runpy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ui"))
runpy.run_path(os.path.join(os.path.dirname(__file__), "ui", "coach_bot_ui.py"), run_name="__main__")