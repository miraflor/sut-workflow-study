# -*- coding: utf-8 -*-
"""
The data (paper, Section 4).

Question: which numbers of the 2018 Supply and Use Tables does the study use?
Three of them: the supply table V (which industry makes which product), the use
table U (which industry uses which product as an input) and the imports M of
each product, all in million pesos. Example: V[0, 0] = 437,272 is the palay
(product 001) grown by the industry "Growing of palay" (industry 001).

They are read from the simple CSV tables in data/tables (240 sectors, made by
make_tables.py from PSA's workbook; PSA's values, digit for digit) or in
data/tables80 (80 sectors, made by make_tables80.py from the 80-sector SUT
workbook, which adds up PSA's rows and columns over PSA's 80 groups).
"""
import csv
import hashlib
from dataclasses import dataclass

import numpy as np


@dataclass
class SUT:
    """The parts of the supply and use tables that the study uses."""
    V: np.ndarray            # V[i, j]: output of product i by industry j (supply table), million pesos
    U: np.ndarray            # U[i, j]: use of product i by industry j (use table), million pesos
    M: np.ndarray            # M[i]: imports of product i, million pesos
    product_codes: list      # "001" to "240" (or "01" to "80" with 80 sectors)
    product_names: list
    industry_codes: list     # the same codes as the products
    industry_names: list

    @property
    def n_products(self):
        return self.U.shape[0]

    @property
    def n_industries(self):
        return self.U.shape[1]


def read_csv(file):
    """A CSV file as its header (a list of names) and its rows (lists of text)."""
    with open(file, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def read_matrix(file):
    """A product x industry table (supply.csv or use.csv). Returns the matrix,
    the product codes, the product names and the industry codes."""
    header, rows = read_csv(file)
    if header[:2] != ["product_code", "product_name"]:
        raise ValueError(f"{file.name}: the first two columns must be product_code and product_name.")
    matrix = np.array([[float(x) for x in row[2:]] for row in rows])
    return matrix, [row[0] for row in rows], [row[1] for row in rows], header[2:]


def load_tables(folder):
    """Read V, U, M and the names of products and industries from the CSV tables in `folder`."""
    V, product_codes, product_names, industry_codes = read_matrix(folder / "supply.csv")
    U, product_codes_u, _, industry_codes_u = read_matrix(folder / "use.csv")
    if product_codes_u != product_codes or industry_codes_u != industry_codes:
        raise ValueError("supply.csv and use.csv do not list the same products and industries in the same order.")

    header, rows = read_csv(folder / "product_accounts.csv")
    if [row[0] for row in rows] != product_codes:
        raise ValueError("product_accounts.csv does not list the products in the same order as supply.csv.")
    k = header.index("total_imports")
    M = np.array([float(row[k]) for row in rows])

    header, rows = read_csv(folder / "industries.csv")
    if [row[0] for row in rows] != industry_codes:
        raise ValueError("industries.csv does not list the industries in the same order as supply.csv.")
    industry_names = [row[1] for row in rows]

    return SUT(V, U, M, product_codes, product_names, industry_codes, industry_names)


def fingerprint(sut):
    """A checksum (SHA-256) of the numbers in V, U and M.

    It does not depend on the file format: PSA's workbook and the CSV tables give
    the same checksum. So it shows whether a run used the data of the paper."""
    h = hashlib.sha256()
    for x in (sut.V, sut.U, sut.M):
        h.update(np.ascontiguousarray(x, dtype=np.float64).tobytes())
    return h.hexdigest()
