# -*- coding: utf-8 -*-
"""
The year plan in whole numbers (paper, Section 5).

Question: what does one batch of each industry use and make, in whole units?
Example: with N = 12 batches, one batch of an industry uses 1/12 of its yearly
inputs and makes 1/12 of its yearly outputs; one import delivery brings 1/12 of
the year's imports of a product. Petri-net tokens are whole numbers, so every
product gets its own unit, and every amount is rounded to whole units.

Terms:
  s[i]        the unit of product i, in million pesos (a power of ten)
  A[i, j]     units of product i that one batch of industry j uses   (inputs)
  B[i, j]     units of product i that one batch of industry j makes  (outputs)
  m[i]        units of product i in one import delivery
  f_tilde[i]  units of product i that go to final demand for each 1/N of the
              year: what the rounded table leaves over, so that a finished
              year balances exactly (paper, Section 5.3)
"""
import numpy as np


def round_half_up(x):
    """Round to whole numbers, with halves rounded up."""
    return np.floor(x + 0.5).astype(np.int64)


def build_plan(sut, N, D):
    """The year plan when each industry and each imported product is split into N batches.

    Each product gets its own unit s[i] (a power of ten), chosen so that its
    typical flow per batch (the median of its positive flows) is about 10**D
    units, and every amount is rounded to whole units.
    """
    n_products, n_industries = sut.U.shape
    U_batch, V_batch, M_batch = sut.U / N, sut.V / N, sut.M / N
    s = np.empty(n_products)
    for i in range(n_products):
        flows = np.concatenate([U_batch[i][U_batch[i] > 0], V_batch[i][V_batch[i] > 0],
                                [M_batch[i]] if M_batch[i] > 0 else []])
        s[i] = 10.0 ** (np.round(np.log10(np.median(flows))) - D)
    A = round_half_up(U_batch / s[:, None])   # A[i, j]: units of product i that one batch of industry j uses
    B = round_half_up(V_batch / s[:, None])   # B[i, j]: units of product i that one batch of industry j makes
    m = round_half_up(M_batch / s)            # m[i]: units of product i in one import delivery
    # Final demand per batch is what the rounded table leaves over, so that a
    # finished year balances exactly (paper, Section 5.3).
    f_tilde = B.sum(axis=1) + m - A.sum(axis=1)
    for i in np.flatnonzero(f_tilde < 0):     # not needed for the 2018 table
        B[i, np.argmax(B[i])] -= f_tilde[i]
        f_tilde[i] = 0
    imported = np.flatnonzero(m > 0)          # products that have import deliveries
    return dict(
        N=N, s=s, A=A, m=m, f_tilde=f_tilde, imported=imported,
        change=np.ascontiguousarray((B - A).T),        # change[j]: what one batch of j adds minus what it uses
        changed=[np.flatnonzero(B[:, j] - A[:, j]) for j in range(n_industries)],
        total=N * (n_industries + len(imported)),      # number of firings in a finished year
    )


def opening_stock(plan, weeks):
    """The opening stock: `weeks` weeks of use by industries, for every product.

    One week of use of product i is a fifty-second of what all industries use in
    a year, N * sum_j A[i, j] / 52, rounded up to whole units. With N = 52
    batches, one week of use is the input of one batch of every industry, and
    52 weeks are the whole year's use."""
    return np.ceil(weeks * plan["N"] * plan["A"].sum(axis=1) / 52).astype(np.int64)


def pesos(plan, z):
    """The value of a stock z, in million pesos."""
    return float(z @ plan["s"])
