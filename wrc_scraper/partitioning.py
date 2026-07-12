from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Partition:
    start: date #included lower bound
    end: date   #excluded upper bound

    @property
    def label(self) -> str:
        return self.start.isoformat()


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def generate_partitions(start_date: date, end_date: date, unit: str, size: int) -> list[Partition]:
    if start_date >= end_date:
        raise ValueError("start_date must be before end_date")
    
    if size <= 0:
        raise ValueError("partition size must be greater than zero")    

    partitions: list[Partition] = []
    cursor = start_date
    while cursor < end_date:
        if unit == "months":
            next_cursor = min(_add_months(cursor, size), end_date)
        elif unit == "days":
            next_cursor = min(cursor + timedelta(days=size), end_date)
        else:
            raise ValueError(f"Unsupported PARTITION_UNIT: {unit!r}")
        partitions.append(Partition(start=cursor, end=next_cursor))
        cursor = next_cursor
    return partitions
