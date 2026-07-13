import subprocess
import sys
from datetime import datetime
from pathlib import Path

import dagster as dg
from pydantic import field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DateRangeResource(dg.ConfigurableResource):
    start_date: str
    end_date: str

    @field_validator("start_date", "end_date")
    @classmethod
    def _validate_format(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Expected YYYY-MM-DD, got {value!r}") from None
        return value

    @model_validator(mode="after")
    def _validate_order(self) -> "DateRangeResource":
        if self.start_date >= self.end_date:
            raise ValueError(f"start_date ({self.start_date}) must be before end_date ({self.end_date})")
        return self


class BodiesConfig(dg.Config):
    bodies: str = ""


def _run_subprocess(context: dg.OpExecutionContext, args: list[str], label: str) -> None:
    context.log.info(f"{label} starting: {' '.join(args)}")
    result = subprocess.run(args, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise dg.Failure(f"{label} failed with exit code {result.returncode}")
    context.log.info(f"{label} completed successfully")


@dg.op
def scrape_op(context: dg.OpExecutionContext, config: BodiesConfig, date_range: DateRangeResource) -> None:
    args = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "workplace_relations",
        "-a",
        f"start_date={date_range.start_date}",
        "-a",
        f"end_date={date_range.end_date}",
    ]
    if config.bodies:
        args += ["-a", f"bodies={config.bodies}"]
    _run_subprocess(context, args, "scrape")


@dg.op(ins={"start_after": dg.In(dg.Nothing)})
def transform_op(context: dg.OpExecutionContext, date_range: DateRangeResource) -> None:
    args = [
        sys.executable,
        "-m",
        "transform.transform",
        "--start-date",
        date_range.start_date,
        "--end-date",
        date_range.end_date,
    ]
    _run_subprocess(context, args, "transform")


@dg.job
def scrape_and_transform_job():
    transform_op(start_after=scrape_op())


defs = dg.Definitions(
    jobs=[scrape_and_transform_job],
    resources={"date_range": DateRangeResource.configure_at_launch()},
)
