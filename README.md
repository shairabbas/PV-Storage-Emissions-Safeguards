# PV-Storage-Emissions-Safeguards

Research code, processed inputs, corrected saved outcomes, and plotting data accompanying **“Failure conditions of finite-scenario emissions safeguards in a shared photovoltaic-storage simulation.”**

## Study purpose

The study examines when forecast-based emissions safeguards can accept a schedule whose separately evaluated, reference-relative emissions change is positive. It compares shared-meter, flexible-demand and battery configurations, finite-scenario CVaR guards, a worst-scenario guard and a calibrated margin in a simulated photovoltaic–battery community. Synthetic merit-order regimes and a corrected ERCOT/ERCO regional-input check support diagnostic comparisons of operating expense, signed emissions and positive-change severity.

Results are conditional on the stated models and sampled dates. They do not establish a probability guarantee or measured real-world abatement. CV8/CV32 use different residual pools; CV32/CV128 use non-nested scenario sets. These comparisons do not isolate scenario count.

## Contents and release scope

| Path | Contents |
|---|---|
| `plotting/build_figures.py` | Regenerates the presentation plots from the supplied CSV files. |
| `plotting_data/` | Derived summary tables, paired scenario comparisons, selected-day hourly diagnostics, response coefficients and calibration/verification records. |
| `requirements.txt` | Versions used for the figure-build check of this release. |
| `SHA256SUMS.json` | Checksums for the expanded repository, excluding checksum inventories. |
| `CODE_DATA_README.md` | Corrected-output boundary, units, omissions, and replay commands. |
| `src/`, `scripts/` | Simulation, optimization, accounting, calibration, replay, audit, and analysis code. |
| `data/`, `results/` | Corrected processed inputs, policy configurations, daily outcomes, and hourly schedules. |
| `tables/`, `audit/` | Corrected analyses and verification records. |
| `requirements-research.txt` | Research and replay dependencies. |
| `MANIFEST_SHA256_FULL.csv` | Checksums for the expanded repository. |

The repository now includes the corrected optimizer, processed inputs and saved schedules. Raw public downloads, manuscript and supplementary documents, literature, pre-rendered figures, caches, and known erroneous outputs are excluded. Some source-building scripts require omitted raw inputs; the final processed frames needed to inspect or rerun reported policies are included. The script still generates all five main figures and the supplementary robustness plot locally.

The previously uploaded plotting files remain unchanged. The earlier plotting-only README and checksum record are preserved under `audit/legacy_plotting_release_*`; that historical checksum record has six mismatches, documented in `audit/legacy_plotting_release_checksum_audit.json`. Use the current root `SHA256SUMS.json` or `MANIFEST_SHA256_FULL.csv` for verification. The plotting script has one portability adjustment: it creates its output directory if absent.

## Software requirements

Python with NumPy, pandas and Matplotlib is required. A figure-build check was performed with Python 3.12.14 and the pinned package versions in `requirements.txt`. Replay and optimization use the dependencies in `requirements-research.txt`, including SciPy's bundled HiGHS solver; LaTeX is not needed for plotting. Other Python/package combinations have not been verified here.

## Reproduce the plots

Download or clone this repository, then run from its root:

```bash
python -m venv .venv
# Activate the environment: Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python plotting/build_figures.py
```

The script creates `figures/` and writes PDF, SVG and PNG versions of:

- `Figure_1_Framework`
- `Figure_2_Performance`
- `Figure_3_Mechanisms`
- `Figure_4_Hourly_Case`
- `Figure_5_Signed_Emissions`
- `Figure_S1_Robustness`

Expected output: 18 image files and a completion message. Existing files with these names are overwritten. Plotting does not rerun optimization, independently replay saved schedules or recalculate confidence intervals. For replay and analysis, follow [`CODE_DATA_README.md`](CODE_DATA_README.md). File bytes can differ between rendering environments.

## Data provenance and access

**Public upstream sources:** the study uses NASA POWER weather and EIA-930/ERCO operating inputs. See [NASA POWER methodology](https://power.larc.nasa.gov/docs/) and [EIA-930 methodology](https://www.eia.gov/electricity/930-content/about.html). Their raw files are not included; `data/EXTERNAL_DATA_README.md` and `audit/eia_provenance.json` provide source URLs, checksums, acquisition details, and limitations.

**Derived/model-generated data:** the bundled CSV and JSON files contain analysis products, synthetic participant profiles or summaries, selected-hour diagnostics, fitted response parameters and calibration records. EIA production CO2 is estimated; the regional intervention response is observationally fitted and model-generated. These are not measured battery-induced emissions reductions. Reported changes are relative to fixed tasks and idle storage, rather than absolute grid emissions.

**Restricted data:** this release does not identify or include a restricted dataset. The absence of raw inputs is a release-scope limitation, not evidence that those inputs are restricted. Upstream public availability does not itself specify redistribution terms. Source-specific terms should be checked before redistributing raw files.

## Citation

Publication metadata has not been verified. Until a final citation is available, identify the manuscript by the title above and cite the exact repository commit used:

> Muhammad Abbas and Syed Sabahat Hussain Bukhari. “Failure conditions of finite-scenario emissions safeguards in a shared photovoltaic-storage simulation.” 2026. Code/data: https://github.com/shairabbas/PV-Storage-Emissions-Safeguards, commit [insert commit used].

No acceptance, journal publication or archival DOI is claimed. A code/data license has not yet been selected; upstream data retain their applicable terms.
