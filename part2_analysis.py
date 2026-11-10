# -*- coding: utf-8 -*-
"""
Part 2. Analysis of the firing logs (paper, Section 7), for each number of
batches in settings.BATCHES. Uses the files saved by Part 1.

  2a. For every industry and every n (its 1st, 2nd, ... firing), the
      distribution of the moment (0 = start of the year, 1 = end) at which its
      n-th firing happened, over all finished years.
  2b. A sequence: industries ranked by how early they fire, compared with the
      reference years.
  2c. A DAG: a link A -> B when A's n-th firing comes before B's n-th firing in
      clearly more than half of the cases.
Saved in settings.OUT: one folder analysis_batches{N}/ per N.
"""
import json

import numpy as np
from scipy.stats import kendalltau

import settings
from firing_stats import cycles_in, dag_links, earliness, firing_moments, load_logs, pairwise_order
from helpers import write_csv


def part2_analysis(sut):
    OUT, FDR = settings.OUT, settings.FDR
    n_industries = sut.n_industries
    industries, industry_codes = sut.industry_names, sut.industry_codes

    for N in settings.BATCHES:
        chosen_dir = OUT / "paths" / f"batches{N}_chosen"
        reference_dir = OUT / "paths" / f"batches{N}_reference"
        if not (list(chosen_dir.glob("part_*.npz")) and list(reference_dir.glob("part_*.npz"))):
            print(f"No firing logs for {N} batches: run Part 1 first.")
            continue
        out = OUT / f"analysis_batches{N}"
        out.mkdir(exist_ok=True)
        for old in ("timing_links.csv", "sequence.png"):     # files that are written only in some runs
            (out / old).unlink(missing_ok=True)
        stock = json.loads((chosen_dir / "info.json").read_text(encoding="utf-8"))["weeks"]

        # --- 2a. The moments of every industry's n-th firing.
        logs, years, finished, blocked_share = load_logs(chosen_dir)
        ref_logs, ref_years, _, _ = load_logs(reference_dir)
        if len(logs) < 10 or len(ref_logs) < 10:
            print(f"Too few finished years for {N} batches ({len(logs)} and {len(ref_logs)}): skipped.")
            continue
        moments = firing_moments(logs, N, n_industries)            # finished years at the chosen stock
        ref_moments = firing_moments(ref_logs, N, n_industries)    # reference years (52 weeks of stock)
        print(f"\n=== Part 2, {N} batches: {len(logs)} of {years} years finished at {stock:g} weeks; "
              f"{len(ref_logs)} reference years")

        # In the reference nothing ever waits, so all industries behave alike: the
        # reference moment of the n-th firing is the same for every industry.
        ref_median_n = np.median(ref_moments, axis=(0, 1))          # one value per n
        rows = []
        for j in range(n_industries):
            for n in range(N):
                x = moments[:, j, n]
                rows.append(dict(industry=industry_codes[j], n=n + 1,
                                 median=float(np.median(x)), p10=float(np.percentile(x, 10)),
                                 p90=float(np.percentile(x, 90)),
                                 reference_median=float(ref_median_n[n]),
                                 lead_weeks=float((np.median(x) - ref_median_n[n]) * 52)))
        write_csv(out / "distributions.csv", rows)

        # --- 2b. The sequence: how early each industry fires, in weeks,
        # compared with the reference (negative = earlier). An industry counts as
        # clearly earlier or later when its q-value is below FDR.
        lead, half, q_lead = earliness(moments, ref_moments)
        earlier = int(((q_lead < FDR) & (lead < 0)).sum())
        later = int(((q_lead < FDR) & (lead > 0)).sum())
        # Check: the same test within the reference years (even years against odd
        # years, so that the two samples are independent) should find (almost) none.
        _, _, ref_q_lead = earliness(ref_moments[0::2], ref_moments[1::2])
        ref_found = int((ref_q_lead < FDR).sum())
        # Is the ranking the same early and late in the year? The ranking from the
        # first half of the firings, in one half of the years, is compared with the
        # ranking from the second half of the firings, in the other half of the
        # years. (Using different years keeps chance from making them look alike.)
        early = moments[0::2, :, : N // 2].mean(axis=(0, 2))
        late = moments[1::2, :, N // 2:].mean(axis=(0, 2))
        stability, stability_p = kendalltau(early, late)

        # --- 2c. The DAG from the firing logs.
        share, t, p = pairwise_order(moments)
        links = dag_links(share, t, p, FDR)
        is_dag, on_cycles = cycles_in(links, n_industries)
        # Check: the same procedure on the reference years should find (almost) no links.
        ref_links = dag_links(*pairwise_order(ref_moments), FDR)

        rank = np.argsort(lead)                                      # earliest first
        write_csv(out / "sequence.csv",
                  [dict(rank=r + 1, industry=industry_codes[j], lead_weeks=float(lead[j]),
                        low=float(lead[j] - half[j]), high=float(lead[j] + half[j]), q=float(q_lead[j]),
                        name=f'"{industries[j]}"')
                   for r, j in enumerate(rank)])
        if links:
            write_csv(out / "timing_links.csv",
                      [dict(source=industry_codes[a], target=industry_codes[b], share_first=s, t=tt, q=qq,
                            source_name=f'"{industries[a]}"', target_name=f'"{industries[b]}"')
                       for a, b, s, tt, qq in links])

        summary = [
            f"Firing-log analysis, {N} batches per year",
            f"Chosen stock: {stock:g} weeks of use. Years: {years}, finished: {len(logs)}, "
            f"stopped: {years - len(logs)}. Reference years (52 weeks): {len(ref_logs)}.",
            "",
            "Blocking (some industry with batches left had to wait for an input):",
            f"  finished years with any blocking: {np.mean(blocked_share[finished] > 0):.1%}",
            f"  average share of steps with blocking: {np.mean(blocked_share[finished]):.2%}",
            "  If there is no blocking, there is no reason for an order, and the results below show none.",
            "",
            "Sequence (sequence.csv):",
            f"  industries clearly earlier than the reference: {earlier}; clearly later: {later} "
            f"(false-discovery rate {FDR})",
            f"  check on the reference years: {ref_found} industries found (should be about 0)",
            f"  stability: ranking from early firings vs ranking from late firings, in different years "
            f"(Kendall tau): {stability:.3f} (p = {stability_p:.3g}; about 0 if there is no order)",
            "",
            "DAG from the firing logs (timing_links.csv):",
            f"  links found: {len(links)} of {n_industries * (n_industries - 1) // 2} pairs "
            f"(false-discovery rate {FDR})",
            f"  is a DAG: {is_dag}; industries on cycles: {on_cycles}",
            f"  check on the reference years: {len(ref_links)} links found (should be about 0)",
        ]

        (out / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
        print("\n".join("  " + line for line in summary[1:]))

        try:                                           # figure: the sequence, earliest first
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(7, 3.5))
            x = np.arange(n_industries)
            ax.errorbar(x, lead[rank], yerr=half[rank], fmt="o", ms=2, lw=0.6)
            ax.axhline(0, color="grey", lw=0.8)
            ax.set_xlabel("Industries, from earliest to latest")
            ax.set_ylabel("Lead in weeks\n(negative = earlier)")
            ax.set_title(f"{N} batches, stock {stock:g} weeks")
            fig.tight_layout()
            fig.savefig(out / "sequence.png", dpi=200)
            plt.close(fig)
        except ImportError:
            pass
        print(f"  Saved in {out}")
