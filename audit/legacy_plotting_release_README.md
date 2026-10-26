# PV-Storage-Emissions-Safeguards

Plotting code and derived data accompanying **“Failure conditions of finite-scenario emissions safeguards in a shared photovoltaic-storage simulation.”**

## Study purpose

The study examines when forecast-based emissions safeguards can accept a schedule whose separately evaluated, reference-relative emissions change is positive. It compares shared-meter, flexible-demand and battery configurations, finite-scenario CVaR guards, a worst-scenario guard and a calibrated margin in a simulated photovoltaic–battery community. Synthetic merit-order regimes and a corrected ERCOT/ERCO regional-input check support diagnostic comparisons of operating expense, signed emissions and positive-change severity.

Results are conditional on the stated models and sampled dates. They do not establish a probability guarantee or measured real-world abatement. CV8/CV32 use different residual pools; CV32/CV128 use non-nested scenario sets. These comparisons do not isolate scenario count.

## Contents and release scope

| Path | Contents |
|---|---|
| `plotting/build_figures.py` | Regenerates the presentation plots from the supplied CSV files. |
| `plotting_data/` | Derived summary tables, paired scenario comparisons, selected-day hourly diagnostics, response coefficients and calibration/verification records. |
| `requirements.txt` | Versions used for the figure-build check of this release. |
| `SHA256SUMS.json` | SHA-256 checksums of the release files, excluding this checksum file. |

This is a **plotting and derived-data release**. It does not contain the optimizer, full simulation workflow, raw source inputs or complete saved schedules; it cannot independently reproduce the full study. Manuscript, supplementary document, literature files and pre-rendered figures are excluded. The script still generates all five main figures and the supplementary robustness plot locally.

The uploaded data are unchanged from the supplied revised package. The plotting script has one portability adjustment: it creates its output directory if absent.

## Software requirements

Python with NumPy, pandas and Matplotlib is required. A figure-build check was performed with Python 3.12.14 and the pinned package versions in `requirements.txt`. No optimization solver or LaTeX installation is needed for this plotting workflow. Other Python/package combinations have not been verified here.

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

Expected output: 18 image files and a completion message. Existing files with these names are overwritten. Plotting does not rerun optimization, independently replay saved schedules or recalculate confidence intervals. File bytes can differ between rendering environments.

## Data provenance and access

**Public upstream sources:** the study uses NASA POWER weather and EIA-930/ERCO operating inputs. See [NASA POWER methodology](https://power.larc.nasa.gov/docs/) and [EIA-930 methodology](https://www.eia.gov/electricity/930-content/about.html). Their raw files and acquisition manifests are not included in this release; exact extraction versions, URLs and checksums must be supplied with any future full-data release.

**Derived/model-generated data:** the bundled CSV and JSON files contain analysis products, synthetic participant profiles or summaries, selected-hour diagnostics, fitted response parameters and calibration records. EIA production CO2 is estimated; the regional intervention response is observationally fitted and model-generated. These are not measured battery-induced emissions reductions. Reported changes are relative to fixed tasks and idle storage, rather than absolute grid emissions.

**Restricted data:** this release does not identify or include a restricted dataset. The absence of raw inputs is a release-scope limitation, not evidence that those inputs are restricted. Upstream public availability does not itself specify redistribution terms. **[VERIFY before extending this release: source-specific terms and any access restrictions.]**

## Citation

Publication metadata has not been verified. Until a final citation is available, identify the manuscript by the title above and cite the exact repository commit used:

> [VERIFY: authors]. “Failure conditions of finite-scenario emissions safeguards in a shared photovoltaic-storage simulation.” [VERIFY: publication year, venue and DOI, if assigned]. Code/data: https://github.com/shairabbas/PV-Storage-Emissions-Safeguards, commit [insert commit used].

No acceptance, journal publication or archival DOI is claimed. Code/data licensing is **[VERIFY: author-selected license not yet supplied]**; upstream data retain their applicable terms.
