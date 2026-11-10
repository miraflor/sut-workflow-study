# -*- coding: utf-8 -*-
"""
Simulated years (paper, Section 6).

Question: starting from an opening stock, can every batch of the year fire, if
the batches fire in a random order? Example: at each step, the program lists
every batch that can start now (an industry with batches left that has all its
inputs in stock, or an import delivery that is still due), picks one of them at
random, and fires it. The year either finishes (every batch fired) or stops
(some batches are left, but none can start).

Many years are simulated on several processor cores at the same time. Each
block of years has its own random stream, so the results do not depend on the
number of cores.
"""
import numpy as np
from joblib import Parallel, delayed

import settings
from yearplan import opening_stock


def simulate_year(plan, z0, rng, order=None):
    """Simulate the year once, from the opening stock z0, in a random order.

    At each step, the program lists every batch that can start now: an industry
    with batches left that has all its inputs in stock, or an imported product
    with deliveries left. It picks one of them at random, with equal chances,
    and fires it. The year ends when nothing can start: either every batch has
    fired (the year finished), or some batches are left (the year stopped).

    If `order` is given, the number of each fired transition is written into it:
    0 to (number of industries - 1) are industries (0-239 with 240 sectors),
    and the numbers after them are import deliveries.

    Returns: finished (True or False), the number of firings, and the number of
    steps (firings) at which some industry with batches left had to wait for an
    input. The final step of a stopped year, at which nothing fires, is not counted.
    """
    A, change, changed = plan["A"], plan["change"], plan["changed"]
    m, imported, N = plan["m"], plan["imported"], plan["N"]
    n_industries = A.shape[1]
    z = z0.copy()                                   # the stock of every product
    batches_left = np.full(n_industries, N)         # batches left for every industry
    deliveries_left = np.full(len(imported), N)     # deliveries left for every imported product
    industries_left = n_industries                  # industries that still have batches left
    lacks = z[:, None] < A                          # lacks[i, j] is True if industry j lacks product i
    n_lacking = lacks.sum(axis=0).astype(np.int64)  # how many inputs industry j lacks
    steps = 0
    blocked_steps = 0
    while True:
        can_run = np.flatnonzero((n_lacking == 0) & (batches_left > 0))
        can_deliver = np.flatnonzero(deliveries_left > 0)
        k = len(can_run) + len(can_deliver)
        if k == 0:                                  # nothing can start: the year is over
            break
        if len(can_run) < industries_left:          # some industry with batches left waits at this step
            blocked_steps += 1
        pick = int(rng.integers(k))                 # a random choice, equal chances
        # After a firing, only the products whose stock changed can change what
        # an industry lacks, so only those rows of `lacks` are checked again.
        if pick < len(can_run):                     # one batch of industry j
            j = can_run[pick]
            z += change[j]
            batches_left[j] -= 1
            if batches_left[j] == 0:
                industries_left -= 1
            rows = changed[j]
            new = z[rows, None] < A[rows]
            n_lacking += new.sum(axis=0) - lacks[rows].sum(axis=0)
            lacks[rows] = new
            if order is not None:
                order[steps] = j
        else:                                       # one import delivery of product i
            t = can_deliver[pick - len(can_run)]
            i = imported[t]
            z[i] += m[i]
            deliveries_left[t] -= 1
            new = z[i] < A[i]
            n_lacking += new.astype(np.int64) - lacks[i]
            lacks[i] = new
            if order is not None:
                order[steps] = n_industries + t
        steps += 1

    finished = steps == plan["total"]
    # Check: a finished year must end with the opening stock plus final demand (paper, Section 5.3).
    if finished and not np.array_equal(z, z0 + N * plan["f_tilde"]):
        raise RuntimeError("Check failed: a finished year must leave z0 + N f.")
    return finished, steps, blocked_steps


def run_block(plan, weeks, key, runs, seed, file=None):
    """Simulate `runs` years from an opening stock of `weeks` weeks of use.

    Each block has its own random stream, made from `seed` and `key` (which
    part, how many batches, which stock, which block). So the results are the
    same whatever the number of cores. If `file` is given, the firing logs are
    saved. Returns: finished years, total firings, total blocked steps.
    """
    rng = np.random.default_rng(np.random.SeedSequence([seed, *key]))
    z0 = opening_stock(plan, weeks)
    # Check: with a whole year of stock (52 weeks), no batch waits, so no year can stop.
    whole_year = bool((z0 >= plan["N"] * plan["A"].sum(axis=1)).all())
    if file is not None:
        order = np.full((runs, plan["total"]), -1, dtype=np.int16)   # -1 after a year stops
        steps = np.zeros(runs, dtype=np.int32)
        blocked = np.zeros(runs, dtype=np.int32)
    finished = firings = blocked_total = 0
    for r in range(runs):
        ok, k, b = simulate_year(plan, z0, rng, None if file is None else order[r])
        if whole_year and not ok:
            raise RuntimeError("Check failed: a year with a whole year of stock stopped.")
        finished += ok
        firings += k
        blocked_total += b
        if file is not None:
            steps[r] = k
            blocked[r] = b
    if file is not None:
        np.savez_compressed(file, order=order, steps=steps, finished=steps == plan["total"],
                            blocked=blocked, z0=z0)
    return finished, firings, blocked_total


def run_stock(plan, weeks, part, runs, block, folder=None, cores=None):
    """Simulate `runs` years from an opening stock of `weeks` weeks of use, split into blocks of
    `block` years that run at the same time on several cores (settings.CORES,
    unless `cores` is given). With `folder`, each block is saved as one file.
    Returns: finished years, firings, blocked steps."""
    cores = settings.CORES if cores is None else cores
    tasks = []
    for b in range(-(-runs // block)):              # the number of blocks, rounded up
        key = (part, plan["N"], round(weeks * 1_000_000), b)
        file = None if folder is None else folder / f"part_{b:03d}.npz"
        tasks.append(delayed(run_block)(plan, weeks, key, min(block, runs - b * block), settings.SEED, file))
    done = Parallel(n_jobs=cores)(tasks)
    return sum(d[0] for d in done), sum(d[1] for d in done), sum(d[2] for d in done)
