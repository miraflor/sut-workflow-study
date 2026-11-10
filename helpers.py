# -*- coding: utf-8 -*-
"""Small helpers used by several files: write a CSV file, and show the time used."""
import time

START = time.time()          # when the program started (when this file was first imported)


def write_csv(file, rows):
    """Write a list of dicts (all with the same keys) as a CSV file."""
    with open(file, "w", encoding="utf-8") as fh:
        fh.write(",".join(rows[0]) + "\n")
        for r in rows:
            fh.write(",".join(f"{v:.6g}" if isinstance(v, float) else str(v) for v in r.values()) + "\n")


def minutes():
    """The time since the program started, in minutes, as text."""
    return f"{(time.time() - START) / 60:.1f} min"
