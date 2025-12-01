from __future__ import annotations

from typing import (
    Protocol,
    runtime_checkable,
    Iterable,
    List,
    Any,
    TYPE_CHECKING,
)

import numpy as np

from TM1py.Utils.Utils import (
    CaseAndSpaceInsensitiveTuplesDict
)

# Only import pandas/polars for type hints (not at runtime)
if TYPE_CHECKING:
    import pandas as pd
    import polars as pl


def _require_pandas():
    try:
        import pandas as pd
        return pd
    except ImportError:
        raise ImportError("Pandas is required but not installed.")


def _require_polars():
    try:
        import polars as pl
        return pl
    except ImportError:
        raise ImportError("Polars is required but not installed.")


@runtime_checkable
class DataFrameLike(Protocol):
    """
    A backend-agnostic interface for DataFrame-like objects
    (pandas, polars, or others).
    """

    @property
    def columns(self) -> Iterable[str]:
        ...

    @columns.setter
    def columns(self, new_columns: Iterable[str]) -> None:
        ...

    def iter_rows(self, columns: Iterable[str] = None) -> Iterable[tuple]:
        ...

    def reset_index(self) -> DataFrameLike:
        ...

    def is_numeric_column(self, col: str) -> bool:
        ...

    def filter_rows(self, mask: Iterable[bool]) -> DataFrameLike:
        ...

    def concat(self, others: List[DataFrameLike]) -> DataFrameLike:
        ...

    def get_column_values(self, col: str) -> Iterable[Any]:
        ...

    def copy(self) -> "DataFrameLike":
        ...

    def aggregate_duplicate_intersections(
        self,
        dimension_headers: Iterable[str],
        value_header: str
    ) -> DataFrameLike:
        ...

    def __getitem__(self, key) -> DataFrameLike:
        ...

    def __setitem__(self, key, value) -> DataFrameLike:
        ...


class PandasFrame:
    def __init__(self, df: "pd.DataFrame"):
        self._pd = _require_pandas()
        self.df = df

    @property
    def columns(self):
        return self.df.columns

    @columns.setter
    def columns(self, new_columns):
        self.df.columns = new_columns

    def copy(self) -> "PandasFrame":
        return PandasFrame(self.df.copy(deep=True))

    def iter_rows(self, columns: Iterable[str] = None):
        if columns is None:
            return self.df.itertuples(index=False, name=None)
        return self.df[list(columns)].itertuples(index=False, name=None)

    def reset_index(self) -> "PandasFrame":
        if isinstance(self.df.index, self._pd.MultiIndex):
            return PandasFrame(self.df.reset_index())
        return self

    def is_numeric_column(self, col: str) -> bool:
        return self._pd.api.types.is_numeric_dtype(self.df[col])

    def filter_rows(self, mask):
        return PandasFrame(self.df[mask])

    def concat(self, others):
        dfs = [self.df] + [o.df for o in others]
        return PandasFrame(self._pd.concat(dfs, ignore_index=True))

    def get_column_values(self, col: str):
        return self.df[col].values

    def aggregate_duplicate_intersections(
            self,
            dimension_headers: Iterable[str],
            value_header: str
    ) -> "PandasFrame":
        df = self.df

        for col in dimension_headers:
            df[col] = df[col].astype(str).str.lower().str.replace(" ", "")

        if self.is_numeric_column(value_header):
            grouped = (
                df.groupby([*dimension_headers])[value_header].sum().reset_index()
            )
            return PandasFrame(grouped)

        filter_mask = df[value_header].apply(np.isreal)

        df_n = df[filter_mask]
        df_s = df[~filter_mask]

        if not df_n.empty:
            df_n = (
                df_n.groupby([*dimension_headers])[value_header].sum().reset_index()
            )

        combined = self._pd.concat([df_n, df_s], ignore_index=True)

        return PandasFrame(combined)

    def __getitem__(self, key):

        if isinstance(key, list):
            # DataFrame result -> wrap again
            return PandasFrame(self.df[key])

        if isinstance(key, str):
            # Single column -> Series
            return self.df[key]

        raise TypeError(f"Unsupported key type: {type(key)}")

    def __setitem__(self, key, value):

        if not isinstance(key, str):
            raise TypeError("Column name must be a string")

        self.df[key] = value

class PolarsFrame:
    def __init__(self, df: "pl.DataFrame"):
        self._pl = _require_polars()
        self.df = df

    @property
    def columns(self):
        return self.df.columns

    @columns.setter
    def columns(self, new_columns):
        # rename all columns at once
        if len(new_columns) != len(self.df.columns):
            raise ValueError("Number of new columns must match existing columns")
        self.df = self.df.rename(dict(zip(self.df.columns, new_columns)))

    def iter_rows(self, columns: Iterable[str] = None):
        df_to_iter = self.df.select(list(columns)) if columns else self.df
        return df_to_iter.iter_rows()

    def reset_index(self) -> "PolarsFrame":
        return self

    def is_numeric_column(self, col: str) -> bool:
        pl = self._pl
        return self.df[col].dtype in (
            pl.Int8, pl.Int16, pl.Int32, pl.Int64,
            pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
            pl.Float32, pl.Float64,
        )

    def filter_rows(self, mask):
        mask_series = self._pl.pl.Series("mask", mask)
        return PolarsFrame(self.df.filter(mask_series))

    def concat(self, others):
        dfs = [self.df] + [o.df for o in others]
        return PolarsFrame(self._pl.concat(dfs))

    def get_column_values(self, col: str):
        return self.df[col].to_list()

    def aggregate_duplicate_intersections(
        self,
        dimension_headers: Iterable[str],
        value_header: str
    ) -> "PolarsFrame":
        pl = self._pl
        df = self.df

        for col in dimension_headers:
            df = df.with_columns(
                pl.col(col).cast(pl.Utf8).str.to_lowercase().str.replace(" ", "").alias(col)
            )

        is_numeric = self.is_numeric_column(value_header)

        if is_numeric:
            grouped = ((df.group_by(list(dimension_headers))
                       .agg(pl.col(value_header).sum().alias(value_header)))
                       .select([*dimension_headers, value_header])
                       )
            return PolarsFrame(grouped)

        casted = df.with_columns(pl.col(value_header).cast(pl.Float64, strict=False).alias("__value_float__"))
        numeric_mask = pl.col("__value_float__").is_not_null()

        df_n = casted.filter(numeric_mask).select([*dimension_headers, "__value_float__"])
        if df_n.height > 0:
            df_n = df_n.rename({"__value_float__": value_header})
            df_n = ((df_n.group_by(list(dimension_headers))
                       .agg(pl.col(value_header).sum().alias(value_header)))
                       .select([*dimension_headers, value_header])
                       )

        df_s = casted.filter(~numeric_mask).select([*dimension_headers, value_header])

        if df_n.height > 0 and df_s.height > 0:
            df = pl.concat([df_n, df_s], how="vertical")
        elif df_n.height > 0:
            df = df_n
        else:
            df = df_s

        return PolarsFrame(df)

    def __getitem__(self, key):

        if isinstance(key, list):
            return PolarsFrame(self.df.select(key))

        if isinstance(key, str):
            return self.df[key]

        raise TypeError(f"Unsupported key type: {type(key)}")

    def __setitem__(self, key, value):
        """
        Assign scalar value (str, int, float, bool) to a column:
        data[key] = value
        """
        if not isinstance(key, str):
            raise TypeError("Column name must be a string")

        # Allow string or numeric types
        if not isinstance(value, (str, int, float, bool)):
            raise TypeError("Only scalar string or numeric values are supported")

        self.df = self.df.with_columns(self._pl.lit(value).alias(key))


def convert_to_dataframe_like(df: Any) -> DataFrameLike:

    try:
        import pandas as pd
        if isinstance(df, pd.DataFrame):
            return PandasFrame(df)
    except ImportError:
        pass

    try:
        import polars as pl
        if isinstance(df, pl.DataFrame):
            return PolarsFrame(df)
    except ImportError:
        pass

    raise TypeError(f"Unsupported dataframe type: {type(df)}")


def build_cellset_from_dataframe(
    df: "DataFrameLike",
    sum_numeric_duplicates: bool = True
) -> "CaseAndSpaceInsensitiveTuplesDict":

    # Reset index if backend supports it (noop for polars)
    df = df.reset_index()

    # Identify value and dimension columns
    columns = list(df.columns)
    value_header = columns[-1]
    dimension_headers = columns[:-1]

    # Aggregate duplicates if requested
    if sum_numeric_duplicates:
        df = df.aggregate_duplicate_intersections(dimension_headers, value_header)

    keys = df.iter_rows(columns=dimension_headers)
    values = df.get_column_values(value_header)
    cellset = CaseAndSpaceInsensitiveTuplesDict(dict(zip(keys, values)))

    return cellset