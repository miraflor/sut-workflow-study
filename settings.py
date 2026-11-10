# -*- coding: utf-8 -*-
"""
Settings of the study. Change the numbers here, and nowhere else: every other
file reads its settings from this file.
"""
from pathlib import Path

FOLDER = Path(__file__).resolve().parent       # the folder of the project

# Number of sectors: 240 (PSA's tables, data/tables) or 80 (data/tables80: the 80-sector SUT in
# data/Philippines_2018_80_Sector_Observed_SUT.xlsx, PSA's tables added up over PSA's 80 groups).
SECTORS = 80
TABLES = FOLDER / "data" / ("tables" if SECTORS == 240 else f"tables{SECTORS}")   # the SUT as CSV tables
OUT = FOLDER / ("results" if SECTORS == 240 else f"results{SECTORS}")             # all results are saved here

# --- Part 1: runs (Question 1, and the firing logs for Question 2) -----------
BATCHES = [52]                          # number of batches per year (each industry and each imported product);
                                        # 52 maps easily to weeks, but a batch is only a size, not a date
GRID = [2, 4, 9, 13, 17, 22, 26, 35, 52]   # opening stocks for Table 2, in weeks of use (52 = the whole year)
GRID_RUNS = 1000                        # simulated years for each grid stock
SEARCH_RUNS = 1000                      # simulated years for each stock tried in the search
SEARCH_STEPS = 6                        # how many times the search halves its interval
PATH_RUNS = 1000                        # saved years at the stock found by the search (or at LOG_STOCK)
REFERENCE_RUNS = 1000                   # saved years at 52 weeks of stock (the reference: nothing waits)
LOG_STOCK = {}                          # optional: a fixed stock for the firing logs instead of the search
                                        # result, in weeks, for example {52: 13.0}. Empty = use the search result.

BLOCK = 100                             # years per task in Part 1a and 1b (one task runs on one core)
FILE_RUNS = 200                         # years per saved file in Part 1c (one file is one task)
CORES = 5                               # how many processor cores to use
SEED = 2026                             # fixed seed, so that the results can be repeated exactly
D = 5                                   # whole-number resolution: a typical flow per batch is about 10**D units

# --- Part 2: analysis of the firing logs (Question 2) ------------------------
FDR = 0.05                              # false-discovery rate for the tests (industries in 2b, links in 2c)

# Checksums of the numbers in the tables made from PSA's files (the supply table, the
# use table and the imports; see data.fingerprint), for each number of sectors.
# The program prints a note if the tables differ.
DATA_SHA256 = {
    240: "a93a9e953c1f01ba1f629b631bcf6b7a98f2d4355fc6d454e7a28f10da4801ee",
    80: "cdcc80965eeac934ff74858e3ac4c2323e65c7e086f238a695408f1ee730c6af",
}
