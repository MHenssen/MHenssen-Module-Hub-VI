"""Entry point for PI Portfolio Explorer.

Run with no arguments to open the setup window; `python run.py sync` and
`python run.py serve --port 8010` are the same commands the window launches.
"""
from pi_portfolio.cli import main

if __name__ == "__main__":
    main()
