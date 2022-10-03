from .main import run_app
from .main_cli import run_cli
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli()
    else:
        run_app()