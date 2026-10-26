# Corrected research code and data package

This document describes the full corrected research code and data. The root
`README.md` and `requirements.txt` are retained from the earlier plotting-only
GitHub release; use `requirements-research.txt` for replay and analysis.

This archive keeps the original research folder structure: `src/` contains the
simulation, optimisation and accounting implementation; `scripts/` contains
run, replay, calibration, audit and analysis code; `data/` contains processed
inputs; `results/` contains saved policy configurations, daily outputs and
hourly schedules; `tables/` and `audit/` contain final corrected analyses and
verification records. The previously uploaded `plotting/` and `plotting_data/` are retained. The plotting script creates `figures/` when run; no rendered figures are included.

## Version boundary and omissions

The regional-input unit error is corrected in
`data/eia_erco_2022_2023_frame_corrected.csv.gz` and
`data/eia_erco_2022_2024_frame_corrected.csv.gz`. The corresponding rerun
outcomes are in `results/v3_eia_validation_2023/` and
`results/v3_eia_confirmation_2024/`. The uncorrected frames and older
`results/eia_validation_2023/` and `results/eia_confirmation_2024/` runs
are deliberately excluded. `audit/v3_eia_unit_correction.json` documents
the correction. Synthetic confirmation, development, scenario-replication
and sensitivity schedules are retained under their original run-directory
names. Sensitivity directory labels were corrected from bias114 to bias115;
the actual stored multiplier was 1.15 throughout (see the audit JSON).

Manuscript and supplementary files, literature, rendered figures, known
erroneous outputs, raw public downloads, caches and virtual environments
are omitted. The historical `v7_verify_frozen_outputs.py` provenance script
requires the sibling V6 tree and cannot be run from this subset alone.
Some source-building scripts require the omitted raw inputs; the final
processed frames needed to inspect or rerun the reported policies are here.
See `data/EXTERNAL_DATA_README.md` and `audit/eia_provenance.json` for raw
source URLs and checksums. The regional response is observationally fitted
and model-generated, not measured battery abatement.

## Verification and use

From the extracted package root, install dependencies from
`requirements-research.txt`. The simulation uses SciPy's bundled HiGHS solver.
Commands that analyze saved outcomes without rerunning simulations include:

    python scripts/replay_v2.py
    python scripts/v3_verify_interaction.py
    python scripts/v3_cv32_128_analysis.py
    python scripts/v3_failure_and_tradeoff.py
    python scripts/v7_scenario_and_failure_audit.py

These scripts write tables or audit reports; run them on a working copy if
you wish to preserve the packaged hashes. `plotting/build_figures.py`
regenerates V8 figures from `plotting_data/` and writes into `figures/`.
No simulation or optimisation was run while assembling this archive.

The repository-wide SHA-256 inventories are `MANIFEST_SHA256_FULL.csv` and `SHA256SUMS.json`. The earlier plotting-only checksum record is archived under `audit/` and its mismatches are documented there. Values and units
follow the saved column names and configurations: grid exchanges and battery
actions are kWh per one-hour interval, state of charge is kWh, response
and decomposition terms are kg CO2 per interval, and expense is synthetic
USD. The EIA regional-input response is a fitted counterfactual proxy.
