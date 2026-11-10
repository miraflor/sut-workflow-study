# -*- coding: utf-8 -*-
"""
Check the 80-sector tables (data/tables80) against PSA's 240-sector tables (data/tables).

Usage:  python aggregate.py

The check adds up the 240-sector supply table, use table and imports over the 80
groups of PSA's 2018 Input-Output Industry Classification (data/classification.csv),
in the same way for products (rows) and industries (columns):

    V80 = G' V G,   U80 = G' U G,   M80 = G' M,   G[i, g] = 1 if code i is in group g,

and compares the result with data/tables80. The two must agree up to the last digit
of floating-point arithmetic: adding the same numbers in another order can change
the last binary digit, so the largest relative difference must be below 1e-12.
"""
import csv
import sys
from pathlib import Path

import numpy as np

from data import load_tables

FOLDER = Path(__file__).resolve().parent
TOLERANCE = 1e-12


def grouping(level):
    """The 240 codes, the group codes (in order), and G[i, g] = 1 if code i is in group g."""
    with open(FOLDER / "data" / "classification.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    groups = list(dict.fromkeys(row[f"code_{level}"] for row in rows))
    G = np.zeros((len(rows), len(groups)))
    for i, row in enumerate(rows):
        G[i, groups.index(row[f"code_{level}"])] = 1.0
    return [row["code_240"] for row in rows], groups, G


def compare(level=80):
    """For V, U and M: the largest relative difference between data/tables{level}
    and the 240-sector tables added up over the groups."""
    sut240 = load_tables(FOLDER / "data" / "tables")
    sut = load_tables(FOLDER / "data" / f"tables{level}")
    codes240, groups, G = grouping(level)
    if codes240 != sut240.product_codes or groups != sut.product_codes:
        raise ValueError("the codes of the tables do not match data/classification.csv")
    result = {}
    for name, small, added_up in [("supply", sut.V, G.T @ sut240.V @ G),
                                  ("use", sut.U, G.T @ sut240.U @ G),
                                  ("imports", sut.M, G.T @ sut240.M)]:
        scale = np.where(added_up == 0, 1.0, np.abs(added_up))   # a zero cell must stay exactly zero
        result[name] = float((np.abs(small - added_up) / scale).max())
    return result


if __name__ == "__main__":
    result = compare(80)
    for name, difference in result.items():
        print(f"{name:<8} largest relative difference: {difference:.1e}")
    if all(d < TOLERANCE for d in result.values()):
        print("OK: the 80-sector tables are the 240-sector tables added up over PSA's 80 groups.")
    else:
        sys.exit("The 80-sector tables differ from the added-up 240-sector tables.")
