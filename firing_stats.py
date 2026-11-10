# -*- coding: utf-8 -*-
"""
Statistics of the firing logs (paper, Section 7).

Question: in the years that finish, do some industries fire earlier than
others, and does industry a's n-th firing tend to come before industry b's
n-th firing? Example: with 12 batches, each industry fires 12 times in a
finished year. If industry a's 1st, 2nd, ..., 12th firings come before those of
industry b in clearly more than half of the cases, the timing DAG gets a link
a -> b.

Terms:
  moment     the time of a firing as a share of the year: step / (number of
             firings in the year); 0 = start, 1 = end
  lead       how much earlier (negative) or later (positive) an industry fires
             than in the reference years, in weeks
  q-value    for each test, the lowest false-discovery rate at which it counts
             as a finding (Benjamini and Hochberg, 1995)
"""
import networkx as nx
import numpy as np
from scipy.stats import t as t_dist


def load_logs(folder):
    """Read the saved firing logs in a folder. Keeps the finished years only.
    Returns the logs, the number of years, which years finished, and the share
    of blocked steps in every year."""
    logs, finished, blocked_share = [], [], []
    for file in sorted(folder.glob("part_*.npz")):
        d = np.load(file)
        logs.append(d["order"][d["finished"]])
        finished.append(d["finished"])
        blocked_share.append(d["blocked"] / d["steps"])
    finished = np.concatenate(finished)
    return np.concatenate(logs), len(finished), finished, np.concatenate(blocked_share)


def firing_moments(logs, N, n_industries):
    """For every finished year, every industry and every n = 1, ..., N: the moment
    of the industry's n-th firing, as a share of the year (0 = start, 1 = end).

    Result: moments[year, industry, n - 1].
    """
    years, total = logs.shape
    moments = np.empty((years, n_industries, N), dtype=np.float32)
    for y in range(years):
        row = logs[y]
        steps = np.flatnonzero(row < n_industries)     # the steps at which an industry fired
        who = row[steps]                               # which industry fired at each of those steps
        # Sort by industry, keeping the time order inside each industry. In a
        # finished year every industry fired exactly N times, so the result can
        # be cut into one row of N moments per industry.
        by_industry = np.argsort(who, kind="stable")
        moments[y] = ((steps[by_industry] + 1) / total).reshape(n_industries, N)
    return moments


def t_test(values, target):
    """Test whether the average of `values` (one value per year, in the rows)
    differs from `target`. Returns the t-score and the two-sided p-value."""
    years = len(values)
    spread = values.std(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (values.mean(axis=0) - target) / (spread / np.sqrt(years))
    t = np.nan_to_num(t)               # no spread at all only happens when there is nothing to test
    return t, 2 * t_dist.sf(np.abs(t), df=years - 1)


def benjamini_hochberg(p):
    """q-values: for each test, the lowest false-discovery rate at which it counts as a finding."""
    m = len(p)
    rank = np.argsort(p)
    scaled = p[rank] * m / np.arange(1, m + 1)
    q_sorted = np.minimum.accumulate(scaled[::-1])[::-1]
    q = np.empty(m)
    q[rank] = np.minimum(q_sorted, 1.0)
    return q


def earliness(moments, ref_moments):
    """How early each industry fires, compared with the reference years: its lead
    in weeks (negative = earlier), the half-width of its 95% interval, and its
    q-value (false-discovery rate over all industries).

    Each year gives one value per industry: the average moment of its firings.
    Industry j's yearly values are compared with the yearly values of the
    reference years (the average over all industries in each reference year)
    with Welch's two-sample t-test, so the uncertainty of the reference is
    included."""
    x = moments.mean(axis=2)                           # years x industries: average moment of the firings
    r = ref_moments.mean(axis=(1, 2))                  # one value per reference year
    n1, n2 = len(x), len(r)
    v1, v2 = x.var(axis=0, ddof=1) / n1, r.var(ddof=1) / n2    # squared standard errors of the two means
    se = np.sqrt(v1 + v2)
    diff = x.mean(axis=0) - r.mean()                   # a share of the year
    with np.errstate(divide="ignore", invalid="ignore"):
        df = (v1 + v2) ** 2 / (v1 ** 2 / (n1 - 1) + v2 ** 2 / (n2 - 1))   # Welch-Satterthwaite
        t = diff / se
    df = np.where(np.isfinite(df), df, n1 + n2 - 2)
    t = np.nan_to_num(t)                               # no spread at all only happens when there is nothing to test
    p = 2 * t_dist.sf(np.abs(t), df=df)
    half = t_dist.ppf(0.975, df) * se
    return diff * 52, half * 52, benjamini_hochberg(p)


def pairwise_order(moments):
    """For every pair of industries a and b: the share of cases in which a's n-th
    firing comes before b's n-th firing (over all n and all years), its t-score
    and its p-value for the difference from 0.5. A share of 0.5 means no order.

    Each year is one independent observation: the test compares the year-by-year
    shares with 0.5.
    """
    years, n, N = moments.shape
    share = np.full((n, n), 0.5)
    t = np.zeros((n, n))
    p = np.ones((n, n))
    for a in range(n):
        before = (moments[:, [a], :] < moments).mean(axis=2)   # years x industries
        share[a] = before.mean(axis=0)
        t[a], p[a] = t_test(before, 0.5)
    np.fill_diagonal(share, 0.5)
    np.fill_diagonal(t, 0.0)
    np.fill_diagonal(p, 1.0)
    return share, t, p


def dag_links(share, t, p, fdr):
    """The links of the timing DAG: A -> B when A's firings come first in clearly
    more than half of the cases (false-discovery rate `fdr` over all pairs)."""
    n = len(share)
    a_idx, b_idx = np.triu_indices(n, k=1)             # every pair once
    q = benjamini_hochberg(p[a_idx, b_idx])
    links = []
    for a, b, qq in zip(a_idx, b_idx, q):
        if qq < fdr:
            first, second = (a, b) if share[a, b] > 0.5 else (b, a)
            links.append((int(first), int(second), float(share[first, second]),
                          float(t[first, second]), float(qq)))
    return links


def cycles_in(links, n):
    """Is the graph of links a DAG? Returns (True or False, the number of
    industries that lie on a cycle)."""
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    G.add_edges_from((a, b) for a, b, *_ in links)
    on_cycles = sum(len(c) for c in nx.strongly_connected_components(G) if len(c) > 1)
    return nx.is_directed_acyclic_graph(G), on_cycles
