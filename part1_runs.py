# -*- coding: utf-8 -*-
"""
Part 1. Runs (paper, Section 6), for each number of batches in settings.BATCHES.

  1a. Table 2 (Question 1): for each opening stock in GRID (in weeks of use),
      simulate GRID_RUNS years and count how many finish.
  1b. Search (Question 1): starts between the largest grid stock where some year
      stopped and the next grid stock up, and halves that interval SEARCH_STEPS
      times. More stock can make some orders fail (paper, Section 2), so the
      stocks that complete every year need not form one interval. The result,
      w*, is therefore defined by the stocks tried: the smallest stock tried
      above the largest stock tried at which some year stopped. Every stock
      tried at w* or above completed all of its years.
  1c. Firing logs (for Question 2): simulate PATH_RUNS years at the stock found
      by the search (or at LOG_STOCK), and REFERENCE_RUNS years at 52 weeks of
      stock (the whole year's use), where no batch ever has to wait. For every year, save the order in
      which the batches fired.

Saved in settings.OUT: table2.csv, search.csv, chosen_stock.csv and paths/.
"""
import json

import numpy as np

import settings
from data import fingerprint
from helpers import minutes, write_csv
from simulation import run_stock
from yearplan import build_plan, opening_stock, pesos


def wilson(k, n, z=1.96):
    """The 95% Wilson interval for the share k / n."""
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def part1_runs(sut, only_logs=False):
    """Part 1. With only_logs=True, only the firing logs (1c) are made, at the
    stocks given in settings.LOG_STOCK."""
    OUT = settings.OUT
    n_industries = sut.n_industries
    table, search, chosen = [], [], []
    for N in settings.BATCHES:
        plan = build_plan(sut, N, settings.D)
        print(f"\n=== Part 1, {N} batches: {plan['total']:,} firings in a finished year")

        if only_logs:
            if N not in settings.LOG_STOCK:
                print(f"   No stock for {N} batches in LOG_STOCK: skipped.")
                continue
            log_weeks = settings.LOG_STOCK[N]
        else:
            # --- 1a. Table 2: the share of years that finish, for every grid stock.
            GRID, GRID_RUNS = settings.GRID, settings.GRID_RUNS
            stopped = {}
            for weeks in GRID:
                fin, firings, blocked = run_stock(plan, weeks, 1, GRID_RUNS, settings.BLOCK)
                stopped[weeks] = GRID_RUNS - fin
                low, high = wilson(fin, GRID_RUNS)
                table.append(dict(batches=N, weeks=float(weeks),
                                  stock_trillion_pesos=pesos(plan, opening_stock(plan, weeks)) / 1e6,
                                  runs=GRID_RUNS, finished=fin, stopped=GRID_RUNS - fin,
                                  share=fin / GRID_RUNS, low=low, high=high,
                                  share_of_steps_blocked=blocked / firings))
                print(f"1a Table 2  weeks {weeks:>5g}: {fin:>5} of {GRID_RUNS} finished; "
                      f"{blocked / firings:.1%} of steps had a waiting industry | {minutes()}")

            # --- 1b. Search for w*: the smallest stock tried above the largest stock tried
            # at which some year stopped (see the top of this file).
            # lo = the largest grid stock where some year stopped;
            # hi = the next grid stock up, where no year stopped (52 weeks never stop).
            SEARCH_RUNS = settings.SEARCH_RUNS
            with_stop = [a for a in GRID if stopped[a] > 0]
            lo = max(with_stop) if with_stop else 0.0
            hi = min([a for a in GRID if a > lo and stopped[a] == 0] or [52.0])
            for k in range(1, settings.SEARCH_STEPS + 1):
                mid = (lo + hi) / 2                     # try the middle of the interval
                fin, _, _ = run_stock(plan, mid, 2, SEARCH_RUNS, settings.BLOCK)
                search.append(dict(batches=N, step=k, weeks=mid, runs=SEARCH_RUNS, stopped=SEARCH_RUNS - fin))
                if fin < SEARCH_RUNS:                   # some year stopped: w* lies above mid
                    lo = mid
                else:                                   # no year stopped: w* is mid or below
                    hi = mid
                print(f"1b Search   weeks {mid:>8.5g}: {SEARCH_RUNS - fin:>5} of {SEARCH_RUNS} stopped | {minutes()}")
            stock = pesos(plan, opening_stock(plan, hi)) / 1e6
            chosen.append(dict(batches=N, weeks=hi, stock_trillion_pesos=stock, largest_weeks_with_a_stop=lo,
                               check_runs=0, check_runs_stopped=0))
            print(f"   Chosen stock: {hi:g} weeks ({stock:.3f} trillion pesos)")
            log_weeks = settings.LOG_STOCK.get(N, hi)   # LOG_STOCK, if given, replaces the search result

        # --- 1c. Firing logs at the chosen stock, and at 52 weeks for reference.
        for name, weeks, runs in [("chosen", log_weeks, settings.PATH_RUNS),
                                  ("reference", 52.0, settings.REFERENCE_RUNS)]:
            if runs == 0:
                continue
            folder = OUT / "paths" / f"batches{N}_{name}"
            folder.mkdir(parents=True, exist_ok=True)
            for old in folder.glob("part_*.npz"):   # remove files from an earlier run
                old.unlink()
            with open(folder / "transitions.csv", "w", encoding="utf-8") as fh:
                fh.write("transition,kind,code,name\n")
                for j in range(n_industries):
                    fh.write(f'{j},industry,{sut.industry_codes[j]},"{sut.industry_names[j]}"\n')
                for t, i in enumerate(plan["imported"]):
                    fh.write(f'{n_industries + t},import,{sut.product_codes[i]},"{sut.product_names[i]}"\n')
            info = dict(batches=N, weeks=weeks, runs=runs, years_per_file=settings.FILE_RUNS, seed=settings.SEED,
                        stock_trillion_pesos=pesos(plan, opening_stock(plan, weeks)) / 1e6,
                        firings_in_finished_year=plan["total"], data_sha256=fingerprint(sut))
            (folder / "info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
            fin, firings, blocked = run_stock(plan, weeks, 3, runs, settings.FILE_RUNS, folder)
            if name == "chosen" and not only_logs and weeks == chosen[-1]["weeks"]:
                # w* was chosen because its search runs had no stop, so those runs cannot
                # test it. The firing-log years are new runs at w*: if none of them stops,
                # the chance that a random year stops at w* is below 3 / runs (95% confidence).
                chosen[-1].update(check_runs=runs, check_runs_stopped=runs - fin)
            print(f"1c Logs     weeks {weeks:>5g}: {fin:>5} of {runs} finished; "
                  f"{blocked / firings:.1%} of steps had a waiting industry | {minutes()}")

    if not only_logs:
        write_csv(OUT / "table2.csv", table)
        write_csv(OUT / "search.csv", search)
        write_csv(OUT / "chosen_stock.csv", chosen)
        print(f"\nPart 1 saved in {OUT}: table2.csv, search.csv, chosen_stock.csv, paths/")
