# CLEER Dashboard

Public data and code for the [CLEER Dashboard](https://github.com/sustainableaigroup/CLEER) by
[Sustainable AI Group](https://sustainableaigroup.com/), which estimates the energy and carbon of
AI inference for closed and open models. Methodology: [CLEER Technical Report](https://reports.sustainableaigroup.com/CLEER-Tech-Report).

## Changelog

Newest first. Data releases follow the CLEER version (e.g. CLEER-Text-0926); dashboard
features can ship between data releases.

### 2026-10-30 · Dashboard update
- Added **Account for verbosity variation?** toggle. When on, each model's output tokens are
  scaled by its verbosity relative to the median model, based on Artificial Analysis
  Intelligence Index output tokens per task. Models without verbosity data are hidden while
  the toggle is on.
- Header now shows **Data updated** (current data release) and **Dashboard updated**
  (latest build) separately.
- Data schema 1.1.0: adds `verbosity_factor`, `results_verbosity_adjusted` and `dataUpdated`.
  Existing fields are unchanged.

### 2026-09-29 · Launch (CLEER-Text-0926)
- Public launch of the CLEER Dashboard: 51 models (35 closed, 16 open) across chat and agentic
  workloads, with energy and carbon per session and adjustable PUE and grid intensity.

## License

This repository uses separate licenses for software and data:

- Software in `/app` and `/scripts` is licensed under the
  [Apache License 2.0](LICENSE).
- Data in `/data` is licensed under the
  [Creative Commons Attribution-NonCommercial 4.0 International License](data/LICENSE).

Commercial use of the data requires separate written permission from
[Sustainable AI Group](https://sustainableaigroup.com/).

Unless explicitly stated otherwise, documentation and other repository content
are licensed under the Apache License 2.0.
