import { useMemo } from "react";
import * as d3 from "d3";
import LineChart, { type LineSeries } from "../components/charts/LineChart";
import BarChart from "../components/charts/BarChart";
import type { DailyHouseholdRow, Dataset, Filters } from "../types";
import { WEALTH_COLORS, WEALTH_ORDER } from "../types";
import { fmt } from "../components/charts/useChart";

interface Props {
  dataset: Dataset;
  filters: Filters;
  fd: DailyHouseholdRow[];
}

export default function BatteryGrid({ dataset, filters }: Props) {
  const socByHour = useMemo<LineSeries[]>(() => {
    const seg = dataset.hourlySeg.filter((r) => filters.types.includes(r.type));
    const byWealth = d3.rollups(
      seg,
      (rs) => rs,
      (r) => r.wealth,
    );
    return WEALTH_ORDER.filter((w) => byWealth.some(([wk]) => wk === w)).map((w) => {
      const rs = byWealth.find(([wk]) => wk === w)?.[1] ?? [];
      const grouped = d3.rollups(
        rs,
        (r) => d3.mean(r, (x) => x.mean_soc) ?? 0,
        (r) => r.hour,
      ).sort((a, b) => a[0] - b[0]);
      return {
        name: w,
        color: WEALTH_COLORS[w],
        values: grouped.map(([x, y]) => ({ x, y })),
      };
    });
  }, [dataset, filters]);

  const hnByHour = dataset.hourlyNeigh;

  const peakLoadH = useMemo(
    () => hnByHour.reduce((a, b) => (a.mean_load_kWh > b.mean_load_kWh ? a : b)).hour,
    [hnByHour],
  );
  const peakGenH = useMemo(
    () => hnByHour.reduce((a, b) => (a.mean_gen_kWh > b.mean_gen_kWh ? a : b)).hour,
    [hnByHour],
  );

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Average battery SoC by hour of day</div>
          {socByHour.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--color-ink-dim)" }}>
              No battery data in the current selection.
            </div>
          ) : (
            <LineChart
              series={socByHour}
              height={360}
              xLabel="Hour of day"
              yLabel="Avg SoC (%)"
              xDomain={[0, 23]}
              xTickFormat={(v) => `${String(v).padStart(2, "0")}:00`}
              yTickFormat={(v) => `${fmt.num(v, 0)}%`}
            />
          )}
        </div>

        <div className="card">
          <div className="card-title">Grid flow by hour of day</div>
          <BarChart
            groups={hnByHour.map((h) => ({
              label: String(h.hour),
              values: [
                { name: "Exports", value: h.mean_exports_kWh, color: "var(--color-green)" },
                { name: "Imports", value: -h.mean_imports_kWh, color: "var(--color-red)" },
              ],
            }))}
            mode="diverging"
            height={360}
            yLabel="kWh / tick"
            valueFormatter={(v) => fmt.num(v, 2)}
          />
        </div>
      </div>

      <div className="card">
        <div className="card-title">
          Peak demand vs. peak production
          <span style={{ fontWeight: 400, color: "var(--color-ink-dim)", textTransform: "none", letterSpacing: 0, marginLeft: 10 }}>
            peak load {String(peakLoadH).padStart(2, "0")}:00 · peak gen {String(peakGenH).padStart(2, "0")}:00
          </span>
        </div>
        <BarChart
          groups={hnByHour.map((h) => ({
            label: String(h.hour),
            values: [
              {
                name: "Load",
                value: h.mean_load_kWh,
                color: "rgba(239,68,68,0.85)",
              },
              {
                name: "Generation",
                value: h.mean_gen_kWh,
                color: "rgba(245,158,11,0.85)",
              },
            ],
          }))}
          height={360}
          yLabel="kWh / tick"
          valueFormatter={(v) => fmt.num(v, 2)}
        />
      </div>
    </div>
  );
}
