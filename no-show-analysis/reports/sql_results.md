# SQL results

Generated from `sql/analysis.sql` (10 queries).

## 1. Overall summary

|   appointments |   patients |   no_shows |   no_show_pct | first_appt   | last_appt   |
|---------------:|-----------:|-----------:|--------------:|:-------------|:------------|
|         110521 |      62298 |      22314 |          20.2 | 2016-04-29   | 2016-06-08  |

## 2. No-show rate by lead time (days between booking and visit)

| lead_bucket   |   appointments |   no_show_pct |
|:--------------|---------------:|--------------:|
| Same day      |          38562 |           4.6 |
| 1-2 days      |          11938 |          22.7 |
| 3-7 days      |          20247 |          25   |
| 8-14 days     |          12025 |          30.5 |
| 15-30 days    |          17371 |          32.6 |
| 31-60 days    |           8283 |          34.2 |
| 60+ days      |           2095 |          28.4 |

## 3. SMS reminders look harmful... until you control for lead time

| lead_bucket   |   no_sms_pct |   sms_pct |   sms_appts |   no_sms_appts |
|:--------------|-------------:|----------:|------------:|---------------:|
| Same day      |          4.6 |     nan   |           0 |          38562 |
| 1-2 days      |         22.7 |     nan   |           0 |          11938 |
| 3-7 days      |         26.6 |      23.8 |       11548 |           8699 |
| 8-14 days     |         33.8 |      28.1 |        7004 |           5021 |
| 15-30 days    |         36.9 |      29.8 |       10520 |           6851 |
| 31-60 days    |         38.4 |      31.5 |        5059 |           3224 |
| 60+ days      |         33.9 |      25.5 |        1351 |            744 |

## 4. No-show rate by age group

| age_group   |   appointments |   no_show_pct |
|:------------|---------------:|--------------:|
| 0-12        |          21035 |          20.5 |
| 13-17       |           6343 |          26.6 |
| 18-29       |          16729 |          24.6 |
| 30-44       |          22021 |          21.8 |
| 45-59       |          23221 |          17.9 |
| 60-74       |          15237 |          15   |
| 75+         |           5935 |          16   |

## 5. Chronic conditions and welfare enrolment

| factor                  |   has_factor |   appointments |   no_show_pct |
|:------------------------|-------------:|---------------:|--------------:|
| Hypertension            |            0 |          88720 |          20.9 |
| Hypertension            |            1 |          21801 |          17.3 |
| Diabetes                |            0 |         102578 |          20.4 |
| Diabetes                |            1 |           7943 |          18   |
| Alcoholism              |            0 |         107161 |          20.2 |
| Alcoholism              |            1 |           3360 |          20.1 |
| Handicap                |            0 |         108282 |          20.2 |
| Handicap                |            1 |           2239 |          18.1 |
| Welfare (Bolsa Familia) |            0 |          99660 |          19.8 |
| Welfare (Bolsa Familia) |            1 |          10861 |          23.7 |

## 6. Day of week

| appt_weekday   |   appointments |   no_show_pct |
|:---------------|---------------:|--------------:|
| Mon            |          22713 |          20.6 |
| Tue            |          25638 |          20.1 |
| Wed            |          25866 |          19.7 |
| Thu            |          17246 |          19.3 |
| Fri            |          19019 |          21.2 |
| Sat            |             39 |          23.1 |

## 7. Neighbourhoods with the highest no-show rate (min 500 appointments)

| neighbourhood     |   appointments |   no_show_pct |
|:------------------|---------------:|--------------:|
| Santos Dumont     |           1276 |          28.9 |
| Santa Clara       |            506 |          26.5 |
| Itararé           |           3514 |          26.3 |
| Jesus De Nazareth |           2853 |          24.4 |
| Ilha Do Príncipe  |           2266 |          23.5 |
| Caratoíra         |           2565 |          23   |
| Andorinhas        |           2262 |          23   |
| Praia Do Suá      |           1288 |          22.8 |
| Gurigica          |           2018 |          22.6 |
| Bento Ferreira    |            858 |          22.5 |

## 8. Past behaviour predicts future behaviour

| history                                  |   appointments |   no_show_pct |
|:-----------------------------------------|---------------:|--------------:|
| 1. First appointment in window           |          66288 |          19.4 |
| 2. Returning, attended all before        |          30119 |          18.8 |
| 3. Returning, missed at least one before |          14114 |          26.9 |

## 9. Frequent no-show patients (window function: rank patients by missed visits)

|      patient_id |   appts |   missed |   miss_pct |   rank_by_missed |
|----------------:|--------:|---------:|-----------:|-----------------:|
|   1421986987763 |      18 |       18 |      100   |                1 |
| 563513528548171 |      16 |       16 |      100   |                2 |
|   5587789811398 |      20 |       15 |       75   |                3 |
| 581197334462339 |      14 |       14 |      100   |                4 |
|  65751443779385 |      13 |       13 |      100   |                5 |
|   1198157171975 |      23 |       12 |       52.2 |                6 |
|    476861615941 |      12 |       11 |       91.7 |                7 |
|   2728422248149 |      15 |       11 |       73.3 |                8 |
| 249163747571517 |      18 |       11 |       61.1 |                9 |
|   9715135545613 |      20 |       11 |       55   |               10 |

## 10. Daily trend with a 7-day rolling no-show rate

| appointment_date   |   appts |   missed |   rolling_7d_pct |
|:-------------------|--------:|---------:|-----------------:|
| 2016-04-29         |    3235 |      633 |             19.6 |
| 2016-05-02         |    4376 |      861 |             19.6 |
| 2016-05-03         |    4255 |      830 |             19.6 |
| 2016-05-04         |    4167 |      972 |             20.6 |
| 2016-05-05         |    4272 |      806 |             20.2 |
| 2016-05-06         |    3879 |      795 |             20.2 |
| 2016-05-09         |    4519 |     1018 |             20.6 |
| 2016-05-10         |    4308 |      992 |             21.1 |
| 2016-05-11         |    4474 |      885 |             21.1 |
| 2016-05-12         |    4394 |      837 |             21   |
| 2016-05-13         |    3987 |      905 |             20.9 |
| 2016-05-14         |      39 |        9 |             21.3 |
| 2016-05-16         |    4613 |     1049 |             21.6 |
| 2016-05-17         |    4371 |      934 |             21.4 |
| 2016-05-18         |    4373 |      890 |             21   |
| 2016-05-19         |    4270 |      892 |             21.2 |
| 2016-05-20         |    3828 |      899 |             21.9 |
| 2016-05-24         |    4009 |      811 |             21.5 |
| 2016-05-25         |    3909 |      759 |             21.2 |
| 2016-05-30         |    4514 |      888 |             20.7 |
| 2016-05-31         |    4279 |      767 |             20.2 |
| 2016-06-01         |    4464 |      812 |             19.9 |
| 2016-06-02         |    4310 |      802 |             19.6 |
| 2016-06-03         |    4090 |      805 |             19.1 |
| 2016-06-06         |    4691 |      873 |             18.9 |
| 2016-06-07         |    4416 |      816 |             18.7 |
| 2016-06-08         |    4479 |      774 |             18.4 |
