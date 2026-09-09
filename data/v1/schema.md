# CLEER Dashboard Data — Schema v1.0.0

Frozen contract for `/data/v1/models.json`. The dashboard and any external
consumer bind to this shape. Breaking changes require `/v2/`; additive fields
may be introduced within v1.

## Files

| File | Purpose |
| --- | --- |
| `models.json` | Full payload. What the dashboard fetches. |
| `meta.json` | Version, counts, checksum, licences. Cheap to poll. |
| `cleer-dashboard-data.csv` | Same figures as a flat table, one row per model × workload. |

Frozen release snapshots live at `/data/v1/releases/{YYYY-MM-DD}/`. The paths
above always serve the current release.

## What is deliberately absent

**Per-token energy intensities are not published.** The payload carries only
resolved per-session figures. Any field resembling a per-token intensity is a
defect — the build script fails on it.

## Top level

| Field | Type | Notes |
| --- | --- | --- |
| `schemaVersion` | string | Semver. `1.0.0`. |
| `generatedAt` | string | `YYYY-MM-DD`. |
| `methodology.engine` | string | Energy estimation version, e.g. `CLEER-Text-0826`. |
| `methodology.accounting` | string | Emissions methodology version. |
| `methodology.capability_and_cost_source` | string | `Artificial Analysis`. |
| `methodology.capability_and_cost_snapshot` | string | `YYYY-MM`. Moves faster than the energy factors; keep visible wherever cost is shown. |
| `scenario` | object | The single documented energy and carbon scenario. |
| `batchSizes` | number[] | Batch sizes for `batch_curve_wh`, in order. |
| `workloads` | object | Keyed `{use_case}.{tier}`, lowercase. |
| `models` | array | One entry per model, sorted by name. |

## `workloads[key]`

| Field | Type | Notes |
| --- | --- | --- |
| `use_case` | string | `Chat` or `Agentic`. |
| `tier` | string | `Light`, `Typical`, `Heavy`. |
| `unit` | string | The unit of one session. |
| `description` | string | Tooltip copy. Descriptive, never numeric. |

Token counts behind each workload are **not** published.

## `models[]`

| Field | Type | Notes |
| --- | --- | --- |
| `name` | string | Display name. Unique. |
| `kind` | string | `Closed` or `Open`. |
| `provider` | string | |
| `serving` | string | `GPU` or `TPU`. |
| `estimation_basis` | string | `CLEER proxy estimation`, `CLEER TPU calibration`, or `Directly measured`. |
| `confidence` | number \| null | 0–1. Null for TPU and open models. |
| `hardware` | string | |
| `intelligence_index` | number \| null | Artificial Analysis Intelligence Index. |
| `release_month` | string \| null | `YYYY-MM`. |
| `selected_batch_size` | number \| null | Open models only. |
| `proxies` | array | `{name, weight}`. Five entries for proxy-estimated models, empty otherwise. |
| `results` | object | Keyed by workload. |

### `results[workloadKey]`

| Field | Type | Notes |
| --- | --- | --- |
| `energy_wh.mean` | number | Total facility energy for one session. |
| `energy_wh.sd` | number \| null | Null for open models. |
| `carbon_gco2e.mean` | number | |
| `carbon_gco2e.sd` | number \| null | Null for open models. |
| `cost_usd` | number \| null | Same token basis as energy. |
| `energy_components_wh` | object | `accelerator`, `host`, `idle`, `cooling`. Sums to `energy_wh.mean`. |
| `carbon_components_gco2e` | object | `operational`, `embodied`, `construction`. Sums to `carbon_gco2e.mean`. |
| `batch_curve_wh` | number[] | Open models only. Aligned to `batchSizes`. |

## Consumer notes

- **Nulls are meaningful.** A null SD means the quantity does not apply, not zero. Render nothing rather than a zero band.
- **Components sum to totals** within floating-point tolerance (~1e-9 relative). Do not re-derive totals by summing.
- **Confidence bands**: >0.85 strong, 0.55–0.85 good, 0.30–0.55 weaker, <0.30 extrapolated.
- **One workload for every model.** Differences reflect the model, not usage. Verbosity is held constant.
- **Figures are central estimates** under one documented scenario.
