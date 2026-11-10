# sut-workflow-study

Code for the CS 296 paper **"Can a Year of Production Always Be Completed, and in What Order? A Petri-Net Simulation of the 2018 Philippine Supply and Use Tables"** (first draft) by James Matthew Miraflor.

The paper reads the 2018 Supply and Use Tables of the Philippine Statistics Authority (PSA), collapsed from 240 to 80 products and industries, as a Petri net: products are places, industries are transitions, and stocks of products are tokens. The year of each industry is split into 52 equal batches, and the plan of the year is that every batch fires once. (52 maps easily to weeks, but a batch is only a size, not a date.) The paper asks two questions:

- **Q1.** How much opening stock is needed so that every simulated year is completed? For smaller stocks, what share of simulated years is completed?
- **Q2.** In the years that are completed at a limited stock, do the industries fire in an order (a sequence, or a DAG of "fires before" links)?

## How to run

You need Python 3.9 or newer. From this folder:

```
pip install -r requirements.txt
python -m pytest        # quick checks, less than a minute
python run.py           # the whole study: Part 1 (runs), then Part 2 (analysis)
```

| Command | What it does |
|---|---|
| `python run.py` | everything: Part 1, then Part 2 |
| `python run.py runs` | Part 1 only: Table 2, the search for the smallest stock, the firing logs |
| `python run.py logs` | Part 1c only: firing logs at the stocks set in `LOG_STOCK` in `settings.py` (for example, to look at a lower stock) |
| `python run.py analysis` | Part 2 only, from the firing logs saved by Part 1 |

In Spyder or a Jupyter notebook, run the same commands from this folder with `%run run.py runs` and so on. `run.py` reads `settings.py` again at every run; if you change any other file, restart the kernel before the next run.

All settings are in `settings.py`. The first draft uses:

| Setting | Value | Meaning |
|---|---|---|
| `SECTORS` | 80 | the 80-sector SUT in `data/tables80` (`240` uses PSA's 240-sector tables in `data/tables`) |
| `BATCHES` | [52] | 52 batches per year for each industry and each imported product |
| `GRID` | 2, 4, 9, 13, 17, 22, 26, 35, 52 | opening stocks for Table 2, in weeks of use |
| `GRID_RUNS`, `SEARCH_RUNS`, `PATH_RUNS`, `REFERENCE_RUNS` | 1,000 each | simulated years per stock |
| `SEARCH_STEPS` | 6 | how many times the search halves its interval |
| `CORES` | 5 | processor cores |
| `SEED` | 2026 | fixed random seed |

**The opening stock is measured in weeks of use.** One week of use of a product is 1/52 of the year's use of that product by all industries. With 52 batches, this is exactly the input of one batch of every industry (0.35 trillion pesos for all products together). 52 weeks are the whole year's use (18.27 trillion pesos); at that stock no batch ever waits, so it is the reference.

**Time.** With 80 sectors and 52 batches, a year that finishes takes about 0.13 seconds on one core. With 5 cores, Part 1 should take about 10 minutes, and Part 2 a few minutes. The results do not depend on the number of cores, because each block of simulated years has its own random stream.

## Files, in reading order

| File | What it does | Paper (first draft) |
|---|---|---|
| `settings.py` | every setting of the study, in one place | Sections 5–7 |
| `data.py` | reads V (supply), U (use) and M (imports) from the CSV tables | Section 4 |
| `yearplan.py` | the year plan in whole numbers: units, batch weights, final demand per batch, opening stock | Section 5 |
| `simulation.py` | one simulated year in a random order; many years on several cores | Section 6 |
| `part1_runs.py` | Part 1: Table 2, the search for the smallest stock (Q1), the firing logs | Section 6 |
| `firing_stats.py` | statistics of the firing logs: moments, leads, q-values, pairwise order, the timing DAG | Section 7 |
| `part2_analysis.py` | Part 2: runs the statistics and writes the results (Q2) | Section 7 |
| `run.py` | the command that runs Part 1 and Part 2 | Appendix A |
| `make_tables.py` | makes the 240-sector CSV tables in `data/tables` from PSA's workbook (needed only once) | Section 4 |
| `make_tables80.py` | makes the 80-sector CSV tables in `data/tables80` from the 80-sector SUT workbook (needed only once) | Section 4 |
| `aggregate.py` | checks that the 80-sector tables are the 240-sector tables added up over PSA's 80 groups | Section 4 |
| `helpers.py` | writes CSV files and shows the time used | |
| `tests/test_quick.py` | quick checks, most of them against numbers stated in the paper | |

## Where each step of the paper is in the code

| Step in the paper | Function |
|---|---|
| Collapse from 240 to 80 sectors: V⁸⁰ = GᵀVG, U⁸⁰ = GᵀUG, M⁸⁰ = GᵀM (done in the 80-sector SUT workbook; checked here) | `aggregate.compare` |
| Unit of each product, s_i = 10^(round(log10 χ_i) − 5) | `yearplan.build_plan` |
| Batch weights ã, b̃, m̃ (rounded, halves up) and final demand per batch f̃ | `yearplan.build_plan` |
| Opening stock z0(w) = ⌈w Σ_j ã_ij⌉, w in weeks (52 batches) | `yearplan.opening_stock` |
| Random rule: each step fires one of the batches that can start, with equal chances | `simulation.simulate_year` |
| Check: a completed year ends at z0 + N f̃ | end of `simulation.simulate_year` |
| Check: with 52 weeks of stock, no year stops | `simulation.run_block` |
| Table of completion by stock, with 95% Wilson intervals | `part1_runs.part1_runs` (1a), `part1_runs.wilson` |
| Search for w*, the smallest stock tried above the largest stock tried at which some year stopped (the interval is halved 6 times) | `part1_runs.part1_runs` (1b) |
| Firing logs at w* and at 52 weeks of stock (the reference); the new runs at w* also check w* | `part1_runs.part1_runs` (1c) |
| Moment of the n-th firing of each industry | `firing_stats.firing_moments` |
| Lead in weeks, Welch's two-sample t-test against the reference years, Benjamini–Hochberg q-values | `firing_stats.earliness`, `firing_stats.benjamini_hochberg` |
| Stability: ranking from early firings vs ranking from late firings, in different years (Kendall τ) | `part2_analysis.part2_analysis` (2b) |
| Share of cases in which a's n-th firing comes before b's, and the links a → b | `firing_stats.pairwise_order`, `firing_stats.dag_links` |
| Is the graph of timing links a DAG? | `firing_stats.cycles_in` |
| Checks on the reference years (they should find about 0 industries and 0 links; for the sequence, even reference years against odd ones) | `part2_analysis.part2_analysis` (2b, 2c) |

## Results

`run.py` saves everything in the folder `results80` (with `SECTORS = 240`, in `results`).

| File | Content |
|---|---|
| `table2.csv` | Part 1a: for each grid stock (`weeks`), its value in trillion pesos, the share of years that finish with its 95% Wilson interval, and the share of steps at which some industry had to wait |
| `search.csv` | Part 1b: every stock tried by the search, and how many years stopped |
| `chosen_stock.csv` | Part 1b: the stock found (w*), the largest stock tried at which some year stopped, and the check of w* with the new firing-log runs at w* (`check_runs`, `check_runs_stopped`; if none stops, the chance that a random year stops at w* is below 3/1,000 with 95% confidence) |
| `paths/` | Part 1c: the firing logs (see below) |
| `analysis_batches52/summary.txt` | Part 2: the main numbers, in words. Read this first. |
| `analysis_batches52/distributions.csv` | for every industry and n: the median moment of its n-th firing, the 10th and 90th percentiles, the reference median, and the lead in weeks |
| `analysis_batches52/sequence.csv` | industries from earliest to latest: lead in weeks, its 95% interval, q-value |
| `analysis_batches52/timing_links.csv` | the links a → b of the timing DAG (written only if there are links) |
| `analysis_batches52/sequence.png` | the leads as a figure (needs matplotlib) |

### The firing logs

`paths/batches52_chosen/` (at w*) and `paths/batches52_reference/` (at 52 weeks) hold one file per block of `FILE_RUNS` years: `part_000.npz`, `part_001.npz`, and so on. Read them with `numpy.load`.

| Array | Content |
|---|---|
| `order` | years × firings (7,644 with 80 sectors and 52 batches). Entry t of a row is the transition that fired at step t: 0–79 are industries, and 80 and above are import deliveries (see `transitions.csv` in the same folder). After a year stops, the rest of its row is −1. |
| `steps` | the number of firings in each year |
| `finished` | True if the year finished |
| `blocked` | the number of steps at which some industry had to wait for an input |
| `z0` | the opening stock, in each product's own unit |

`info.json` in the same folder records the settings of the run (including the stock in `weeks`) and `data_sha256`, the checksum of the data.

## Data

`data/tables` holds PSA's 2018 Supply and Use Tables (sheets 240_Supply and 240_Use) as simple CSV tables, with one header row and one record per row, in million pesos. The values are PSA's values, digit for digit. `data/tables/README.txt` describes every table and column. `data/tables/sut2018_tables.xlsx` has the same tables in one workbook, with a sheet of checks. The tables were made by `make_tables.py` from [PSA's workbook](https://psa.gov.ph/system/files/macroeconomic-accounts/2018%20Supply%20and%20Use%20Tables.xlsx) (as of December 2021; SHA-256 `f36c64f1232f332a250408e4a6ee8f8df10af445618255239c06a875a2cd2c71`). To make them again, download the workbook and run `python make_tables.py "2018 Supply and Use Tables.xlsx"`.

`data/Philippines_2018_80_Sector_Observed_SUT.xlsx` is the 80-sector SUT used in the first draft. It adds up PSA's 240-sector supply and use tables (rows and columns, and the accounts beside and below them) over the 80 groups of PSA's 2018 Input-Output Industry Classification, with no other change; its Notes sheet describes the sources. `data/tables80` holds its values, unchanged, in the same CSV format as `data/tables`; to make them again, run `python make_tables80.py`. `data/classification.csv` lists, for each of the 240 codes, its group among 80 and among 16 (from PSA's classification workbook, as of December 2021).

`python aggregate.py` checks the 80-sector tables: it adds up the 240-sector tables over the groups in `data/classification.csv` and compares the result with `data/tables80`. The largest relative differences are 2.1×10⁻¹⁶ (supply), 3.6×10⁻¹⁶ (use) and 1.8×10⁻¹⁶ (imports): the same numbers, added in a different order. All accounting identities hold in the workbook, with the same small product gap as PSA's table (at most 0.097 million pesos).

`run.py` computes a checksum of V, U and M and prints a note if it differs from the checksum of the tables made from PSA's files (`DATA_SHA256` in `settings.py`).

## Relation to `sut_study.py`

This code started as the single script `sut_study.py`, split into files; with the same settings, it gave the same results. Since then: the data are read from the CSV tables; the number of sectors is a setting (80 in the first draft); the opening stock and the leads are measured in weeks instead of months; the RGE baseline, its comparison with the timing DAG and the timing score were removed; and `info.json` records `data_sha256`. Because the stocks are now in weeks, the random streams differ from the earlier runs, so the results are new.

## References

- Benjamini, Y., and Hochberg, Y. (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society: Series B*, 57(1):289–300.
- Bonanno, G. (1995). Modeling production with Petri nets. *Economic Notes*, 24(2):263–292.
- Philippine Statistics Authority (2021). *2018 Supply and Use Tables* [Excel workbook, as of December 2021].
- Philippine Statistics Authority (2021). *2018 Input-Output Industry Classification* [Excel workbook, as of December 2021].

## License

MIT. See `LICENSE`.
