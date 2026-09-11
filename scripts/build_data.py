#!/usr/bin/env python3
"""
Build /data/v1/models.json and meta.json from the pipeline CSV export,
validating on the way. Fails loudly rather than publishing bad data.

    python3 scripts/build_data.py data/v1/cleer-dashboard-data.csv

Run in CI on every PR. A non-zero exit blocks the deploy.
"""
import sys, csv, json, math, hashlib, datetime, os, re

SCHEMA = "1.0.0"
ENGINE = "CLEER-Text-0926"
ACCOUNTING = "Closed-AI-Emissions-Methodology-0926"
AA_SNAPSHOT = "2026-09"
BATCHES = [32, 64, 128, 256, 384]
OUT_DIR = os.path.join("data", "v1")

# Any published field matching these is an IP leak. The guard is the point.
FORBIDDEN = re.compile(
    r"(per[_ ]?token|\bwh_per_\w*token|\be_in\b|\be_out\b|\bintensity\b|"
    r"\bcache_price\w*|\btokens_in\w*|\btokens_out\w*|\buncached\b|"
    r"\bcached_tokens\b|\be_in_wh\w*|\be_out_wh\w*)", re.I)

BASES = {"CLEER proxy estimation", "CLEER TPU calibration", "Directly measured"}
errors, warnings = [], []


def err(m): errors.append(m)
def warn(m): warnings.append(m)
def num(v):
    if v in ("", None): return None
    try: return float(v)
    except ValueError: return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT_DIR, "cleer-dashboard-data.csv")
    if not os.path.exists(path):
        print(f"input not found: {path}"); sys.exit(1)

    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("no rows"); sys.exit(1)

    # --- IP guard on column names -------------------------------------------
    for col in rows[0].keys():
        if FORBIDDEN.search(col or ""):
            err(f"IP GUARD: column '{col}' looks like a per-token intensity and must not be published")

    models, workloads = {}, {}
    for r in rows:
        nm = (r.get("model_name") or "").strip()
        if not nm: continue
        key = f"{(r.get('use_case') or '').strip().lower()}.{(r.get('tier') or '').strip().lower()}"
        workloads.setdefault(key, {
            "use_case": r.get("use_case"), "tier": r.get("tier"),
            "unit": r.get("unit"), "description": r.get("dashboard_description")})

        m = models.setdefault(nm, {
            "name": nm, "kind": r.get("kind"), "provider": r.get("provider"),
            "serving": r.get("serving"), "estimation_basis": r.get("estimation_basis"),
            "confidence": num(r.get("confidence")), "hardware": r.get("hardware"),
            "intelligence_index": num(r.get("aa_intelligence_index")),
            "release_month": (r.get("release_month") or None),
            "selected_batch_size": num(r.get("selected_batch_size")),
            "proxies": [{"name": r.get(f"proxy_{i}"), "weight": num(r.get(f"proxy_{i}_w"))}
                        for i in range(1, 6) if (r.get(f"proxy_{i}") or "").strip()],
            "results": {}})

        is_open = m["kind"] == "Open"
        ec = [num(r.get(k)) for k in ("e_accelerator_wh", "e_host_wh", "e_idle_wh", "e_cooling_wh")]
        cc = [num(r.get(k)) for k in ("c_operational_gco2e", "c_embodied_gco2e", "c_construction_gco2e")]
        res = {
            "energy_wh": {"mean": num(r.get("energy_wh_mean")),
                          "sd": None if is_open else num(r.get("energy_wh_sd"))},
            "carbon_gco2e": {"mean": num(r.get("carbon_gco2e_mean")),
                             "sd": None if is_open else num(r.get("carbon_gco2e_sd"))},
            "cost_usd": num(r.get("cost_usd")),
            "energy_components_wh": dict(zip(("accelerator", "host", "idle", "cooling"), ec)),
            "carbon_components_gco2e": dict(zip(("operational", "embodied", "construction"), cc)),
        }
        if is_open:
            curve = [num(r.get(f"curve_b{b}_wh")) for b in BATCHES]
            if all(v is not None for v in curve):
                res["batch_curve_wh"] = curve
            else:
                err(f"{nm} [{key}]: open model missing batch curve points")
        models[nm] = m
        m["results"][key] = res

        # --- per-row validation ---
        e, c = res["energy_wh"]["mean"], res["carbon_gco2e"]["mean"]
        if e is None or e <= 0: err(f"{nm} [{key}]: energy missing or non-positive")
        if c is None or c <= 0: err(f"{nm} [{key}]: carbon missing or non-positive")
        if None not in ec and e is not None and not math.isclose(sum(ec), e, rel_tol=1e-6, abs_tol=1e-7):
            err(f"{nm} [{key}]: energy components {sum(ec):.6g} != total {e:.6g}")
        if None not in cc and c is not None and not math.isclose(sum(cc), c, rel_tol=1e-6, abs_tol=1e-7):
            err(f"{nm} [{key}]: carbon components {sum(cc):.6g} != total {c:.6g}")

    ml = list(models.values())

    # --- structural validation ---------------------------------------------
    nwl = len(workloads)
    if nwl != 6: err(f"expected 6 workloads, found {nwl}")
    for m in ml:
        if len(m["results"]) != nwl:
            err(f"{m['name']}: {len(m['results'])} workloads, expected {nwl}")
        if m["estimation_basis"] not in BASES:
            err(f"{m['name']}: unknown estimation_basis '{m['estimation_basis']}'")
        if m["estimation_basis"] == "CLEER proxy estimation":
            if m["confidence"] is None: err(f"{m['name']}: proxy model without confidence")
            if len(m["proxies"]) != 5: err(f"{m['name']}: {len(m['proxies'])} proxies, expected 5")
            w = sum(p["weight"] or 0 for p in m["proxies"])
            if not 0.9 <= w <= 1.1: warn(f"{m['name']}: proxy weights sum to {w:.3f}")
        if m["serving"] == "TPU" and (m["confidence"] is not None or m["proxies"]):
            err(f"{m['name']}: TPU model should carry no confidence and no proxies")
        if m["kind"] == "Open" and any(
                r["energy_wh"]["sd"] is not None or r["carbon_gco2e"]["sd"] is not None
                for r in m["results"].values()):
            err(f"{m['name']}: open model must not publish a standard deviation")
        for f in ("intelligence_index", "release_month"):
            if m[f] in (None, ""): warn(f"{m['name']}: missing {f}")

    # --- IP guard on values -------------------------------------------------
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if FORBIDDEN.search(str(k)):
                    err(f"IP GUARD: field '{k}' must not be published")
                walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(ml)

    if errors:
        print(f"BUILD FAILED — {len(errors)} error(s):")
        for e in errors[:40]: print("  -", e)
        if warnings:
            print(f"\n{len(warnings)} warning(s):")
            for w in warnings[:10]: print("  -", w)
        sys.exit(1)

    payload = {
        "schemaVersion": SCHEMA,
        "generatedAt": datetime.date.today().isoformat(),
        "methodology": {"engine": ENGINE, "accounting": ACCOUNTING,
                        "capability_and_cost_source": "Artificial Analysis",
                        "capability_and_cost_snapshot": AA_SNAPSHOT},
        "scenario": {"grid": "behind-the-meter gas", "grid_gco2e_per_kwh": 640,
                     "facility": "US-average data center",
                     "note": "One documented scenario. The methodology supports alternatives."},
        "batchSizes": BATCHES,
        "workloads": workloads,
        "models": sorted(ml, key=lambda x: x["name"]),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    blob = json.dumps(payload, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "models.json"), "w") as f: f.write(blob)
    meta = {"schemaVersion": SCHEMA, "generatedAt": payload["generatedAt"],
            "methodology": payload["methodology"], "scenario": payload["scenario"],
            "counts": {"models": len(ml),
                       "closed": sum(1 for m in ml if m["kind"] == "Closed"),
                       "open": sum(1 for m in ml if m["kind"] == "Open"),
                       "workloads": nwl},
            "sha256": hashlib.sha256(blob.encode()).hexdigest(),
            "license": {"data": "CC BY-NC 4.0", "code": "Apache-2.0", "methodology": "CC BY 4.0"}}
    with open(os.path.join(OUT_DIR, "meta.json"), "w") as f: f.write(json.dumps(meta, indent=2))

    print(f"OK — {len(ml)} models, {nwl} workloads, {len(rows)} rows")
    print(f"   sha256 {meta['sha256'][:16]}…")
    if warnings:
        print(f"   {len(warnings)} warning(s):")
        for w in warnings[:10]: print("     -", w)


if __name__ == "__main__":
    main()
