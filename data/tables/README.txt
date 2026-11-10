2018 Philippine Supply and Use Tables, as simple tables

Source: Philippine Statistics Authority (PSA), 2018 Supply and Use Tables, Excel workbook as of December 2021,
sheets 240_Supply and 240_Use. https://psa.gov.ph/system/files/macroeconomic-accounts/2018%20Supply%20and%20Use%20Tables.xlsx
SHA-256 of the source file used: f36c64f1232f332a250408e4a6ee8f8df10af445618255239c06a875a2cd2c71
Unit: million Philippine pesos, at current prices. Values are copied from PSA's cells without change.

TABLES (one header row, one record per row)
  products            240 products: product_code, product_name, group
  industries          240 industries: industry_code, industry_name, group
  supply              row = product, column = industry code; value = how much of the product the industry produced
  use                 row = product, column = industry code; value = how much of the product the industry used as an input
  product_accounts    one row per product: the columns to the right of the two matrices in PSA's sheets
  industry_accounts   one row per industry: the rows below the two matrices in PSA's sheets
  flows_long          one row per nonzero cell of the two matrices: table, product_code, industry_code, value (5,648 supply and 12,507 use cells)
  checks              (workbook only) formulas that recompute the totals and the accounting identities

COLUMNS OF product_accounts, with PSA's label
  domestic_production                   240_Supply: Total Domestic Production
  imports_of_goods                      240_Supply: Imports of Goods
  imports_of_services                   240_Supply: Imports of Services
  total_imports                         240_Supply: Total Imports
  total_supply                          240_Supply: Total Supply at Purchasers' Prices
  intermediate_demand                   240_Use: Total Intermediate Demand
  household_consumption                 240_Use: Household Final Consumption Expenditure
  government_consumption                240_Use: Government Final Consumption Expenditure
  gfcf_construction                     240_Use: Construction
  gfcf_durable_equipment                240_Use: Durable Equipment
  gfcf_breeding_stocks_and_orchards     240_Use: Breeding Stocks and Orchard Development
  gfcf_intellectual_property_products   240_Use: Intellectual Property Products
  changes_in_inventories                240_Use: Changes in Inventories
  valuables                             240_Use: Valuables
  exports_of_goods                      240_Use: Exports of Goods
  exports_of_services                   240_Use: Exports of Services
  final_demand                          240_Use: Final Demand
  total_use                             240_Use: Total Use at Purchasers' Prices
  gfcf = gross fixed capital formation (investment), by type of asset.

COLUMNS OF industry_accounts, with PSA's label
  industry_output                                  240_Supply: Total Industry Output
  intermediate_consumption                         240_Use: Total Use of Industries
  compensation_of_employees                        240_Use: Compensation of employees
  gross_operating_surplus                          240_Use: Gross operating surplus
  taxes_less_subsidies_on_production_and_imports   240_Use: Taxes less subsidies on production and imports
  gross_value_added                                240_Use: Gross Value Added
  gross_output                                     240_Use: Gross Output

CONVENTIONS
  Codes are text with leading zeros (001 to 240). Products and industries use the same numbers:
  for example, product 001 is Palay and industry 001 is Growing of palay.
  Empty cells in PSA's sheets are 0.
  Cells that hold '-' instead of a number are 0: 240_Use cell HG252 (Compensation of employees, industry 210 Ownership of dwellings); 240_Use cell HG254 (Taxes less subsidies on production and imports, industry 210 Ownership of dwellings).
  Negative values appear only in: changes_in_inventories (99 cells).
  group: six groups by code range, the same as in the study scripts (a grouping for convenience, not a PSA table):
  agriculture     001-038  agriculture, forestry and fishing
  mining          039-045  mining and quarrying
  manufacturing   046-171  manufacturing
  utilities       172-175  electricity, steam and gas, water, sewerage and waste
  construction    176      construction
  services        177-240  trade, transport, finance, government and other services

ACCOUNTING IDENTITIES
  For each product: total supply = domestic production + imports, and total use = intermediate demand + final demand.
  For each industry: gross output = intermediate consumption + gross value added.
  In PSA's table, total supply and total use of a product differ by at most 0.0966 million pesos
  (product 176, Construction). All other identities hold to within 9e-10 million pesos.

LOADING THE CSV FILES IN PYTHON (pandas)
  import pandas as pd
  read = lambda name, code: pd.read_csv(name, dtype={code: str}, float_precision='round_trip').set_index(code)
  V = read('supply.csv', 'product_code').drop(columns='product_name')      # 240 x 240
  U = read('use.csv', 'product_code').drop(columns='product_name')         # 240 x 240
  products = read('product_accounts.csv', 'product_code')
  industries = read('industry_accounts.csv', 'industry_code')
  dtype={code: str} keeps the leading zeros of the codes (without it, pandas reads 001 as the number 1).
  float_precision='round_trip' makes pandas read every value exactly as written; the default reader can change
  the last digit (a relative change of about 1e-14).
