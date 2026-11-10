# -*- coding: utf-8 -*-
"""
Make the 80-sector CSV tables (data/tables80) from the workbook
data/Philippines_2018_80_Sector_Observed_SUT.xlsx.

Usage:  python make_tables80.py

The workbook adds up PSA's 240-sector supply and use tables over the 80 groups of
PSA's 2018 Input-Output Industry Classification, without any other change (see its
Notes sheet). This script copies its values, unchanged, into the same simple tables
as data/tables, so that the study reads 240 and 80 sectors in the same way.
aggregate.py checks the result against the 240-sector tables.
"""
import csv
from pathlib import Path

import openpyxl

FOLDER = Path(__file__).resolve().parent
WORKBOOK = FOLDER / "data" / "Philippines_2018_80_Sector_Observed_SUT.xlsx"
OUT = FOLDER / "data" / "tables80"

# (our column name, sheet in the workbook, column label in that sheet)
PRODUCT_COLUMNS = [
    ("domestic_production", "Supply Accounts", "Total Domestic Production"),
    ("imports_of_goods", "Supply Accounts", "Imports of Goods"),
    ("imports_of_services", "Supply Accounts", "Imports of Services"),
    ("total_imports", "Supply Accounts", "Total Imports"),
    ("total_supply", "Supply Accounts", "Total Supply at Purchasers' Prices"),
    ("intermediate_demand", "Final Demand", "Total Intermediate Demand"),
    ("household_consumption", "Final Demand", "Household Final Consumption Expenditure"),
    ("government_consumption", "Final Demand", "Government Final Consumption Expenditure"),
    ("gfcf_construction", "Final Demand", "Construction"),
    ("gfcf_durable_equipment", "Final Demand", "Durable Equipment"),
    ("gfcf_breeding_stocks_and_orchards", "Final Demand", "Breeding Stocks and Orchard Development"),
    ("gfcf_intellectual_property_products", "Final Demand", "Intellectual Property Products"),
    ("changes_in_inventories", "Final Demand", "Changes in Inventories"),
    ("valuables", "Final Demand", "Valuables"),
    ("exports_of_goods", "Final Demand", "Exports of Goods"),
    ("exports_of_services", "Final Demand", "Exports of Services"),
    ("final_demand", "Final Demand", "Final Demand"),
    ("total_use", "Final Demand", "Total Use at Purchasers' Prices"),
]
INDUSTRY_COLUMNS = [
    ("intermediate_consumption", "Primary Inputs", "Total Use of Industries"),
    ("compensation_of_employees", "Primary Inputs", "Compensation of Employees"),
    ("gross_operating_surplus", "Primary Inputs", "Gross Operating Surplus"),
    ("taxes_less_subsidies_on_production_and_imports", "Primary Inputs", "Taxes Less Subsidies on Production and Imports"),
    ("gross_value_added", "Primary Inputs", "Gross Value Added"),
    ("gross_output", "Primary Inputs", "Gross Output"),
]


def clean(x):
    """A cell as clean text: no line breaks, no extra spaces."""
    return " ".join(str(x).split()) if x is not None else ""


def number(x):
    """A cell as a number; an empty cell is 0."""
    return 0.0 if x is None else float(x)


def write(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
sheets = {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}
wb.close()

# The 80 sectors, in order: code, name, and the 16-sector group they belong to.
sectors = sheets["80 Sectors"][1:]
codes = [clean(r[0]) for r in sectors]
names = [clean(r[1]) for r in sectors]
assert codes == [f"{k:02d}" for k in range(1, 81)], "the 80 Sectors sheet must list the codes 01 to 80 in order"


def matrix(name):
    """A product x industry sheet: rows and columns must be the codes 01 to 80, in order."""
    rows = sheets[name]
    if [clean(c) for c in rows[0][1:]] != codes or [clean(r[0]) for r in rows[1:]] != codes:
        raise ValueError(f"sheet {name}: rows and columns must be the codes 01 to 80, in order")
    return [[number(v) for v in r[1:]] for r in rows[1:]]


def column(sheet_name, label):
    """One column of an accounts sheet, found by its label; rows must be the codes 01 to 80."""
    rows = sheets[sheet_name]
    head = [clean(h) for h in rows[0]]
    if [clean(r[0]) for r in rows[1:]] != codes:
        raise ValueError(f"sheet {sheet_name}: rows must be the codes 01 to 80, in order")
    return [number(r[head.index(label)]) for r in rows[1:]]


OUT.mkdir(parents=True, exist_ok=True)
V, U = matrix("Supply 80x80"), matrix("Use 80x80")
product_accounts = [column(s, label) for _, s, label in PRODUCT_COLUMNS]
industry_accounts = [column(s, label) for _, s, label in INDUSTRY_COLUMNS]

info = [[codes[i], names[i], clean(r[2]), clean(r[3]), int(r[4])] for i, r in enumerate(sectors)]
write("products.csv", ["product_code", "product_name", "code_16", "name_16", "codes_240"], info)
write("industries.csv", ["industry_code", "industry_name", "code_16", "name_16", "codes_240"], info)
write("supply.csv", ["product_code", "product_name"] + codes, [[codes[i], names[i]] + V[i] for i in range(80)])
write("use.csv", ["product_code", "product_name"] + codes, [[codes[i], names[i]] + U[i] for i in range(80)])
write("product_accounts.csv", ["product_code", "product_name"] + [n for n, _, _ in PRODUCT_COLUMNS],
      [[codes[i], names[i]] + [c[i] for c in product_accounts] for i in range(80)])
write("industry_accounts.csv", ["industry_code", "industry_name"] + [n for n, _, _ in INDUSTRY_COLUMNS],
      [[codes[i], names[i]] + [c[i] for c in industry_accounts] for i in range(80)])
write("flows_long.csv", ["table", "product_code", "industry_code", "value_million_pesos"],
      [[t, codes[i], codes[j], M[i][j]] for t, M in (("supply", V), ("use", U))
       for i in range(80) for j in range(80) if M[i][j] != 0])
(OUT / "README.txt").write_text(
    "2018 Philippine Supply and Use Tables with 80 sectors\n\n"
    "Made by make_tables80.py from data/Philippines_2018_80_Sector_Observed_SUT.xlsx, which adds up\n"
    "PSA's 240-sector supply and use tables over the 80 groups of PSA's 2018 Input-Output Industry\n"
    "Classification (data/classification.csv). Values are copied from the workbook without change.\n"
    "Unit: million Philippine pesos, current prices. Codes are 01 to 80; product j and industry j share a code.\n\n"
    "The tables and their columns are the same as in data/tables (see data/tables/README.txt), except:\n"
    "  products.csv and industries.csv give the 16-sector group (code_16, name_16) and the number of\n"
    "  240-sector codes in each sector (codes_240), instead of the broad group;\n"
    "  industry_accounts.csv has no industry_output column (the workbook gives gross_output, which\n"
    "  equals the column sums of the supply table).\n\n"
    "Check against the 240-sector tables: python aggregate.py\n",
    encoding="utf-8")
print(f"Saved in {OUT}: 80 products x 80 industries, from {WORKBOOK.name}")
