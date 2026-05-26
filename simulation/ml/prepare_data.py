"""
Prepare the San Francisco solar/weather dataset for ML training.

Run from the simulation directory:

    python ml/prepare_data.py

The output is a 15-minute table for each dataset variant. The default
``prepared_training_data.csv`` remains the base variant for compatibility.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

SIM_DIR = Path(__file__).resolve().parents[1]
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

import config

DEFAULT_VARIANT = "base"
VARIANTS = ("base", "alt_1")
OUTPUT_DATA = "prepared_training_data.csv"
OUTPUT_SUMMARY = "data_summary.json"
TARGET_COLUMN = "capacity_factor"
TIMESTAMP_COLUMN = "timestamp"


def _input_path(key: str, variant: str = DEFAULT_VARIANT) -> Path:
    base_path = Path(config.ML_DATA_DIR) / config.ML_INPUT_FILES[key]
    if key == "weather" or variant == DEFAULT_VARIANT:
        return base_path
    return base_path.with_name(f"{base_path.stem}_1{base_path.suffix}")


def _parse_local_time(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%m/%d/%y %H:%M")


def _read_power_file(path: Path, column_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)
    df[TIMESTAMP_COLUMN] = _parse_local_time(df["LocalTime"])
    return (
        df[[TIMESTAMP_COLUMN, "Power(MW)"]]
        .rename(columns={"Power(MW)": column_name})
        .set_index(TIMESTAMP_COLUMN)
        .sort_index()
    )


def _read_actual_15m(variant: str) -> pd.DataFrame:
    actual = _read_power_file(_input_path("actual", variant), "actual_mw")
    actual_15m = actual.resample("15min").mean()
    actual_15m[TARGET_COLUMN] = (
        actual_15m["actual_mw"] / config.ML_SITE_CAPACITY_MW
    ).clip(0.0, 1.0)
    return actual_15m


def _read_forecast_15m(
    key: str,
    column_name: str,
    target_index: pd.DatetimeIndex,
    variant: str,
) -> pd.DataFrame:
    forecast = _read_power_file(_input_path(key, variant), column_name)
    return forecast.reindex(target_index, method="ffill")


def _read_weather_raw() -> pd.DataFrame:
    raw = pd.read_csv(_input_path("weather"), skiprows=2)
    raw[TIMESTAMP_COLUMN] = pd.to_datetime(
        {
            "year": raw["Year"],
            "month": raw["Month"],
            "day": raw["Day"],
            "hour": raw["Hour"],
            "minute": raw["Minute"],
        }
    ) + pd.Timedelta(hours=config.ML_WEATHER_TIME_SHIFT_HOURS)
    return raw


def _read_weather_15m(target_index: pd.DatetimeIndex) -> pd.DataFrame:
    raw = _read_weather_raw()
    weather = (
        raw[
            [
                TIMESTAMP_COLUMN,
                "Temperature",
                "Relative Humidity",
                "DHI",
                "DNI",
                "GHI",
                "Solar Zenith Angle",
                "Wind Speed",
                "Pressure",
                "Cloud Type",
                "Cloud Fill Flag",
                "Fill Flag",
            ]
        ]
        .rename(
            columns={
                "Temperature": "temperature_c",
                "Relative Humidity": "relative_humidity_pct",
                "DHI": "dhi",
                "DNI": "dni",
                "GHI": "ghi",
                "Solar Zenith Angle": "solar_zenith_angle",
                "Wind Speed": "wind_speed",
                "Pressure": "pressure",
                "Cloud Type": "cloud_type",
                "Cloud Fill Flag": "cloud_fill_flag",
                "Fill Flag": "fill_flag",
            }
        )
        .set_index(TIMESTAMP_COLUMN)
        .sort_index()
    )

    valid_index = target_index[
        (target_index >= weather.index.min()) & (target_index <= weather.index.max())
    ]

    numeric_cols = [
        "temperature_c",
        "relative_humidity_pct",
        "dhi",
        "dni",
        "ghi",
        "solar_zenith_angle",
        "wind_speed",
        "pressure",
    ]
    categorical_cols = ["cloud_type", "cloud_fill_flag", "fill_flag"]

    numeric_weather = weather[numeric_cols].reindex(valid_index)
    numeric_weather = numeric_weather.interpolate(method="time")

    categorical_weather = weather[categorical_cols].reindex(valid_index, method="ffill")
    return pd.concat([numeric_weather, categorical_weather], axis=1)


def _add_cloud_type_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    cloud_types = sorted(int(v) for v in result["cloud_type"].dropna().unique())
    for cloud_type in cloud_types:
        result[f"cloud_type_{cloud_type}"] = (
            result["cloud_type"].astype(int) == cloud_type
        ).astype(int)
    return result


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    hour_decimal = result.index.hour + result.index.minute / 60
    day_of_year = result.index.dayofyear

    result["hour_sin"] = [math.sin(2 * math.pi * h / 24) for h in hour_decimal]
    result["hour_cos"] = [math.cos(2 * math.pi * h / 24) for h in hour_decimal]
    result["day_sin"] = [math.sin(2 * math.pi * d / 365) for d in day_of_year]
    result["day_cos"] = [math.cos(2 * math.pi * d / 365) for d in day_of_year]
    return result


def _add_split_labels(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    month = result[TIMESTAMP_COLUMN].dt.month
    result["split"] = "test"
    result.loc[month <= 9, "split"] = "train"
    result.loc[month.isin([10, 11]), "split"] = "validation"
    return result


def _cloud_type_columns(df: pd.DataFrame) -> list[str]:
    return sorted(c for c in df.columns if c.startswith("cloud_type_"))


def _expanded_feature_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    cloud_type_cols = _cloud_type_columns(df)
    expanded: dict[str, list[str]] = {}
    for group_name, group_features in config.ML_FEATURE_GROUPS.items():
        features: list[str] = []
        for feature in group_features:
            if feature == "cloud_type":
                features.extend(cloud_type_cols)
            else:
                features.append(feature)
        expanded[group_name] = features
    return expanded


def _configured_features(df: pd.DataFrame) -> list[str]:
    features: list[str] = []
    for group_features in _expanded_feature_groups(df).values():
        for feature in group_features:
            if feature not in features:
                features.append(feature)
    return features


def cloud_type_columns(df: pd.DataFrame) -> list[str]:
    """Return the one-hot cloud-type columns generated for a prepared dataset."""
    return _cloud_type_columns(df)


def expanded_feature_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    """Return configured feature groups with categorical placeholders expanded."""
    return _expanded_feature_groups(df)


def feature_columns(
    df: pd.DataFrame,
    feature_group: str | None = None,
) -> list[str]:
    """Return model input columns for the requested feature group."""
    group_name = feature_group or getattr(config, "ML_ACTIVE_FEATURE_GROUP", "weather_time")
    groups = _expanded_feature_groups(df)
    if group_name not in groups:
        raise ValueError(f"Unknown ML feature group: {group_name}")
    return groups[group_name]


def build_weather_feature_lookup(
    variant: str = DEFAULT_VARIANT,
    feature_group: str | None = None,
) -> dict[tuple[int, int, int, int], dict]:
    """Build a 15-minute weather/feature lookup for simulator inference.

    Keys are ``(month, day, hour, minute)`` so simulation years can map onto the
    2006 source data while preserving the 15-minute tick structure.
    """
    df = build_dataset(variant)
    features = feature_columns(df, feature_group)
    lookup: dict[tuple[int, int, int, int], dict] = {}

    weather_cols = [
        "temperature_c",
        "relative_humidity_pct",
        "dhi",
        "dni",
        "ghi",
        "solar_zenith_angle",
        "wind_speed",
        "pressure",
        "cloud_type",
    ]
    selected_cols = list(dict.fromkeys([TIMESTAMP_COLUMN, *features, *weather_cols]))
    for row in df[selected_cols].to_dict("records"):
        ts = pd.Timestamp(row[TIMESTAMP_COLUMN])
        lookup[(ts.month, ts.day, ts.hour, ts.minute)] = {
            "timestamp": ts,
            "features": {col: float(row[col]) for col in features},
            "temperature_c": float(row["temperature_c"]),
            "relative_humidity_pct": float(row["relative_humidity_pct"]),
            "dhi": float(row["dhi"]),
            "dni": float(row["dni"]),
            "ghi": float(row["ghi"]),
            "solar_zenith_angle": float(row["solar_zenith_angle"]),
            "wind_speed": float(row["wind_speed"]),
            "pressure": float(row["pressure"]),
            "cloud_type": int(row["cloud_type"]),
        }

    return lookup


def _variant_input_files(variant: str) -> dict[str, str]:
    return {
        key: str(_input_path(key, variant).name)
        for key in ["actual", "day_ahead", "four_hour_ahead", "weather"]
    }


def build_dataset(variant: str = DEFAULT_VARIANT) -> pd.DataFrame:
    actual = _read_actual_15m(variant)
    weather = _read_weather_15m(actual.index)
    idx = actual.index.intersection(weather.index)
    merged = pd.concat(
        [
            actual.reindex(idx),
            _read_forecast_15m("day_ahead", "da_mw", idx, variant),
            _read_forecast_15m("four_hour_ahead", "ha4_mw", idx, variant),
            weather.reindex(idx),
        ],
        axis=1,
    )
    merged = merged.dropna()
    merged = _add_cloud_type_columns(merged)
    merged = _add_time_features(merged)
    merged.insert(0, TIMESTAMP_COLUMN, merged.index)
    return _add_split_labels(merged.reset_index(drop=True))


def build_congruence_metrics(df: pd.DataFrame) -> dict:
    zero_irradiance = df["ghi"] <= 1
    high_irradiance = df["ghi"] >= 500
    production_during_zero = zero_irradiance & (df["actual_mw"] > 0.1)
    zero_during_high = high_irradiance & (df["actual_mw"] <= 0.1)
    low_ghi_high_production = (df["ghi"] < 50) & (df["actual_mw"] > 5)
    large_actual_jump = df["actual_mw"].diff().abs() > 10

    return {
        "weather_time_shift_hours": config.ML_WEATHER_TIME_SHIFT_HOURS,
        "actual_ghi_correlation": float(df["actual_mw"].corr(df["ghi"])),
        "production_during_zero_irradiance_rows": int(production_during_zero.sum()),
        "zero_production_during_high_irradiance_rows": int(zero_during_high.sum()),
        "low_ghi_high_production_rows": int(low_ghi_high_production.sum()),
        "large_15min_actual_jump_rows": int(large_actual_jump.sum()),
        "max_15min_actual_jump_mw": float(df["actual_mw"].diff().abs().max()),
        "min_actual_mw": float(df["actual_mw"].min()),
        "max_actual_mw": float(df["actual_mw"].max()),
        "site_capacity_mw": config.ML_SITE_CAPACITY_MW,
        "within_site_capacity": bool(
            (df["actual_mw"].min() >= 0)
            and (df["actual_mw"].max() <= config.ML_SITE_CAPACITY_MW)
        ),
    }


def _forecast_metrics(df: pd.DataFrame) -> dict:
    metrics = {}
    for col in ["da_mw", "ha4_mw"]:
        error = (df[col] - df["actual_mw"]).abs()
        metrics[col] = {
            "mae_mw": float(error.mean()),
            "max_abs_error_mw": float(error.max()),
            "correlation_with_actual": float(df[col].corr(df["actual_mw"])),
        }
    return metrics


def _weather_flag_counts(df: pd.DataFrame) -> dict:
    return {
        "cloud_fill_flag": {
            str(k): int(v)
            for k, v in df["cloud_fill_flag"].value_counts().sort_index().items()
        },
        "fill_flag": {
            str(k): int(v)
            for k, v in df["fill_flag"].value_counts().sort_index().items()
        },
    }


def validate_dataset(df: pd.DataFrame, variant: str = DEFAULT_VARIANT) -> dict:
    features = _configured_features(df)
    missing_columns = [c for c in [TARGET_COLUMN, *features] if c not in df.columns]
    if missing_columns:
        raise ValueError(f"{variant}: missing required columns: {missing_columns}")

    if TARGET_COLUMN in features or "cloud_type" in features:
        raise ValueError(f"{variant}: target/raw cloud_type must not be input features")

    missing_counts = df[[TARGET_COLUMN, *features]].isna().sum()
    missing_counts = missing_counts[missing_counts > 0]
    if not missing_counts.empty:
        raise ValueError(f"{variant}: missing values found: {missing_counts.to_dict()}")

    intervals = df[TIMESTAMP_COLUMN].diff().dropna()
    expected = pd.Timedelta(minutes=config.MINUTES_PER_TICK)
    bad_intervals = intervals[intervals != expected]
    if not bad_intervals.empty:
        raise ValueError(
            f"{variant}: expected {config.MINUTES_PER_TICK}-minute rows; "
            f"found {len(bad_intervals)} irregular intervals"
        )

    congruence = build_congruence_metrics(df)
    if congruence["actual_ghi_correlation"] <= 0:
        raise ValueError(
            f"{variant}: actual production should have positive correlation with GHI; "
            f"got {congruence['actual_ghi_correlation']:.4f}"
        )

    if congruence["production_during_zero_irradiance_rows"]:
        raise ValueError(
            f"{variant}: found actual production during zero irradiance: "
            f"{congruence['production_during_zero_irradiance_rows']} rows"
        )

    if congruence["zero_production_during_high_irradiance_rows"]:
        raise ValueError(
            f"{variant}: found zero actual production during high irradiance: "
            f"{congruence['zero_production_during_high_irradiance_rows']} rows"
        )

    if not congruence["within_site_capacity"]:
        raise ValueError(
            f"{variant}: actual production is outside expected site capacity range: "
            f"{congruence['min_actual_mw']:.2f} to {congruence['max_actual_mw']:.2f} MW"
        )

    return congruence


def _numeric_stats(df: pd.DataFrame) -> dict:
    numeric_columns = [
        c for c in df.columns
        if c != TIMESTAMP_COLUMN and pd.api.types.is_numeric_dtype(df[c])
    ]
    stats = {}
    for col in numeric_columns:
        stats[col] = {
            "min": float(df[col].min()),
            "max": float(df[col].max()),
            "mean": float(df[col].mean()),
            "std": float(df[col].std()),
        }
    return stats


def _split_counts(df: pd.DataFrame) -> dict:
    return {
        str(k): int(v)
        for k, v in df["split"].value_counts().sort_index().items()
    }


def build_variant_summary(df: pd.DataFrame, variant: str, congruence: dict) -> dict:
    return {
        "rows": int(len(df)),
        "start": df[TIMESTAMP_COLUMN].min().isoformat(),
        "end": df[TIMESTAMP_COLUMN].max().isoformat(),
        "input_files": _variant_input_files(variant),
        "split_counts": _split_counts(df),
        "missing_values": {
            col: int(count)
            for col, count in df.isna().sum().items()
            if count
        },
        "congruence": congruence,
        "forecast_metrics": _forecast_metrics(df),
        "weather_flag_counts": _weather_flag_counts(df),
        "stats": _numeric_stats(df),
    }


def build_variant_comparison(datasets: dict[str, pd.DataFrame]) -> dict:
    if set(datasets) != {"base", "alt_1"}:
        return {}

    base = datasets["base"].set_index(TIMESTAMP_COLUMN)
    alt = datasets["alt_1"].set_index(TIMESTAMP_COLUMN)
    idx = base.index.intersection(alt.index)
    comparison = {"aligned_rows": int(len(idx))}

    for col in ["actual_mw", "capacity_factor", "da_mw", "ha4_mw"]:
        diff = (base.loc[idx, col] - alt.loc[idx, col]).abs()
        comparison[col] = {
            "differing_rows": int((diff > 1e-9).sum()),
            "mean_abs_difference": float(diff.mean()),
            "max_abs_difference": float(diff.max()),
            "rows_abs_difference_gt_1": int((diff > 1).sum()),
            "rows_abs_difference_gt_5": int((diff > 5).sum()),
        }

    return comparison


def build_summary(
    datasets: dict[str, pd.DataFrame],
    congruence_by_variant: dict[str, dict],
) -> dict:
    base_df = datasets[DEFAULT_VARIANT]
    return {
        "default_variant": DEFAULT_VARIANT,
        "tick_minutes": config.MINUTES_PER_TICK,
        "site_capacity_mw": config.ML_SITE_CAPACITY_MW,
        "weather_time_shift_hours": config.ML_WEATHER_TIME_SHIFT_HOURS,
        "target_column": TARGET_COLUMN,
        "raw_feature_groups": config.ML_FEATURE_GROUPS,
        "expanded_feature_groups": _expanded_feature_groups(base_df),
        "configured_features": _configured_features(base_df),
        "variant_note": (
            "Base and *_1 power files are prepared separately. They are not "
            "averaged because actual and HA4 values differ materially in some "
            "periods; model training should compare both variants."
        ),
        "variants": {
            variant: build_variant_summary(df, variant, congruence_by_variant[variant])
            for variant, df in datasets.items()
        },
        "variant_comparison": build_variant_comparison(datasets),
    }


def main() -> None:
    output_dir = Path(config.ML_ARTIFACTS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets: dict[str, pd.DataFrame] = {}
    congruence_by_variant: dict[str, dict] = {}
    for variant in VARIANTS:
        df = build_dataset(variant)
        congruence = validate_dataset(df, variant)
        datasets[variant] = df
        congruence_by_variant[variant] = congruence

    summary = build_summary(datasets, congruence_by_variant)

    default_path = output_dir / OUTPUT_DATA
    summary_path = output_dir / OUTPUT_SUMMARY
    datasets[DEFAULT_VARIANT].to_csv(default_path, index=False)
    for variant, df in datasets.items():
        df.to_csv(output_dir / f"prepared_training_data_{variant}.csv", index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("ML data preparation complete")
    for variant, df in datasets.items():
        target = df[TARGET_COLUMN]
        congruence = congruence_by_variant[variant]
        print(f"\nVariant:    {variant}")
        print(f"Rows:       {len(df):,}")
        print(f"Date range: {df[TIMESTAMP_COLUMN].min()} -> {df[TIMESTAMP_COLUMN].max()}")
        print(
            f"Target:     min={target.min():.4f} "
            f"max={target.max():.4f} mean={target.mean():.4f}"
        )
        print(f"GHI corr:   {congruence['actual_ghi_correlation']:.4f}")
        print(
            "Checks:     "
            f"zero-irradiance production={congruence['production_during_zero_irradiance_rows']}, "
            f"high-irradiance zero production={congruence['zero_production_during_high_irradiance_rows']}, "
            f"low-GHI/high-production={congruence['low_ghi_high_production_rows']}, "
            f"large jumps={congruence['large_15min_actual_jump_rows']}"
        )

    print(f"\nDefault:    {default_path}")
    for variant in datasets:
        print(f"{variant}:       {output_dir / f'prepared_training_data_{variant}.csv'}")
    print(f"Summary:    {summary_path}")


if __name__ == "__main__":
    main()
