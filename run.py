# -*- coding: utf-8 -*-
"""
Can a year of production be completed, and in what order?
The 2018 Philippine Supply and Use Tables as a year-plan workflow net.

Use (from a terminal, in this folder):
    python run.py             everything: Part 1 (runs), then Part 2 (analysis)
    python run.py runs        only Part 1
    python run.py logs        only Part 1c, at the stocks given in LOG_STOCK (settings.py)
    python run.py analysis    only Part 2 (uses the files saved by Part 1)

The settings (batches, stocks, runs, cores, seed) are in settings.py.
The results are saved in the folder "results" (see README.md).
"""
import importlib
import sys
import time

import helpers
import settings
from data import fingerprint, load_tables
from helpers import minutes
from part1_runs import part1_runs
from part2_analysis import part2_analysis


def main(what="all"):
    if what not in ("all", "runs", "logs", "analysis"):
        raise SystemExit(__doc__)
    # In Spyder or a notebook the program stays loaded between runs, so read
    # settings.py again (to use any change made since the last run), and start the clock.
    importlib.reload(settings)
    helpers.START = time.time()
    sut = load_tables(settings.TABLES)
    print(f"Read the tables in {settings.TABLES}: {sut.n_products} products x {sut.n_industries} industries")
    if fingerprint(sut) != settings.DATA_SHA256.get(settings.SECTORS):
        print("Note: these tables differ from the tables made from PSA's files, so the numbers may differ.")
    settings.OUT.mkdir(exist_ok=True)

    if what in ("all", "runs"):
        part1_runs(sut)
    if what == "logs":
        part1_runs(sut, only_logs=True)
    if what in ("all", "analysis"):
        part2_analysis(sut)
    print(f"\nDone in {minutes()}.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
