-- MetricFlow's day-grain time spine, covering the study window and its control year.
select cast(range as date) as date_day
from range(date '2025-01-01', date '2027-12-31', interval 1 day)
