-- Medical appointment no-show analysis (SQLite)
-- Table: appointments  (built by src/clean.py)
-- Run all queries and save results:  python src/run_sql.py
-- Each query starts with a "-- name:" line so the runner can label results.

-- name: 1. Overall summary
SELECT
    COUNT(*)                                   AS appointments,
    COUNT(DISTINCT patient_id)                 AS patients,
    SUM(no_show)                               AS no_shows,
    ROUND(100.0 * AVG(no_show), 1)             AS no_show_pct,
    MIN(appointment_date)                      AS first_appt,
    MAX(appointment_date)                      AS last_appt
FROM appointments;

-- name: 2. No-show rate by lead time (days between booking and visit)
SELECT
    lead_bucket,
    COUNT(*)                                   AS appointments,
    ROUND(100.0 * AVG(no_show), 1)             AS no_show_pct
FROM appointments
GROUP BY lead_bucket
ORDER BY MIN(lead_days);

-- name: 3. SMS reminders look harmful... until you control for lead time
-- SMS were never sent for same-day bookings (which almost always show up),
-- so the raw comparison is confounded. Compare within lead-time buckets instead.
SELECT
    lead_bucket,
    ROUND(100.0 * AVG(CASE WHEN sms_received = 0 THEN no_show END), 1) AS no_sms_pct,
    ROUND(100.0 * AVG(CASE WHEN sms_received = 1 THEN no_show END), 1) AS sms_pct,
    SUM(sms_received)                                                  AS sms_appts,
    SUM(1 - sms_received)                                              AS no_sms_appts
FROM appointments
GROUP BY lead_bucket
ORDER BY MIN(lead_days);

-- name: 4. No-show rate by age group
SELECT
    age_group,
    COUNT(*)                                   AS appointments,
    ROUND(100.0 * AVG(no_show), 1)             AS no_show_pct
FROM appointments
GROUP BY age_group
ORDER BY MIN(age);

-- name: 5. Chronic conditions and welfare enrolment
SELECT 'Hypertension' AS factor, hypertension AS has_factor, COUNT(*) AS appointments,
       ROUND(100.0 * AVG(no_show), 1) AS no_show_pct FROM appointments GROUP BY hypertension
UNION ALL
SELECT 'Diabetes', diabetes, COUNT(*), ROUND(100.0 * AVG(no_show), 1) FROM appointments GROUP BY diabetes
UNION ALL
SELECT 'Alcoholism', alcoholism, COUNT(*), ROUND(100.0 * AVG(no_show), 1) FROM appointments GROUP BY alcoholism
UNION ALL
SELECT 'Handicap', has_handicap, COUNT(*), ROUND(100.0 * AVG(no_show), 1) FROM appointments GROUP BY has_handicap
UNION ALL
SELECT 'Welfare (Bolsa Familia)', welfare, COUNT(*), ROUND(100.0 * AVG(no_show), 1) FROM appointments GROUP BY welfare;

-- name: 6. Day of week
SELECT
    appt_weekday,
    COUNT(*)                                   AS appointments,
    ROUND(100.0 * AVG(no_show), 1)             AS no_show_pct
FROM appointments
GROUP BY appt_weekday
ORDER BY CASE appt_weekday WHEN 'Mon' THEN 1 WHEN 'Tue' THEN 2 WHEN 'Wed' THEN 3
                           WHEN 'Thu' THEN 4 WHEN 'Fri' THEN 5 ELSE 6 END;

-- name: 7. Neighbourhoods with the highest no-show rate (min 500 appointments)
SELECT
    neighbourhood,
    COUNT(*)                                   AS appointments,
    ROUND(100.0 * AVG(no_show), 1)             AS no_show_pct
FROM appointments
GROUP BY neighbourhood
HAVING COUNT(*) >= 500
ORDER BY no_show_pct DESC
LIMIT 10;

-- name: 8. Past behaviour predicts future behaviour
-- Returning patients, split by whether they missed any earlier appointment.
SELECT
    CASE WHEN prior_appts = 0      THEN '1. First appointment in window'
         WHEN prior_no_shows = 0   THEN '2. Returning, attended all before'
         ELSE                           '3. Returning, missed at least one before'
    END                                        AS history,
    COUNT(*)                                   AS appointments,
    ROUND(100.0 * AVG(no_show), 1)             AS no_show_pct
FROM appointments
GROUP BY history
ORDER BY history;

-- name: 9. Frequent no-show patients (window function: rank patients by missed visits)
WITH per_patient AS (
    SELECT patient_id,
           COUNT(*)      AS appts,
           SUM(no_show)  AS missed
    FROM appointments
    GROUP BY patient_id
    HAVING COUNT(*) >= 5
)
SELECT patient_id, appts, missed,
       ROUND(100.0 * missed / appts, 1)              AS miss_pct,
       RANK() OVER (ORDER BY missed DESC, appts)     AS rank_by_missed
FROM per_patient
ORDER BY rank_by_missed
LIMIT 10;

-- name: 10. Daily trend with a 7-day rolling no-show rate
WITH daily AS (
    SELECT appointment_date, COUNT(*) AS appts, SUM(no_show) AS missed
    FROM appointments
    GROUP BY appointment_date
)
SELECT appointment_date, appts, missed,
       ROUND(100.0 * SUM(missed) OVER w / SUM(appts) OVER w, 1) AS rolling_7d_pct
FROM daily
WINDOW w AS (ORDER BY appointment_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY appointment_date;
