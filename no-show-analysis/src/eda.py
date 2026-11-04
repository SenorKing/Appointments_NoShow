"""
Exploratory charts -> reports/figures/*.png

Run:  python src/eda.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import seaborn as sns

from clean import AGE_LABELS, LEAD_LABELS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "appointments_clean.csv"
FIG = ROOT / "reports" / "figures"

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

sns.set_theme(style="whitegrid", rc={
    "axes.edgecolor": GRID, "grid.color": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlelocation": "left",
    "font.size": 11, "figure.dpi": 150, "axes.grid.axis": "y",
})


def pct_axis(ax, axis="y"):
    fmt = mtick.PercentFormatter(1.0, decimals=0)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def label_bars(ax, fmt="{:.0%}", horizontal=False):
    for c in ax.containers:
        ax.bar_label(c, labels=[fmt.format(v) for v in c.datavalues], padding=3,
                     fontsize=9, color=MUTED)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


def overall_line(ax, rate, horizontal=False):
    kw = dict(color=MUTED, lw=1, ls="--")
    (ax.axvline if horizontal else ax.axhline)(rate, **kw)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA, parse_dates=["scheduled_at", "appointment_date"])
    overall = df["no_show"].mean()

    # 1. Lead time
    r = df.groupby("lead_bucket")["no_show"].mean().reindex(LEAD_LABELS)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(r.index, r.values, color=BLUE, width=0.65)
    overall_line(ax, overall)
    ax.text(-0.3, overall + 0.008, f"overall {overall:.0%}", ha="left", fontsize=9, color=MUTED)
    label_bars(ax); pct_axis(ax)
    ax.set(title="The longer the wait, the more likely a patient skips", xlabel="Days between booking and appointment", ylabel="No-show rate")
    save(fig, "01_lead_time.png")

    # 2. SMS paradox
    sub = df[df["lead_days"] >= 3]
    raw = df.groupby("sms_received")["no_show"].mean()
    s = (sub.groupby(["lead_bucket", "sms_received"])["no_show"].mean()
            .unstack().reindex(LEAD_LABELS[2:]))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = range(len(s))
    w = 0.38
    ax.bar([i - w / 2 for i in x], s[0], w, color=ORANGE, label="No SMS")
    ax.bar([i + w / 2 for i in x], s[1], w, color=BLUE, label="SMS reminder")
    ax.set_xticks(list(x), s.index)
    label_bars(ax); pct_axis(ax)
    ax.legend(frameon=False, loc="upper left")
    ax.set(title="Within the same wait time, SMS reminders cut no-shows",
           xlabel="Days between booking and appointment (SMS only sent for 3+ day waits)", ylabel="No-show rate")
    ax.text(0, -0.24, f"Raw comparison is misleading: {raw[1]:.1%} no-show with SMS vs {raw[0]:.1%} without, "
            "because same-day visits (rarely missed) never got one.", transform=ax.transAxes, fontsize=9, color=MUTED)
    save(fig, "02_sms_by_lead_time.png")

    # 3. Age
    a = df.groupby("age_group")["no_show"].mean().reindex(AGE_LABELS)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(a.index, a.values, color=BLUE, width=0.65)
    overall_line(ax, overall)
    label_bars(ax); pct_axis(ax)
    ax.set(title="Teens and young adults miss the most appointments", xlabel="Age group", ylabel="No-show rate")
    save(fig, "03_age.png")

    # 4. Patient history
    hist = pd.cut(df["prior_no_shows"].where(df["prior_appts"] > 0, -1), [-2, -0.5, 0.5, 1.5, 100],
                  labels=["First visit\nin window", "Attended all\nprior visits", "Missed 1\nprior visit", "Missed 2+\nprior visits"])
    h = df.groupby(hist, observed=True)["no_show"].agg(["mean", "size"])
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(h.index.astype(str), h["mean"], color=BLUE, width=0.6)
    overall_line(ax, overall)
    label_bars(ax); pct_axis(ax)
    for i, n in enumerate(h["size"]):
        ax.text(i, 0.01, f"n={n:,}", ha="center", color="white", fontsize=8.5)
    ax.set(title="Past no-shows are the strongest warning sign", xlabel="", ylabel="No-show rate")
    save(fig, "04_patient_history.png")

    # 5. Health and welfare factors
    factors = {"Welfare (Bolsa Família)": "welfare", "Alcoholism": "alcoholism", "Handicap": "has_handicap",
               "Diabetes": "diabetes", "Hypertension": "hypertension"}
    rows = [(k, df.loc[df[c] == 0, "no_show"].mean(), df.loc[df[c] == 1, "no_show"].mean()) for k, c in factors.items()]
    f = pd.DataFrame(rows, columns=["factor", "without", "with"]).set_index("factor")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    y = range(len(f))
    ax.barh([i + 0.2 for i in y], f["without"], 0.38, color=ORANGE, label="Without")
    ax.barh([i - 0.2 for i in y], f["with"], 0.38, color=BLUE, label="With")
    ax.set_yticks(list(y), f.index); ax.invert_yaxis()
    label_bars(ax); pct_axis(ax, "x")
    ax.set_xlim(0, 0.3)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="lower right")
    ax.set(title="Chronic patients show up more; welfare recipients less", xlabel="No-show rate", ylabel="")
    save(fig, "05_health_factors.png")

    # 6. Neighbourhood spread
    n = df.groupby("neighbourhood")["no_show"].agg(["mean", "size"]).query("size >= 500").sort_values("mean")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.scatter(n["size"], n["mean"], s=28, color=BLUE, edgecolor="white", linewidth=1)
    overall_line(ax, overall)
    for name, row in pd.concat([n.tail(3), n.head(2)]).iterrows():
        ax.annotate(name, (row["size"], row["mean"]), xytext=(5, 3), textcoords="offset points", fontsize=8.5, color=MUTED)
    pct_axis(ax); ax.set_xscale("log")
    ax.xaxis.set_major_locator(mtick.FixedLocator([500, 1000, 2000, 4000, 8000]))
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.xaxis.set_minor_formatter(mtick.NullFormatter())
    ax.set(title=f"No-show rate varies {n['mean'].min():.0%}–{n['mean'].max():.0%} across neighbourhoods",
           xlabel="Appointments in neighbourhood (log scale, min 500)", ylabel="No-show rate")
    save(fig, "06_neighbourhoods.png")


if __name__ == "__main__":
    main()
