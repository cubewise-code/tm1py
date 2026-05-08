try:
    import pandas as pd
    _has_pandas = True
except ImportError:
    _has_pandas = False

from datetime import datetime

from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils.Utils import format_url, require_pandas, require_version, datetime_to_iso


class MetricService(ObjectService):
    """Service to handle TM1 cube metrics in v12"""

    def __init__(self, rest: RestService):
        super().__init__(rest)

    @require_version(version="12.0.0")
    def get(
            self,
            cube_name: str = None,
            metrics: list[str] = None,
            timestamp: datetime = None,
            **kwargs):

        filters = []

        if cube_name:
            filters.append(f"CubeName eq '{cube_name}'")

        if metrics:
            metric_filter = " or ".join(
                [f"Name eq '{m}'" for m in metrics]
            )
            filters.append(f"({metric_filter})")

        if timestamp:
            filters.append(
                f"Timestamp gt {datetime_to_iso(timestamp)}"
            )

        filter_part = ""

        if filters:
            filter_string = " and ".join(f"({f})" for f in filters)
            filter_part = f"?$filter={filter_string}"

        url = format_url(f"/Metrics(){filter_part}")
        response = self._rest.GET(url, **kwargs)

        return response.json().get("value", [])

    @require_pandas
    @require_version(version="12.0.0")
    def get_as_dataframe(
            self,
            cube_name: str = None,
            metrics: list[str] = None,
            timestamp: datetime = None,
            **kwargs):

        data = self.get(
            cube_name=cube_name,
            metrics=metrics,
            timestamp=timestamp,
            **kwargs
        )

        return pd.DataFrame.from_records(data)