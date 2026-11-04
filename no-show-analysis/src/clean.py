"""
Clean the raw Kaggle "Medical Appointment No Shows" data and engineer features.

Outputs
-------
data/processed/appointments_clean.csv   tidy, analysis-ready table
data/processed/appointments.db          same table in SQLite (for sql/analysis.sql)

Run:  python src/clean.py
"""
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "appointments.csv"
OUT_DIR = ROOT / "data" / "processed"

COLUMN_MAP = {
    "PatientId": "patient_id",
    "AppointmentID": "appointment_id",
    "Gender": "gender",
    "ScheduledDay": "scheduled_at",
    "AppointmentDay": "appointment_date",
    "Age": "age",
    "Neighbourhood": "neighbourhood",
    "Scholarship": "welfare",          # enrolled in Bolsa Família welfare programme
    "Hipertension": "hypertension",    # fix original typos
    "Diabetes": "diabetes",
    "Alcoholism": "alcoholism",
    "Handcap": "handicap_level",
    "SMS_received": "sms_received",
    "No-show": "no_show",
}

AGE_BINS = [-1, 12, 17, 29, 44, 59, 74, 200]
AGE_LABELS = ["0-12", "13-17", "18-29", "30-44", "45-59", "60-74", "75+"]
LEAD_BINS = [-1, 0, 2, 7, 14, 30, 60, 1000]
LEAD_LABELS = ["Same day", "1-2 days", "3-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load_raw(path: Path = RAW) -> pd.DataFrame:
    return pd.read_csv(path).rename(columns=COLUMN_MAP)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Fix types and drop impossible records. Returns the frame and a log of what was removed."""
    log = {"raw_rows": len(df)}
    df = df.copy()

    # IDs: PatientId was stored as float; a handful aren't whole numbers -> keep as string
    df["patient_id"] = df["patient_id"].apply(lambda x: f"{x:.0f}" if float(x).is_integer() else str(x))
    df["scheduled_at"] = pd.to_datetime(df["scheduled_at"]).dt.tz_localize(None)
    df["appointment_date"] = pd.to_datetime(df["appointment_date"]).dt.tz_localize(None).dt.normalize()
    df["no_show"] = (df["no_show"] == "Yes").astype(int)
    df["neighbourhood"] = df["neighbourhood"].str.title()

    # Impossible values
    bad_age = df["age"] < 0
    log["dropped_negative_age"] = int(bad_age.sum())
    df = df[~bad_age]

    df["lead_days"] = (df["appointment_date"] - df["scheduled_at"].dt.normalize()).dt.days
    bad_lead = df["lead_days"] < 0  # appointment before it was booked
    log["dropped_negative_lead_time"] = int(bad_lead.sum())
    df = df[~bad_lead]

    log["clean_rows"] = len(df)
    return df.reset_index(drop=True), log


def engineer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["has_handicap"] = (df["handicap_level"] > 0).astype(int)
    df["chronic_conditions"] = df[["hypertension", "diabetes", "alcoholism", "has_handicap"]].sum(axis=1)
    df["is_female"] = (df["gender"] == "F").astype(int)

    df["age_group"] = pd.cut(df["age"], AGE_BINS, labels=AGE_LABELS).astype(str)
    df["same_day"] = (df["lead_days"] == 0).astype(int)
    df["lead_bucket"] = pd.cut(df["lead_days"], LEAD_BINS, labels=LEAD_LABELS).astype(str)

    df["appt_weekday"] = df["appointment_date"].dt.dayofweek.map(dict(enumerate(WEEKDAYS)))
    df["sched_weekday"] = df["scheduled_at"].dt.dayofweek.map(dict(enumerate(WEEKDAYS)))
    df["sched_hour"] = df["scheduled_at"].dt.hour

    # Patient history, using only appointments on EARLIER dates (no peeking at the outcome
    # of the current appointment or same-day ones). Window = what's in the dataset.
    df = df.sort_values(["patient_id", "appointment_date", "scheduled_at"]).reset_index(drop=True)
    g = df.groupby("patient_id")
    df["total_appts_in_window"] = g["appointment_id"].transform("count")

    daily = (df.groupby(["patient_id", "appointment_date"])
               .agg(n=("no_show", "size"), ns=("no_show", "sum"))
               .groupby(level=0).cumsum()
               .groupby(level=0).shift(1, fill_value=0)
               .rename(columns={"n": "prior_appts", "ns": "prior_no_shows"}))
    df = df.merge(daily, left_on=["patient_id", "appointment_date"], right_index=True, how="left")
    df["prior_no_show_rate"] = np.where(df["prior_appts"] > 0, df["prior_no_shows"] / df["prior_appts"], np.nan)
    df["is_returning"] = (df["prior_appts"] > 0).astype(int)

    return df.sort_values(["appointment_date", "scheduled_at"]).reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, log = clean(load_raw())
    df = engineer(df)

    df.to_csv(OUT_DIR / "appointments_clean.csv", index=False)
    with sqlite3.connect(OUT_DIR / "appointments.db") as con:
        out = df.copy()
        out["scheduled_at"] = out["scheduled_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
        out["appointment_date"] = out["appointment_date"].dt.strftime("%Y-%m-%d")
        out.to_sql("appointments", con, if_exists="replace", index=False)

    for k, v in log.items():
        print(f"{k:>28}: {v:,}")
    print(f"{'overall no-show rate':>28}: {df['no_show'].mean():.1%}")


if __name__ == "__main__":
    main()
