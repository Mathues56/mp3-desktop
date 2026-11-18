"""Run the source checkout."""

import sys

from mp3_desktop.ui import main as classic_main
from mp3_desktop.web import main as web_main

if __name__ == "__main__":
    (classic_main if "--classic" in sys.argv else web_main)()
