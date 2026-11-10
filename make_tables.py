# -*- coding: utf-8 -*-
"""
Turn PSA's "2018 Supply and Use Tables" workbook (a print layout) into simple tables.
This is the only file that reads PSA's workbook; the study reads the CSV tables.

Usage:  python make_tables.py <PSA workbook.xlsx> [output folder]
        (the output folder is data/tables if it is not given)

Writes, in the output folder:
  products.csv, industries.csv, supply.csv, use.csv, product_accounts.csv,
  industry_accounts.csv, flows_long.csv   the tables, one header row and one record per row
  README.txt                              what each table and column holds
  sut2018_tables.xlsx                     the same tables in one workbook, plus a sheet of
                                          checks (formulas); Excel computes them when the file opens

Values are copied from PSA's cells without change, in million pesos at current prices.
"""

import csv
import hashlib
import sys
from pathlib import Path

import openpyxl
import openpyxl.cell._writer
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as col

# openpyxl writes numbers with 16 significant digits, which can change the last binary digit
# of a value. Write repr(value) instead: the shortest text that gives back exactly the same number.
# (This changes only the workbook; the CSV files are always exact.)
if hasattr(openpyxl.cell._writer, "safe_string"):
    _safe_string = openpyxl.cell._writer.safe_string
    openpyxl.cell._writer.safe_string = lambda v: repr(v) if isinstance(v, float) else _safe_string(v)

if len(sys.argv) not in (2, 3):
    raise SystemExit("Use: python make_tables.py <PSA workbook.xlsx> [output folder]")
SOURCE = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) == 3 else Path(__file__).resolve().parent / "data" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------- reading

def clean(x):
    """A cell as clean text: no line breaks, no double spaces."""
    return " ".join(str(x).split()) if x is not None else ""


dash_cells = []          # cells that hold "-" instead of a number (counted as 0, and listed in the README)


def number(v, where):
    """A cell as a number: an empty cell is 0, a cell with "-" is 0, any other text stops the script."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if clean(v) == "-":
        dash_cells.append(where)
        return 0.0
    raise ValueError(f"Unexpected text {v!r} at {where}")

wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
sup = [list(r) for r in wb["240_Supply"].iter_rows(values_only=True)]
use = [list(r) for r in wb["240_Use"].iter_rows(values_only=True)]
wb.close()

# Find the matrices by their labels, not by fixed cell addresses.
# h = the header row: the cell "Industry/Commodity", then the 240 industry names; the row above has the industry codes.
# c = the column of "Industry/Commodity": below it are the 240 product names; the column to its left has the product codes.
h = next(r for r, row in enumerate(sup[:40]) if "industry/commodity" in [clean(x).lower() for x in row])
c = [clean(x).lower() for x in sup[h]].index("industry/commodity")
assert clean(use[h][c]).lower() == "industry/commodity", "the two sheets have different layouts"

ind_cols = []
k = c + 1
while k < len(sup[h - 1]) and sup[h - 1][k] not in (None, ""):
    ind_cols.append(k)
    k += 1
prod_rows = []
r = h + 1
while r < len(sup) and sup[r][c - 1] not in (None, ""):
    prod_rows.append(r)
    r += 1
assert len(ind_cols) == 240 and len(prod_rows) == 240

prod_codes = [clean(sup[r][c - 1]) for r in prod_rows]
prod_names = [clean(sup[r][c]) for r in prod_rows]
ind_codes = [clean(sup[h - 1][k]) for k in ind_cols]
ind_names = [clean(sup[h][k]) for k in ind_cols]
assert [clean(use[r][c - 1]) for r in prod_rows] == prod_codes
assert [clean(use[h - 1][k]) for k in ind_cols] == ind_codes


def column(sheet, sheet_name, label):
    # Look only to the right of the 240 industry columns: industry 176 is also called "Construction".
    found = [k for k in range(ind_cols[-1] + 1, len(sheet[h])) if clean(sheet[h][k]).lower() == label.lower()]
    assert len(found) == 1, f"{sheet_name}: label {label!r} found {len(found)} times"
    j = found[0]
    return [number(sheet[r][j], f"{sheet_name} {col(j + 1)}{r + 1}") for r in prod_rows]


def row(sheet, sheet_name, label):
    # Look only below the 240 product rows.
    found = [i for i in range(prod_rows[-1] + 1, len(sheet)) if clean(sheet[i][c]).lower() == label.lower()]
    assert len(found) == 1, f"{sheet_name}: label {label!r} found {len(found)} times"
    rr = found[0]
    return [number(sheet[rr][k], f"{sheet_name} cell {col(k + 1)}{rr + 1} ({label}, industry {clean(sup[h - 1][k])} "
                                 f"{clean(sup[h][k])})") for k in ind_cols]


# The two matrices: V[i][j] = supply of product i by industry j; U[i][j] = use of product i by industry j
V = [[number(sup[r][k], f"240_Supply {col(k + 1)}{r + 1}") for k in ind_cols] for r in prod_rows]
U = [[number(use[r][k], f"240_Use {col(k + 1)}{r + 1}") for k in ind_cols] for r in prod_rows]

# Product columns: (our column name, PSA sheet, PSA label)
PRODUCT_COLUMNS = [
    ("domestic_production", "240_Supply", "Total Domestic Production"),
    ("imports_of_goods", "240_Supply", "Imports of Goods"),
    ("imports_of_services", "240_Supply", "Imports of Services"),
    ("total_imports", "240_Supply", "Total Imports"),
    ("total_supply", "240_Supply", "Total Supply at Purchasers' Prices"),
    ("intermediate_demand", "240_Use", "Total Intermediate Demand"),
    ("household_consumption", "240_Use", "Household Final Consumption Expenditure"),
    ("government_consumption", "240_Use", "Government Final Consumption Expenditure"),
    ("gfcf_construction", "240_Use", "Construction"),
    ("gfcf_durable_equipment", "240_Use", "Durable Equipment"),
    ("gfcf_breeding_stocks_and_orchards", "240_Use", "Breeding Stocks and Orchard Development"),
    ("gfcf_intellectual_property_products", "240_Use", "Intellectual Property Products"),
    ("changes_in_inventories", "240_Use", "Changes in Inventories"),
    ("valuables", "240_Use", "Valuables"),
    ("exports_of_goods", "240_Use", "Exports of Goods"),
    ("exports_of_services", "240_Use", "Exports of Services"),
    ("final_demand", "240_Use", "Final Demand"),
    ("total_use", "240_Use", "Total Use at Purchasers' Prices"),
]
# Industry rows: (our column name, PSA sheet, PSA label)
INDUSTRY_ROWS = [
    ("industry_output", "240_Supply", "Total Industry Output"),
    ("intermediate_consumption", "240_Use", "Total Use of Industries"),
    ("compensation_of_employees", "240_Use", "Compensation of employees"),
    ("gross_operating_surplus", "240_Use", "Gross operating surplus"),
    ("taxes_less_subsidies_on_production_and_imports", "240_Use", "Taxes less subsidies on production and imports"),
    ("gross_value_added", "240_Use", "Gross Value Added"),
    ("gross_output", "240_Use", "Gross Output"),
]
SHEETS = {"240_Supply": sup, "240_Use": use}
prod_acc = {name: column(SHEETS[s], s, label) for name, s, label in PRODUCT_COLUMNS}
ind_acc = {name: row(SHEETS[s], s, label) for name, s, label in INDUSTRY_ROWS}


def group(code):
    n = int(code)
    for name, lo, hi in [("agriculture", 1, 38), ("mining", 39, 45), ("manufacturing", 46, 171),
                         ("utilities", 172, 175), ("construction", 176, 176), ("services", 177, 240)]:
        if lo <= n <= hi:
            return name

# ----------------------------------------------------------------- tables
# Each table: (name, header, rows, number of label columns at the left)
tables = []
tables.append(("products", ["product_code", "product_name", "group"],
               [[prod_codes[i], prod_names[i], group(prod_codes[i])] for i in range(240)], 3))
tables.append(("industries", ["industry_code", "industry_name", "group"],
               [[ind_codes[j], ind_names[j], group(ind_codes[j])] for j in range(240)], 3))
tables.append(("supply", ["product_code", "product_name"] + ind_codes,
               [[prod_codes[i], prod_names[i]] + V[i] for i in range(240)], 2))
tables.append(("use", ["product_code", "product_name"] + ind_codes,
               [[prod_codes[i], prod_names[i]] + U[i] for i in range(240)], 2))
tables.append(("product_accounts", ["product_code", "product_name"] + [n for n, _, _ in PRODUCT_COLUMNS],
               [[prod_codes[i], prod_names[i]] + [prod_acc[n][i] for n, _, _ in PRODUCT_COLUMNS] for i in range(240)], 2))
tables.append(("industry_accounts", ["industry_code", "industry_name"] + [n for n, _, _ in INDUSTRY_ROWS],
               [[ind_codes[j], ind_names[j]] + [ind_acc[n][j] for n, _, _ in INDUSTRY_ROWS] for j in range(240)], 2))
long_rows = []
for name, M in (("supply", V), ("use", U)):
    for i in range(240):
        for j in range(240):
            if M[i][j] != 0:
                long_rows.append([name, prod_codes[i], ind_codes[j], M[i][j]])
tables.append(("flows_long", ["table", "product_code", "industry_code", "value_million_pesos"], long_rows, 3))

# ----------------------------------------------------------------- README text
sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
n_supply = sum(1 for x in long_rows if x[0] == "supply")
n_use = len(long_rows) - n_supply
# Where are the negative values? (count of negative cells per table or column)
negatives = {"supply matrix": sum(x < 0 for r_ in V for x in r_), "use matrix": sum(x < 0 for r_ in U for x in r_)}
negatives.update({n: sum(x < 0 for x in prod_acc[n]) for n, _, _ in PRODUCT_COLUMNS})
negatives.update({n: sum(x < 0 for x in ind_acc[n]) for n, _, _ in INDUSTRY_ROWS})
negatives = {k: v for k, v in negatives.items() if v > 0}
negative_text = ", ".join(f"{k} ({v} cells)" for k, v in negatives.items()) if negatives else "none"
dash_text = "; ".join(dash_cells) if dash_cells else "none"

# The accounting identities, computed here for the README (the sheet 'checks' repeats them as formulas)
FD_PARTS = ["household_consumption", "government_consumption", "gfcf_construction", "gfcf_durable_equipment",
            "gfcf_breeding_stocks_and_orchards", "gfcf_intellectual_property_products", "changes_in_inventories",
            "valuables", "exports_of_goods", "exports_of_services"]
pa_ = lambda n, i: prod_acc[n][i]
ia_ = lambda n, j: ind_acc[n][j]
balance_gap = [pa_("total_supply", i) - pa_("total_use", i) for i in range(240)]
i_max = max(range(240), key=lambda i: abs(balance_gap[i]))
other_gaps = []
for i in range(240):
    other_gaps += [sum(V[i]) - pa_("domestic_production", i), sum(U[i]) - pa_("intermediate_demand", i),
                   pa_("imports_of_goods", i) + pa_("imports_of_services", i) - pa_("total_imports", i),
                   pa_("domestic_production", i) + pa_("total_imports", i) - pa_("total_supply", i),
                   sum(pa_(n, i) for n in FD_PARTS) - pa_("final_demand", i),
                   pa_("intermediate_demand", i) + pa_("final_demand", i) - pa_("total_use", i)]
for j in range(240):
    other_gaps += [sum(V[i][j] for i in range(240)) - ia_("industry_output", j),
                   sum(U[i][j] for i in range(240)) - ia_("intermediate_consumption", j),
                   ia_("compensation_of_employees", j) + ia_("gross_operating_surplus", j)
                   + ia_("taxes_less_subsidies_on_production_and_imports", j) - ia_("gross_value_added", j),
                   ia_("intermediate_consumption", j) + ia_("gross_value_added", j) - ia_("gross_output", j),
                   ia_("industry_output", j) - ia_("gross_output", j)]
other_max = max(abs(g) for g in other_gaps)
assert other_max < 1e-6, "an accounting identity fails: check the column and row labels"

# The README, as a list of lines. A line is plain text, a heading ("## ..."), or a pair
# (name, text) that is shown as two aligned columns.
README = [
    "2018 Philippine Supply and Use Tables, as simple tables",
    "",
    "Source: Philippine Statistics Authority (PSA), 2018 Supply and Use Tables, Excel workbook as of December 2021,",
    "sheets 240_Supply and 240_Use. https://psa.gov.ph/system/files/macroeconomic-accounts/2018%20Supply%20and%20Use%20Tables.xlsx",
    f"SHA-256 of the source file used: {sha}",
    "Unit: million Philippine pesos, at current prices. Values are copied from PSA's cells without change.",
    "",
    "## TABLES (one header row, one record per row)",
    ("products", "240 products: product_code, product_name, group"),
    ("industries", "240 industries: industry_code, industry_name, group"),
    ("supply", "row = product, column = industry code; value = how much of the product the industry produced"),
    ("use", "row = product, column = industry code; value = how much of the product the industry used as an input"),
    ("product_accounts", "one row per product: the columns to the right of the two matrices in PSA's sheets"),
    ("industry_accounts", "one row per industry: the rows below the two matrices in PSA's sheets"),
    ("flows_long", f"one row per nonzero cell of the two matrices: table, product_code, industry_code, value "
                   f"({n_supply:,} supply and {n_use:,} use cells)"),
    ("checks", "(workbook only) formulas that recompute the totals and the accounting identities"),
    "",
    "## COLUMNS OF product_accounts, with PSA's label",
] + [(n, f"{s}: {label}") for n, s, label in PRODUCT_COLUMNS] + [
    "  gfcf = gross fixed capital formation (investment), by type of asset.",
    "",
    "## COLUMNS OF industry_accounts, with PSA's label",
] + [(n, f"{s}: {label}") for n, s, label in INDUSTRY_ROWS] + [
    "",
    "## CONVENTIONS",
    "  Codes are text with leading zeros (001 to 240). Products and industries use the same numbers:",
    "  for example, product 001 is Palay and industry 001 is Growing of palay.",
    "  Empty cells in PSA's sheets are 0.",
    f"  Cells that hold '-' instead of a number are 0: {dash_text}.",
    f"  Negative values appear only in: {negative_text}.",
    "  group: six groups by code range, the same as in the study scripts (a grouping for convenience, not a PSA table):",
    ("agriculture", "001-038  agriculture, forestry and fishing"),
    ("mining", "039-045  mining and quarrying"),
    ("manufacturing", "046-171  manufacturing"),
    ("utilities", "172-175  electricity, steam and gas, water, sewerage and waste"),
    ("construction", "176      construction"),
    ("services", "177-240  trade, transport, finance, government and other services"),
    "",
    "## ACCOUNTING IDENTITIES",
    "  For each product: total supply = domestic production + imports, and total use = intermediate demand + final demand.",
    "  For each industry: gross output = intermediate consumption + gross value added.",
    f"  In PSA's table, total supply and total use of a product differ by at most {abs(balance_gap[i_max]):.4f} million pesos",
    f"  (product {prod_codes[i_max]}, {prod_names[i_max]}). All other identities hold to within {other_max:.0e} million pesos.",
    "",
    "## LOADING THE CSV FILES IN PYTHON (pandas)",
    "  import pandas as pd",
    "  read = lambda name, code: pd.read_csv(name, dtype={code: str}, float_precision='round_trip').set_index(code)",
    "  V = read('supply.csv', 'product_code').drop(columns='product_name')      # 240 x 240",
    "  U = read('use.csv', 'product_code').drop(columns='product_name')         # 240 x 240",
    "  products = read('product_accounts.csv', 'product_code')",
    "  industries = read('industry_accounts.csv', 'industry_code')",
    "  dtype={code: str} keeps the leading zeros of the codes (without it, pandas reads 001 as the number 1).",
    "  float_precision='round_trip' makes pandas read every value exactly as written; the default reader can change",
    "  the last digit (a relative change of about 1e-14).",
]


def readme_text(lines):
    """Plain-text version: pairs in a block are padded to the same width."""
    out, i = [], 0
    while i < len(lines):
        if isinstance(lines[i], tuple):
            j = i
            while j < len(lines) and isinstance(lines[j], tuple):
                j += 1
            width = max(len(name) for name, _ in lines[i:j]) + 3
            out += [f"  {name:<{width}}{text}" for name, text in lines[i:j]]
            i = j
        else:
            out.append(lines[i][3:] if lines[i].startswith("## ") else lines[i])
            i += 1
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------- CSV files
for name, header, rows, _ in tables:
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
(OUT / "README.txt").write_text(readme_text(README), encoding="utf-8")

# ----------------------------------------------------------------- workbook
ARIAL = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True)
TITLE = Font(name="Arial", size=12, bold=True)
HEAD_FILL = PatternFill("solid", fgColor="E7ECF3")
NUM = "#,##0.00;-#,##0.00;0"

book = openpyxl.Workbook()
ws = book.active
ws.title = "README"
for i, line in enumerate(README, start=1):
    if isinstance(line, tuple):                       # a pair: name in column A, text in column B
        ws.cell(row=i, column=1, value="  " + line[0]).font = ARIAL
        ws.cell(row=i, column=2, value=line[1]).font = ARIAL
    else:
        cell = ws.cell(row=i, column=1, value=line[3:] if line.startswith("## ") else line)
        cell.font = TITLE if i == 1 else (BOLD if line.startswith("## ") else ARIAL)
ws.column_dimensions["A"].width = 50
ws.column_dimensions["B"].width = 110

for name, header, rows, n_labels in tables:
    s = book.create_sheet(name)
    s.append(header)
    for row_values in rows:
        s.append(row_values)
    for cell in s[1]:
        cell.font = BOLD
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="center")
    for r_cells in s.iter_rows(min_row=2):
        for k, cell in enumerate(r_cells):
            cell.font = ARIAL
            if k >= n_labels:
                cell.number_format = NUM
    s.freeze_panes = "A2" if name == "flows_long" else s.cell(row=2, column=min(n_labels, 2) + 1)
    for k, head in enumerate(header, start=1):
        if head.endswith("_code"):
            width = 14
        elif head.endswith("_name"):
            width = 70
        elif name in ("supply", "use"):
            width = 12                                # the 240 industry columns
        else:
            width = max(14, len(head) + 3)
        s.column_dimensions[col(k)].width = width

# ---- checks: every cell is a formula on the other sheets; every gap should be 0 or very small
ck = book.create_sheet("checks")
P = {n: col(3 + i) for i, (n, _, _) in enumerate(PRODUCT_COLUMNS)}   # column letter of each product account
I = {n: col(3 + i) for i, (n, _, _) in enumerate(INDUSTRY_ROWS)}     # column letter of each industry account
FIRST, LAST = col(3), col(242)                                        # industry columns in supply and use


def pa(name, r):
    return f"product_accounts!{P[name]}{r}"


def ia(name, r):
    return f"industry_accounts!{I[name]}{r}"


# (header, formula for the product in row r of supply, use and product_accounts)
PRODUCT_CHECKS = [
    ("supply matrix row sum - domestic_production", lambda r: f"=SUM(supply!{FIRST}{r}:{LAST}{r})-{pa('domestic_production', r)}"),
    ("use matrix row sum - intermediate_demand", lambda r: f"=SUM(use!{FIRST}{r}:{LAST}{r})-{pa('intermediate_demand', r)}"),
    ("imports_of_goods + imports_of_services - total_imports",
     lambda r: f"={pa('imports_of_goods', r)}+{pa('imports_of_services', r)}-{pa('total_imports', r)}"),
    ("domestic_production + total_imports - total_supply",
     lambda r: f"={pa('domestic_production', r)}+{pa('total_imports', r)}-{pa('total_supply', r)}"),
    ("sum of the ten final demand columns - final_demand",
     lambda r: "=" + "+".join(pa(n, r) for n in FD_PARTS) + f"-{pa('final_demand', r)}"),
    ("intermediate_demand + final_demand - total_use",
     lambda r: f"={pa('intermediate_demand', r)}+{pa('final_demand', r)}-{pa('total_use', r)}"),
    ("total_supply - total_use", lambda r: f"={pa('total_supply', r)}-{pa('total_use', r)}"),
]
# (header, formula for industry j, in row r of industry_accounts)
INDUSTRY_CHECKS = [
    ("supply matrix column sum - industry_output",
     lambda j, r: f"=SUM(supply!{col(3 + j)}2:{col(3 + j)}241)-{ia('industry_output', r)}"),
    ("use matrix column sum - intermediate_consumption",
     lambda j, r: f"=SUM(use!{col(3 + j)}2:{col(3 + j)}241)-{ia('intermediate_consumption', r)}"),
    ("compensation + operating surplus + taxes less subsidies - gross_value_added",
     lambda j, r: f"={ia('compensation_of_employees', r)}+{ia('gross_operating_surplus', r)}"
                  f"+{ia('taxes_less_subsidies_on_production_and_imports', r)}-{ia('gross_value_added', r)}"),
    ("intermediate_consumption + gross_value_added - gross_output",
     lambda j, r: f"={ia('intermediate_consumption', r)}+{ia('gross_value_added', r)}-{ia('gross_output', r)}"),
    ("industry_output (supply sheet) - gross_output (use sheet)",
     lambda j, r: f"={ia('industry_output', r)}-{ia('gross_output', r)}"),
]
GAP = "#,##0.000000;-#,##0.000000;0"

S0 = 5                                              # first summary row
P0 = S0 + len(PRODUCT_CHECKS) + len(INDUSTRY_CHECKS) + 1 + 4   # first row of the product block
I0 = P0 + 240 + 4                                   # first row of the industry block

ck.cell(row=1, column=1, value="Checks of the tables (every number below is a formula on the other sheets)").font = TITLE
ck.cell(row=2, column=1, value="Each number is a gap that should be 0 or very small. Unit: million pesos.").font = ARIAL
for k, t in enumerate(["Check", "Largest gap, in absolute value"], start=1):
    cell = ck.cell(row=S0 - 1, column=k, value=t)
    cell.font, cell.fill = BOLD, HEAD_FILL

rr = S0
for k, (head, _) in enumerate(PRODUCT_CHECKS):
    rng = f"{col(2 + k)}{P0}:{col(2 + k)}{P0 + 239}"
    ck.cell(row=rr, column=1, value=f"Products: {head}").font = ARIAL
    ck.cell(row=rr, column=2, value=f"=MAX(MAX({rng}),-MIN({rng}))+0")      # +0 turns -0 into 0
    rr += 1
for k, (head, _) in enumerate(INDUSTRY_CHECKS):
    rng = f"{col(2 + k)}{I0}:{col(2 + k)}{I0 + 239}"
    ck.cell(row=rr, column=1, value=f"Industries: {head}").font = ARIAL
    ck.cell(row=rr, column=2, value=f"=MAX(MAX({rng}),-MIN({rng}))+0")
    rr += 1
ck.cell(row=rr, column=1, value="Whole economy: sum of gross_value_added + sum of total_imports - sum of final_demand").font = ARIAL
ck.cell(row=rr, column=2, value=f"=SUM(industry_accounts!{I['gross_value_added']}2:{I['gross_value_added']}241)"
                                f"+SUM(product_accounts!{P['total_imports']}2:{P['total_imports']}241)"
                                f"-SUM(product_accounts!{P['final_demand']}2:{P['final_demand']}241)")
for r_ in range(S0, rr + 1):
    ck.cell(row=r_, column=2).font = ARIAL
    ck.cell(row=r_, column=2).number_format = GAP


def block(first_row, title, code_head, codes, checks, formula):
    ck.cell(row=first_row - 2, column=1, value=title).font = BOLD
    for k, t in enumerate([code_head] + [head for head, _ in checks], start=1):
        cell = ck.cell(row=first_row - 1, column=k, value=t)
        cell.font, cell.fill = BOLD, HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ck.row_dimensions[first_row - 1].height = 54
    for i in range(240):
        ck.cell(row=first_row + i, column=1, value=codes[i]).font = ARIAL
        for k, check in enumerate(checks):
            cell = ck.cell(row=first_row + i, column=2 + k, value=formula(check, i))
            cell.font, cell.number_format = ARIAL, GAP


block(P0, "Products (one row per product)", "product_code", prod_codes, PRODUCT_CHECKS,
      lambda check, i: check[1](i + 2))
block(I0, "Industries (one row per industry)", "industry_code", ind_codes, INDUSTRY_CHECKS,
      lambda check, j: check[1](j, j + 2))
ck.column_dimensions["A"].width = 84
for k in range(2, 2 + max(len(PRODUCT_CHECKS), len(INDUSTRY_CHECKS))):
    ck.column_dimensions[col(k)].width = 24

book.calculation.fullCalcOnLoad = True      # Excel and LibreOffice compute the 'checks' formulas when the file opens
book.save(OUT / "sut2018_tables.xlsx")
print(f"Saved in {OUT}: " + ", ".join(f"{t[0]}.csv ({len(t[2]):,} rows)" for t in tables)
      + ", README.txt, sut2018_tables.xlsx")
print("Cells with '-' (counted as 0):", dash_text)
print("Negative values:", negative_text)
