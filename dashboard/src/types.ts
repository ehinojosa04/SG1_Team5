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

export interface Dataset {
  manifest: Manifest | null;
  households: Household[];
  system: SystemTick[];
  daily: DailyHouseholdRow[];
  hourlyNeigh: HourlyNeighborhoodRow[];
  hourlySeg: HourlySegmentRow[];
  segment: SegmentRow[];
  adoption: AdoptionRow[];
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
