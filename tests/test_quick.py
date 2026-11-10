# -*- coding: utf-8 -*-
"""
Quick checks of the code (less than a minute). Run them from the project folder:

    python -m pytest              (if pytest is installed)
    python tests/test_quick.py    (without pytest)

Most checks compare the code with numbers stated in the paper. The last check
runs a very small version of the whole study, to show that every part runs.
"""
import functools
import itertools
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))     # the project folder

import settings                                                       # noqa: E402
from data import fingerprint, load_tables                            # noqa: E402
from firing_stats import (benjamini_hochberg, dag_links, earliness,  # noqa: E402
                          firing_moments, pairwise_order)
from simulation import run_stock, simulate_year                       # noqa: E402
from yearplan import build_plan, opening_stock, pesos                 # noqa: E402

SUT = load_tables(settings.FOLDER / "data" / "tables")       # the 240-sector tables of the paper


# --- Data (paper, Section 4) -------------------------------------------------

def test_data_are_the_papers():
    """The tables give the same numbers as PSA's workbook used in the paper."""
    assert fingerprint(SUT) == settings.DATA_SHA256[240]
    assert SUT.V.shape == SUT.U.shape == (240, 240)
    assert (SUT.V >= 0).all() and (SUT.U >= 0).all()
    assert (SUT.V != 0).sum() == 5648 and (SUT.U != 0).sum() == 12507
    assert (SUT.M > 0).sum() == 218                       # 218 products are imported


def test_80_sectors_add_up():
    """The 80-sector tables (from the 80-sector SUT workbook) are the 240-sector tables
    added up over PSA's 80 groups, up to the last digit of floating-point arithmetic."""
    from aggregate import TOLERANCE, compare
    sut80 = load_tables(settings.FOLDER / "data" / "tables80")
    assert fingerprint(sut80) == settings.DATA_SHA256[80]
    assert sut80.V.shape == sut80.U.shape == (80, 80)
    assert all(difference < TOLERANCE for difference in compare(80).values())


# --- Whole-number units and opening stock (paper, Section 5, Table 3) -------

def test_rounding_table():
    """The numbers of the paper's table 'Effect of rounding to whole units'."""
    for N, lost, value_share, largest in [(12, 70, 4.5e-8, 1.2e11), (52, 72, 6.5e-8, 5.4e10)]:
        plan = build_plan(SUT, N, settings.D)
        A = plan["A"]
        B = plan["change"].T + A                              # outputs per batch
        zero = (SUT.U > 0) & (A == 0)                         # input links that round to zero
        assert zero.sum() == lost
        assert round(100 * SUT.U[zero].sum() / SUT.U.sum(), 9) == value_share     # in percent
        assert not ((SUT.V > 0) & (B == 0)).any()             # no output link lost
        assert not ((SUT.M > 0) & (plan["m"] == 0)).any()     # no import delivery lost
        assert (A.sum(axis=0) > 0).all()                      # no industry lost all its inputs
        assert (plan["f_tilde"] >= 0).all()                   # no negative final demand
        assert float(f"{max(A.max(), B.max(), plan['m'].max()):.1e}") == largest
        assert plan["total"] == N * (240 + 218)               # 5,496 and 23,816 firings


def test_opening_stock_in_pesos():
    """One week of stock is worth 0.35 trillion pesos, 52 weeks 18.27 (paper, Section 5.4)."""
    for N in (12, 52):
        plan = build_plan(SUT, N, settings.D)
        assert round(pesos(plan, opening_stock(plan, 1)) / 1e6, 2) == 0.35
        assert round(pesos(plan, opening_stock(plan, 52)) / 1e6, 2) == 18.27
    plan = build_plan(SUT, 52, settings.D)                      # with 52 batches, one week of use
    assert np.array_equal(opening_stock(plan, 1), plan["A"].sum(axis=1))   # = one batch of every industry


# --- The small example (paper, Section 2, Table 2) ---------------------------

def toy_plan():
    """The small example as a year plan: 3 products, 3 industries, 3 batches each, no imports."""
    A = np.array([[1, 2, 1],        # crops used by one batch of Farming, Factory, Power plant
                  [1, 1, 2],        # goods used
                  [2, 2, 1]])       # power used
    B = 6 * np.eye(3, dtype=np.int64)   # each batch makes 6 units of its own product
    N = 3
    return dict(N=N, A=A, m=np.zeros(3, dtype=np.int64), imported=np.array([], dtype=np.int64),
                f_tilde=B.sum(axis=1) - A.sum(axis=1), change=np.ascontiguousarray((B - A).T),
                changed=[np.flatnonzero(B[:, j] - A[:, j]) for j in range(3)], total=3 * N)


def orders_that_complete(plan, z0):
    """How many of the 1,680 orders of the 9 batches complete the year."""
    count = 0
    for order in set(itertools.permutations([0, 0, 0, 1, 1, 1, 2, 2, 2])):
        z = np.array(z0)
        for j in order:
            if (z < plan["A"][:, j]).any():
                break
            z = z + plan["change"][j]
        else:
            count += 1
    return count


def share_of_random_runs(plan, z0):
    """The exact chance that a random run completes the year (each step picks one
    of the batches that can start, with equal chances)."""
    A, change, N = plan["A"], plan["change"], plan["N"]

    @functools.lru_cache(maxsize=None)
    def chance(fired):                                  # fired: batches fired by each industry
        if all(f == N for f in fired):
            return 1.0
        z = np.array(z0) + sum(f * change[j] for j, f in enumerate(fired))
        can = [j for j in range(3) if fired[j] < N and (z >= A[:, j]).all()]
        if not can:
            return 0.0                                  # the year stops here
        return sum(chance(tuple(f + (k == j) for k, f in enumerate(fired))) for j in can) / len(can)

    return chance((0, 0, 0))


def test_small_example():
    """The paper's table 'Completion by opening stock', and that the simulation agrees with it."""
    plan = toy_plan()
    rng = np.random.default_rng(1)
    for z0, orders, share in [((3, 3, 4), 0, 0.00), ((4, 4, 5), 360, 0.21), ((6, 6, 8), 1122, 0.57),
                              ((9, 9, 12), 1620, 0.84), ((10, 10, 13), 1680, 1.00)]:
        assert orders_that_complete(plan, z0) == orders
        exact = share_of_random_runs(plan, z0)
        assert round(exact, 2) == share
        runs = 2000
        simulated = np.mean([simulate_year(plan, np.array(z0, dtype=np.int64), rng)[0] for _ in range(runs)])
        assert abs(simulated - exact) <= 4 * np.sqrt(exact * (1 - exact) / runs) + 1e-12
    # More stock does not always help: no run stops from (10, 10, 9), some runs stop from (10, 10, 10);
    # even on the scale of the table, the share falls from (6, 6, 7) to (6, 6, 8).
    assert share_of_random_runs(plan, (10, 10, 9)) == 1.0
    assert share_of_random_runs(plan, (10, 10, 10)) < 1.0
    assert round(share_of_random_runs(plan, (6, 6, 7)), 2) == 0.63


def test_waiting_counts_only_steps_that_fire():
    """A year that stops at once has no firing and no waiting step; waiting never exceeds firings."""
    plan = toy_plan()
    rng = np.random.default_rng(3)
    assert simulate_year(plan, np.zeros(3, dtype=np.int64), rng) == (False, 0, 0)
    for _ in range(200):
        finished, steps, blocked = simulate_year(plan, np.array([4, 4, 5]), rng)
        assert blocked <= steps


# --- Simulation (paper, Sections 5.5 and 6) ----------------------------------

def test_whole_year_of_stock_never_waits():
    """With 52 weeks of stock (the whole year's use), no batch waits and every year finishes.
    (simulate_year itself checks that a finished year ends at z0 + N f.)"""
    plan = build_plan(SUT, 12, settings.D)
    z0 = opening_stock(plan, 52)
    rng = np.random.default_rng(1)
    for _ in range(3):
        finished, steps, blocked = simulate_year(plan, z0, rng)
        assert finished and steps == plan["total"] and blocked == 0


def test_same_results_on_any_number_of_cores():
    """Each block of years has its own random stream, so 1 core and 2 cores give the same results."""
    plan = build_plan(SUT, 12, settings.D)
    one = run_stock(plan, 13.0, 9, runs=6, block=2, cores=1)
    two = run_stock(plan, 13.0, 9, runs=6, block=2, cores=2)
    assert one == two


# --- Analysis of the firing logs (paper, Section 7) --------------------------

def test_firing_moments():
    """The moment of a firing is (step + 1) / (number of firings in the year)."""
    # 2 industries (0 and 1) and 1 imported product (2), 2 batches each: 6 firings.
    logs = np.array([[0, 2, 1, 1, 0, 2]])
    moments = firing_moments(logs, N=2, n_industries=2)
    assert np.allclose(moments[0], [[1 / 6, 5 / 6], [3 / 6, 4 / 6]])


def test_benjamini_hochberg():
    p = np.array([0.01, 0.04, 0.03, 0.2])
    assert np.allclose(benjamini_hochberg(p), [0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.2])


def test_order_found_only_when_present():
    """A made-up example. With no order, no link is found. When industry 0 fires
    earlier than the others, it is found as earlier, with links 0 -> b for every
    other industry b, and no link into 0. (Other links can appear by chance: the
    false-discovery rate allows about 5% of the links found to be false.)"""
    rng = np.random.default_rng(7)
    years, n, N = 40, 6, 12
    moments = np.sort(rng.uniform(0, 1, (years, n, N)), axis=2)       # no order
    assert dag_links(*pairwise_order(moments), 0.05) == []
    moments[:, 0, :] *= 0.8                                           # industry 0 fires earlier
    reference = np.sort(rng.uniform(0, 1, (years, n, N)), axis=2)    # reference years: no order
    lead, _, q = earliness(moments, reference)
    assert lead[0] < 0 and q[0] < 0.05
    links = dag_links(*pairwise_order(moments), 0.05)
    found = {(a, b) for a, b, *_ in links}
    assert {(0, b) for b in range(1, n)} <= found                    # every link 0 -> b is found
    assert not any(b == 0 for a, b in found)                          # no link into industry 0


# --- A very small run of the whole study -------------------------------------

def test_small_study_runs():
    """Part 1 and Part 2 with very small settings, in a temporary folder."""
    from part1_runs import part1_runs
    from part2_analysis import part2_analysis
    # 12 batches to be quick; LOG_STOCK = 26 weeks, so that enough of the 12 saved years finish for Part 2.
    small = dict(BATCHES=[12], GRID=[13, 52], GRID_RUNS=4, SEARCH_RUNS=4, SEARCH_STEPS=1, PATH_RUNS=12,
                 REFERENCE_RUNS=12, BLOCK=2, FILE_RUNS=6, CORES=2, LOG_STOCK={12: 26.0})
    saved = {name: getattr(settings, name) for name in list(small) + ["OUT"]}
    folder = Path(tempfile.mkdtemp())
    try:
        for name, value in small.items():
            setattr(settings, name, value)
        settings.OUT = folder
        part1_runs(SUT)
        part2_analysis(SUT)
        for file in ["table2.csv", "search.csv", "chosen_stock.csv",
                     "analysis_batches12/summary.txt", "analysis_batches12/sequence.csv"]:
            assert (folder / file).exists(), file
    finally:
        for name, value in saved.items():
            setattr(settings, name, value)
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok ", name)
