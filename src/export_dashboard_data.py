"""
Export small aggregate tables for the interactive dashboard -> reports/dashboard_data/*.csv
Run after model.py:  python src/export_dashboard_data.py
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from clean import AGE_LABELS, LEAD_LABELS

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUT = REPORTS / "dashboard_data"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ROOT / "data/processed/appointments_clean.csv")
    m = json.loads((REPORTS / "metrics.json").read_text())

    # Breakdowns: one long table, one row per (dimension, group)
    rows = []
    def add(dim, key, order):
        g = df.groupby(key)
        t = pd.DataFrame({"appointments": g.size(), "no_show_rate": g["no_show"].mean(),
                          "rate_no_sms": df[df.sms_received == 0].groupby(key)["no_show"].mean(),
                          "rate_sms": df[df.sms_received == 1].groupby(key)["no_show"].mean()}).reindex(order)
        for i, (grp, r) in enumerate(t.iterrows()):
            rows.append({"dimension": dim, "group": grp, "sort": i, **r.to_dict()})
    add("lead_time", "lead_bucket", LEAD_LABELS)
    add("age", "age_group", AGE_LABELS)
    hist = np.select([df.prior_appts == 0, df.prior_no_shows == 0, df.prior_no_shows == 1],
                     ["First visit in window", "Attended all prior", "Missed 1 prior"], "Missed 2+ prior")
    df["history"] = hist
    add("history", "history", ["First visit in window", "Attended all prior", "Missed 1 prior", "Missed 2+ prior"])
    b = pd.DataFrame(rows)
    b[["no_show_rate", "rate_no_sms", "rate_sms"]] = b[["no_show_rate", "rate_no_sms", "rate_sms"]].round(4)
    b["appointments"] = b["appointments"].astype(int)
    b.to_csv(OUT / "breakdowns.csv", index=False)

    # Headline figures
    elig = df[df.lead_days >= 3]
    fit = smf.logit("no_show ~ sms_received + C(lead_bucket) + age + I(age**2) + welfare + hypertension"
                    " + diabetes + is_female + prior_no_shows", data=elig).fit(disp=0)
    ci = np.exp(fit.conf_int().loc["sms_received"])
    best = m["models"][m["best_model"]]
    kpis = [
        ("appointments", len(df)), ("patients", df.patient_id.nunique()),
        ("no_show_rate", round(df.no_show.mean(), 4)), ("same_day_share", round(df.same_day.mean(), 4)),
        ("raw_rate_sms", round(df[df.sms_received == 1].no_show.mean(), 4)),
        ("raw_rate_no_sms", round(df[df.sms_received == 0].no_show.mean(), 4)),
        ("sms_odds_ratio", round(np.exp(fit.params["sms_received"]), 3)),
        ("sms_or_ci_low", round(ci.iloc[0], 3)), ("sms_or_ci_high", round(ci.iloc[1], 3)),
        ("best_roc_auc", best["roc_auc"]), ("capture_top_20pct", best["capture_top_20pct"]),
        ("test_rows", m["test_rows"]),
    ]
    pd.DataFrame(kpis, columns=["metric", "value"]).to_csv(OUT / "kpis.csv", index=False)

    pd.DataFrame([{"model": k, **v} for k, v in m["models"].items()]).to_csv(OUT / "models.csv", index=False)
    pd.Series(m["permutation_importance_roc_auc_drop"], name="auc_drop").rename_axis("feature") \
      .reset_index().head(8).to_csv(OUT / "importance.csv", index=False)
    (OUT / "capture_curve.csv").write_text((REPORTS / "capture_curve.csv").read_text())
    print("exported", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
