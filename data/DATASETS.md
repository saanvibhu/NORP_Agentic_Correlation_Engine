# Dataset Inventory

Real datasets incorporated into the NORP project (Checkpoint 2).

| Dataset | Source | Local Path | Size | Join Key | Description |
|---------|--------|------------|------|----------|-------------|
| IRS Form 990 Standard Fields | IRS / NORP | `data/raw/irs/2025_10_18_All_Years_990StandardFields.csv` | ~2.1 GB | `FILEREIN`, `FILERUSZIP` | Nonprofit tax filings: revenue, expenses, org names, addresses, tax year |
| Census ACS DP03 | U.S. Census Bureau | `data/raw/census/ACSDP5Y2023.DP03-Data.csv` | ~11 MB | `GEO_ID` (county FIPS) | Selected Economic Characteristics: income, employment, poverty, insurance |
| Census ACS Metadata | U.S. Census Bureau | `data/raw/census/ACSDP5Y2023.DP03-Column-Metadata.csv` | ~75 KB | — | Column labels for DP03 variable codes |
| CDC PLACES County | CDC | `data/raw/cdc/CDCPLACES_county_2025.csv` | ~60 MB | `LocationID` (county FIPS) | Local health measures: chronic disease, health behaviors, prevention |

## Original Download Locations

- IRS 990: `~/Downloads/2025_10_18_All_Years_990StandardFields.csv`
- Census ACS DP03: `~/Downloads/ACSDP5Y2023.DP03_2026-06-25T200116/`
- CDC PLACES: `~/Downloads/CDCPLACES__Local_Data_for_Better_Health,_County_Data,_2025_release_20260625.csv`

## Cross-Dataset Join Strategy

```
IRS 990 (org-level)
    └── zip/county ──→ Census ACS DP03 (county demographics)
                  └──→ CDC PLACES (county health outcomes)
```

- **IRS → Census**: Join via county FIPS derived from `FILERUSZIP` or state/county fields
- **IRS → CDC**: Join via county FIPS (`LocationID` in CDC PLACES, e.g. `05043` = Drew County, AR)
- **Census ↔ CDC**: Direct join on county FIPS (`GEO_ID` contains `0500000US01001` format)

## Pipeline Integration (Checkpoint 2)

Real datasets are integrated into the agent pipeline:

```bash
python run_pipeline.py          # Real IRS + Census + CDC (Georgia)
python run_pipeline.py --sample   # Sample demo data only
```

**Processing flow:**
1. Census ACS cleaned first → builds GA zip→county crosswalk (`data/reference/zip_county_ga.csv`)
2. IRS 990 filtered to GA (~3.6M rows → ~152 counties), aggregated by county FIPS
3. CDC PLACES filtered to GA, pivoted to county-level health measures
4. All three joined on `county_fips` for correlation analysis

**Processed outputs:** `data/processed/irs_990_ga_county.csv`, `census_acs_dp03_ga.csv`, `cdc_places_ga_county.csv`
