"""
Predict which appointments will be missed.

Use case: the day before an appointment, the clinic ranks tomorrow's patients by
risk and calls / double-books for the riskiest ones. So every feature must be
known by then (no outcome of the current visit, no future visits).

Validation: TIME-BASED split. Train on appointments before 2016-05-25,
test on 2016-05-25 onward - the model is judged on "future" days it never saw.

Outputs: reports/metrics.json, reports/figures/07-09_*.png

Run:  python src/model.py
"""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import eda  # noqa: F401  (applies the shared chart style)
from eda import BLUE, ORANGE, MUTED, save, pct_axis

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "appointments_clean.csv"
REPORTS = ROOT / "reports"
SPLIT_DATE = "2016-05-25"
SEED = 42

NUMERIC = ["age", "lead_days", "sched_hour", "prior_appts", "prior_no_shows", "prior_rate_filled",
           "is_returning", "same_day", "sms_received", "is_female", "welfare",
           "hypertension", "diabetes", "alcoholism", "handicap_level"]
CATEGORICAL = ["appt_weekday", "neighbourhood"]

FRIENDLY = {
    "lead_days": "Lead time (days)", "same_day": "Same-day booking", "age": "Age",
    "prior_no_shows": "Prior no-shows", "prior_rate_filled": "Prior no-show rate",
    "prior_appts": "Prior appointments", "is_returning": "Returning patient",
    "sms_received": "SMS received", "sched_hour": "Hour booked", "welfare": "Welfare enrolment",
    "neighbourhood": "Neighbourhood", "appt_weekday": "Weekday", "is_female": "Female",
    "hypertension": "Hypertension", "diabetes": "Diabetes", "alcoholism": "Alcoholism",
    "handicap_level": "Handicap level",
}


def load():
    df = pd.read_csv(DATA, parse_dates=["appointment_date"])
    df["prior_rate_filled"] = df["prior_no_show_rate"].fillna(-1)  # -1 = no history
    train = df[df["appointment_date"] < SPLIT_DATE]
    test = df[df["appointment_date"] >= SPLIT_DATE]
    return train, test


def build_models():
    ohe = OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=200, sparse_output=False)
    logreg = Pipeline([
        ("prep", ColumnTransformer([("num", StandardScaler(), NUMERIC), ("cat", ohe, CATEGORICAL)])),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])
    gbm = Pipeline([
        ("prep", ColumnTransformer([("num", "passthrough", NUMERIC),
                                    ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=200,
                                                          sparse_output=False), CATEGORICAL)])),
        ("clf", HistGradientBoostingClassifier(learning_rate=0.05, max_iter=400, max_leaf_nodes=31,
                                               l2_regularization=1.0, early_stopping=True,
                                               validation_fraction=0.15, random_state=SEED)),
    ])
    return {"Logistic regression": logreg, "Gradient boosting": gbm}


def capture_at(y, p, frac):
    """Share of all no-shows found if staff contact the top `frac` riskiest appointments."""
    k = int(len(p) * frac)
    top = np.argsort(-p)[:k]
    return y[top].sum() / y.sum()


def main() -> None:
    train, test = load()
    X_tr, y_tr = train[NUMERIC + CATEGORICAL], train["no_show"].values
    X_te, y_te = test[NUMERIC + CATEGORICAL], test["no_show"].values
    print(f"train {len(train):,} rows (no-show {y_tr.mean():.1%}) | test {len(test):,} rows (no-show {y_te.mean():.1%})")

    results, probs = {}, {}
    for name, model in build_models().items():
        model.fit(X_tr, y_tr)
        p = model.predict_proba(X_te)[:, 1]
        probs[name] = p
        results[name] = {
            "roc_auc": round(roc_auc_score(y_te, p), 3),
            "pr_auc": round(average_precision_score(y_te, p), 3),
            "capture_top_20pct": float(round(capture_at(y_te, p, 0.20), 3)),
            "capture_top_30pct": float(round(capture_at(y_te, p, 0.30), 3)),
        }
        print(f"{name:>20}: {results[name]}")

    # Simple rule-of-thumb baseline: rank by lead time only
    base = test["lead_days"].values.astype(float)
    results["Baseline: lead time only"] = {
        "roc_auc": round(roc_auc_score(y_te, base), 3),
        "pr_auc": round(average_precision_score(y_te, base), 3),
        "capture_top_20pct": float(round(capture_at(y_te, base + np.random.default_rng(SEED).random(len(base)) * 1e-3, 0.20), 3)),
        "capture_top_30pct": float(round(capture_at(y_te, base + np.random.default_rng(SEED).random(len(base)) * 1e-3, 0.30), 3)),
    }
    print(f"{'Baseline':>20}: {results['Baseline: lead time only']}")

    best = max((k for k in probs), key=lambda k: results[k]["roc_auc"])
    model = build_models()[best].fit(X_tr, y_tr)

    # Permutation importance on the raw columns (model-agnostic, measured on the test period)
    sample = X_te.sample(n=min(8000, len(X_te)), random_state=SEED)
    imp = permutation_importance(model, sample, y_te[X_te.index.get_indexer(sample.index)],
                                 scoring="roc_auc", n_repeats=5, random_state=SEED, n_jobs=-1)
    importance = (pd.Series(imp.importances_mean, index=sample.columns)
                    .rename(FRIENDLY).sort_values(ascending=False))

    meta = {
        "split_date": SPLIT_DATE, "train_rows": len(train), "test_rows": len(test),
        "test_no_show_rate": round(float(y_te.mean()), 3), "best_model": best,
        "models": results, "permutation_importance_roc_auc_drop": importance.round(4).to_dict(),
    }
    (REPORTS / "metrics.json").write_text(json.dumps(meta, indent=2))

    # --- Figures -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for (name, p), c in zip(probs.items(), [ORANGE, BLUE]):
        fpr, tpr, _ = roc_curve(y_te, p)
        ax.plot(fpr, tpr, color=c, lw=2, label=f"{name} (AUC {results[name]['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], color=MUTED, lw=1, ls="--", label="Random (AUC 0.50)")
    ax.set(title="ROC curve on held-out future dates", xlabel="False positive rate", ylabel="True positive rate")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "07_roc_curve.png")

    top = importance.head(10)[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(top.index, top.values, color=BLUE, height=0.6)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set(title=f"What drives the prediction ({best.lower()})",
           xlabel="Drop in ROC-AUC when the feature is shuffled", ylabel="")
    save(fig, "08_feature_importance.png")

    fracs = np.linspace(0.01, 1, 100)
    pd.DataFrame({"share_contacted": fracs.round(2),
                  "model_capture": [round(capture_at(y_te, probs[best], f), 4) for f in fracs],
                  "random_capture": fracs.round(2)}).to_csv(REPORTS / "capture_curve.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(fracs, [capture_at(y_te, probs[best], f) for f in fracs], color=BLUE, lw=2, label=best)
    ax.plot(fracs, fracs, color=MUTED, lw=1, ls="--", label="Random outreach")
    c20 = results[best]["capture_top_20pct"]
    ax.scatter([0.2], [c20], s=60, color=BLUE, edgecolor="white", zorder=3)
    ax.annotate(f"Call the riskiest 20%\n→ reach {c20:.0%} of no-shows", (0.2, c20), xytext=(0.33, c20 - 0.2),
                fontsize=9.5, color=MUTED, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    pct_axis(ax); pct_axis(ax, "x")
    ax.set(title="Targeting outreach with the model", xlabel="Share of appointments contacted (highest risk first)",
           ylabel="Share of no-shows reached")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "09_capture_curve.png")
    print(f"\nTop features:\n{importance.head(8).round(4).to_string()}")


if __name__ == "__main__":
    main()
