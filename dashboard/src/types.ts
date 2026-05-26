export type WealthLevel = "LOW" | "MIDDLE" | "HIGH" | "LUXURY";
export type HouseType = "STUDIO" | "SMALL" | "LARGE";
export type Strategy = string;

export const WEALTH_ORDER: WealthLevel[] = ["LOW", "MIDDLE", "HIGH", "LUXURY"];
export const TYPE_ORDER: HouseType[] = ["STUDIO", "SMALL", "LARGE"];

export const WEALTH_COLORS: Record<WealthLevel, string> = {
  LOW: "#6366f1",
  MIDDLE: "#10b981",
  HIGH: "#f59e0b",
  LUXURY: "#ef4444",
};

export const TYPE_COLORS: Record<HouseType, string> = {
  STUDIO: "#60a5fa",
  SMALL: "#34d399",
  LARGE: "#f472b6",
};

export interface Manifest {
  scenario: string;
  generated_at: string;
  tick_minutes: number;
  import_cost: number;
  export_cost: number;
  n_households: number;
  n_ticks: number;
  start: string;
  end: string;
  files: string[];
}

export interface Household {
  house_id: number;
  type: HouseType;
  wealth: WealthLevel;
  strategy: Strategy;
  has_solar: boolean;
  has_battery: boolean;
  pv_kwp: number;
  batt_kwh: number;
}

export interface SystemTick {
  timestamp: Date;
  total_load_kWh: number;
  total_generation_kWh: number;
  total_self_consumption_kWh: number;
  net_load_kWh: number;
  total_imports_kWh: number;
  total_exports_kWh: number;
  tick_savings: number;
  cloud_coverage: number;
  hour: number;
  date: string;
}

export interface DailyHouseholdRow {
  date: Date;
  house_id: number;
  type: HouseType;
  wealth: WealthLevel;
  strategy: Strategy;
  has_solar: boolean;
  has_battery: boolean;
  generation_kWh: number;
  load_kWh: number;
  self_consumption_kWh: number;
  grid_imports_kWh: number;
  grid_exports_kWh: number;
  cost: number;
  savings: number;
  avg_soc: number;
}

export interface HourlyNeighborhoodRow {
  hour: number;
  mean_gen_kWh: number;
  mean_load_kWh: number;
  mean_imports_kWh: number;
  mean_exports_kWh: number;
  mean_soc: number;
  mean_net_load_kWh: number;
}

export interface HourlySegmentRow extends HourlyNeighborhoodRow {
  type: HouseType;
  wealth: WealthLevel;
}

export interface SegmentRow {
  type: HouseType;
  wealth: WealthLevel;
  houses: number;
  generation_kWh: number;
  load_kWh: number;
  self_consumption_kWh: number;
  imports_kWh: number;
  exports_kWh: number;
  cost: number;
  savings: number;
  net_balance: number;
  self_consumption_pct: number;
}

export interface AdoptionRow {
  type: HouseType;
  wealth: WealthLevel;
  houses: number;
  solar_homes: number;
  battery_homes: number;
  solar_adoption_pct: number;
  battery_adoption_pct: number;
}

export interface MLPreparedRow {
  [key: string]: Date | number | string;
  timestamp: Date;
  actual_mw: number;
  capacity_factor: number;
  da_mw: number;
  ha4_mw: number;
  temperature_c: number;
  relative_humidity_pct: number;
  dhi: number;
  dni: number;
  ghi: number;
  solar_zenith_angle: number;
  wind_speed: number;
  pressure: number;
  cloud_type: number;
  cloud_fill_flag: number;
  fill_flag: number;
  split: "train" | "validation" | "test";
}

export interface MLModelMetrics {
  mse: number;
  mae: number;
  rmse: number;
  r2: number;
}

export interface MLFeatureGroupComparison {
  features: string[];
  feature_count: number;
  metrics: Record<"train" | "validation" | "test", MLModelMetrics>;
}

export interface MLModelCoefficients {
  model_type: string;
  target: "capacity_factor";
  feature_group: string;
  features: string[];
  weights: number[];
  bias: number;
  feature_means: Record<string, number>;
  feature_stds: Record<string, number>;
  metrics: Record<"train" | "validation" | "test", MLModelMetrics>;
  feature_group_comparison?: Record<string, MLFeatureGroupComparison>;
}

export interface MLVariantSummary {
  rows: number;
  start: string;
  end: string;
  split_counts: Record<string, number>;
  congruence: {
    actual_ghi_correlation: number;
    low_ghi_high_production_rows: number;
    large_15min_actual_jump_rows: number;
    production_during_zero_irradiance_rows: number;
    zero_production_during_high_irradiance_rows: number;
  };
  forecast_metrics: Record<
    "da_mw" | "ha4_mw",
    {
      mae_mw: number;
      max_abs_error_mw: number;
      correlation_with_actual: number;
    }
  >;
  weather_flag_counts: Record<string, Record<string, number>>;
  stats: Record<string, { min: number; max: number; mean: number; std: number }>;
}

export interface MLVariantComparisonMetric {
  differing_rows: number;
  mean_abs_difference: number;
  max_abs_difference: number;
  rows_abs_difference_gt_1: number;
  rows_abs_difference_gt_5: number;
}

export interface MLVariantComparison {
  aligned_rows: number;
  actual_mw: MLVariantComparisonMetric;
  capacity_factor: MLVariantComparisonMetric;
  da_mw: MLVariantComparisonMetric;
  ha4_mw: MLVariantComparisonMetric;
}

export interface MLDataSummary {
  default_variant: string;
  weather_time_shift_hours: number;
  expanded_feature_groups: Record<string, string[]>;
  configured_features: string[];
  variants: Record<"base" | "alt_1", MLVariantSummary>;
  variant_comparison: MLVariantComparison;
}

export interface MLDataset {
  summary: MLDataSummary;
  base: MLPreparedRow[];
  alt1: MLPreparedRow[];
  model: MLModelCoefficients | null;
}

export interface Dataset {
  manifest: Manifest | null;
  households: Household[];
  system: SystemTick[];
  daily: DailyHouseholdRow[];
  hourlyNeigh: HourlyNeighborhoodRow[];
  hourlySeg: HourlySegmentRow[];
  segment: SegmentRow[];
  adoption: AdoptionRow[];
  mlData: MLDataset | null;
}

export interface Filters {
  types: HouseType[];
  wealths: WealthLevel[];
  strategies: Strategy[];
  solar: "all" | "solar" | "non-solar";
  battery: "all" | "battery" | "non-battery";
  start: Date;
  end: Date;
  granularity: Granularity;
}

export type Granularity = "hour" | "day" | "week" | "month";
