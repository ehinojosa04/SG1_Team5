import { csv, json, autoType } from "d3";
import type {
  AdoptionRow,
  DailyHouseholdRow,
  Dataset,
  Household,
  HourlyNeighborhoodRow,
  HourlySegmentRow,
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
  ] = await Promise.all([
    json<Manifest>("/data/manifest.json").catch(() => null),
    csv<Household>("/data/households.csv", (d: Record<string, string>) => ({
      house_id: +d.house_id,
      type: d.type as Household["type"],
      wealth: d.wealth as Household["wealth"],
      strategy: d.strategy,
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
        strategy: d.strategy,
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
  };
}
