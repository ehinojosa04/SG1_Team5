import { csv, json, autoType } from "d3";
import type {
  AdoptionRow,
  DailyHouseholdRow,
  Dataset,
  Household,
  HourlyNeighborhoodRow,
  HourlySegmentRow,
  MLDataSummary,
  MLDataset,
  MLModelCoefficients,
  MLPreparedRow,
  Manifest,
  SegmentRow,
  SystemTick,
} from "../types";

const toBool = (v: unknown): boolean => {
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return v !== 0;
  const s = String(v ?? "").trim().toLowerCase();
  return s === "true" || s === "1" || s === "yes";
};

const toDate = (v: unknown): Date => new Date(String(v).replace(" ", "T"));
const toStrategy = (d: Record<string, string>): string =>
  d.strategy || d.charge_priority || "UNKNOWN";

const parseMlRow = (d: Record<string, string>): MLPreparedRow => {
  const row: MLPreparedRow = {
    timestamp: toDate(d.timestamp),
    actual_mw: +d.actual_mw,
    capacity_factor: +d.capacity_factor,
    da_mw: +d.da_mw,
    ha4_mw: +d.ha4_mw,
    temperature_c: +d.temperature_c,
    relative_humidity_pct: +d.relative_humidity_pct,
    dhi: +d.dhi,
    dni: +d.dni,
    ghi: +d.ghi,
    solar_zenith_angle: +d.solar_zenith_angle,
    wind_speed: +d.wind_speed,
    pressure: +d.pressure,
    cloud_type: +d.cloud_type,
    cloud_fill_flag: +d.cloud_fill_flag,
    fill_flag: +d.fill_flag,
    split: d.split as MLPreparedRow["split"],
  };
  Object.keys(d)
    .filter((key) => key.startsWith("cloud_type_"))
    .forEach((key) => {
      row[key] = +d[key];
    });
  return row;
};

async function loadMlDataset(): Promise<MLDataset | null> {
  try {
    const [summary, base, alt1, model] = await Promise.all([
      json<MLDataSummary>("/ml-data/data_summary.json"),
      csv<MLPreparedRow>("/ml-data/prepared_training_data_base.csv", parseMlRow),
      csv<MLPreparedRow>("/ml-data/prepared_training_data_alt_1.csv", parseMlRow),
      json<MLModelCoefficients>("/ml-model/model_coefficients.json").catch(() => null),
    ]);
    if (!summary) return null;
    return { summary, base, alt1, model: model ?? null };
  } catch {
    return null;
  }
}

export async function loadDataset(): Promise<Dataset> {
  const [
    manifest,
    households,
    system,
    daily,
    hourlyNeigh,
    hourlySeg,
    segment,
    adoption,
    mlData,
  ] = await Promise.all([
    json<Manifest>("/data/manifest.json").catch(() => null),
    csv<Household>("/data/households.csv", (d: Record<string, string>) => ({
      house_id: +d.house_id,
      type: d.type as Household["type"],
      wealth: d.wealth as Household["wealth"],
      strategy: toStrategy(d),
      has_solar: toBool(d.has_solar),
      has_battery: toBool(d.has_battery),
      pv_kwp: +d.pv_kwp,
      batt_kwh: +d.batt_kwh,
    })),
    csv<SystemTick>("/data/system.csv", (d: Record<string, string>) => ({
      timestamp: toDate(d.timestamp),
      total_load_kWh: +d.total_load_kWh,
      total_generation_kWh: +d.total_generation_kWh,
      total_self_consumption_kWh: +d.total_self_consumption_kWh,
      net_load_kWh: +d.net_load_kWh,
      total_imports_kWh: +d.total_imports_kWh,
      total_exports_kWh: +d.total_exports_kWh,
      tick_savings: +d.tick_savings,
      cloud_coverage: +d.cloud_coverage,
      hour: +d.hour,
      date: d.date,
    })),
    csv<DailyHouseholdRow>(
      "/data/daily_by_household.csv",
      (d: Record<string, string>) => ({
        date: toDate(d.date),
        house_id: +d.house_id,
        type: d.type as DailyHouseholdRow["type"],
        wealth: d.wealth as DailyHouseholdRow["wealth"],
        strategy: toStrategy(d),
        has_solar: toBool(d.has_solar),
        has_battery: toBool(d.has_battery),
        generation_kWh: +d.generation_kWh,
        load_kWh: +d.load_kWh,
        self_consumption_kWh: +d.self_consumption_kWh,
        grid_imports_kWh: +d.grid_imports_kWh,
        grid_exports_kWh: +d.grid_exports_kWh,
        cost: +d.cost,
        savings: +d.savings,
        avg_soc: +d.avg_soc,
      }),
    ),
    csv<HourlyNeighborhoodRow>("/data/hourly_neighborhood.csv", autoType) as Promise<
      HourlyNeighborhoodRow[]
    >,
    csv<HourlySegmentRow>("/data/hourly_by_segment.csv", autoType) as Promise<
      HourlySegmentRow[]
    >,
    csv<SegmentRow>("/data/segment_summary.csv", autoType) as Promise<SegmentRow[]>,
    csv<AdoptionRow>("/data/adoption.csv", autoType) as Promise<AdoptionRow[]>,
    loadMlDataset(),
  ]);

  return {
    manifest: manifest ?? null,
    households,
    system,
    daily,
    hourlyNeigh,
    hourlySeg,
    segment,
    adoption,
    mlData,
  };
}
