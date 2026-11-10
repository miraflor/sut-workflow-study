2018 Philippine Supply and Use Tables with 80 sectors

Made by make_tables80.py from data/Philippines_2018_80_Sector_Observed_SUT.xlsx, which adds up
PSA's 240-sector supply and use tables over the 80 groups of PSA's 2018 Input-Output Industry
Classification (data/classification.csv). Values are copied from the workbook without change.
Unit: million Philippine pesos, current prices. Codes are 01 to 80; product j and industry j share a code.

The tables and their columns are the same as in data/tables (see data/tables/README.txt), except:
  products.csv and industries.csv give the 16-sector group (code_16, name_16) and the number of
  240-sector codes in each sector (codes_240), instead of the broad group;
  industry_accounts.csv has no industry_output column (the workbook gives gross_output, which
  equals the column sums of the supply table).

Check against the 240-sector tables: python aggregate.py
