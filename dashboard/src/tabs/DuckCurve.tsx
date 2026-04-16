import { useMemo, useState } from "react";
import * as d3 from "d3";
import LineChart, { type LineSeries } from "../components/charts/LineChart";
import KPI from "../components/KPI";
import type { DailyHouseholdRow, Dataset, Filters, HouseType, WealthLevel } from "../types";
import { TYPE_COLORS, TYPE_ORDER, WEALTH_COLORS, WEALTH_ORDER } from "../types";
import { fmt } from "../components/charts/useChart";

interface Props {
  dataset: Dataset;
  filters: Filters;
  fd: DailyHouseholdRow[];
}

type Mode = "total" | "type" | "wealth";

export default function DuckCurve({ dataset, filters }: Props) {
  const [mode, setMode] = useState<Mode>("total");

  const neighSeries = useMemo<LineSeries[]>(() => {
    const hn = dataset.hourlyNeigh;
    return [
      {
        name: "Gross load",
        color: "var(--color-red)",
        dash: "3 3",
        values: hn.map((h) => ({ x: h.hour, y: h.mean_load_kWh })),
      },
      {
        name: "Solar generation",
        color: "var(--color-accent)",
        dash: "3 3",
        values: hn.map((h) => ({ x: h.hour, y: h.mean_gen_kWh })),
      },
      {
        name: "Net load (the duck)",
        color: "#f3f4f6",
        width: 3,
        values: hn.map((h) => ({ x: h.hour, y: h.mean_net_load_kWh })),
      },
    ];
  }, [dataset]);

  const groupedSeries = useMemo<LineSeries[]>(() => {
    if (mode === "total") return [];
    const dim: "type" | "wealth" = mode;
    const seg = dataset.hourlySeg.filter((r) =>
      dim === "type"
        ? filters.wealths.includes(r.wealth)
        : filters.types.includes(r.type),
    );
    const keyList = (dim === "type" ? TYPE_ORDER : WEALTH_ORDER).filter((k) =>
      dim === "type" ? filters.types.includes(k as HouseType) : filters.wealths.includes(k as WealthLevel),
    );
    const palette = dim === "type" ? TYPE_COLORS : WEALTH_COLORS;
    return keyList.map((k) => {
      const rows = seg.filter((r) => (dim === "type" ? r.type === k : r.wealth === k));
      const grouped = d3.rollups(
        rows,
        (rs) => d3.mean(rs, (r) => r.mean_net_load_kWh) ?? 0,
        (r) => r.hour,
      ).sort((a, b) => a[0] - b[0]);
      return {
        name: k,
        color: (palette as Record<string, string>)[k],
        width: 2.5,
        values: grouped.map(([x, y]) => ({ x, y })),
      };
    });
  }, [dataset, filters, mode]);

  const peaks = useMemo(() => {
    const hn = dataset.hourlyNeigh;
    const peak = hn.reduce((a, b) => (a.mean_net_load_kWh > b.mean_net_load_kWh ? a : b));
    const trough = hn.reduce((a, b) => (a.mean_net_load_kWh < b.mean_net_load_kWh ? a : b));
    const genPeak = hn.reduce((a, b) => (a.mean_gen_kWh > b.mean_gen_kWh ? a : b));
    return {
      peak: peak.hour,
      trough: trough.hour,
      genPeak: genPeak.hour,
    };
  }, [dataset]);

  const series = mode === "total" ? neighSeries : groupedSeries;

  return (
    <div className="flex flex-col gap-5">
      <div className="card">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="card-title" style={{ marginBottom: 4 }}>
              Duck Curve · Net load by hour of day
            </div>
            <p style={{ fontSize: 13, color: "var(--color-ink-dim)", maxWidth: 680, margin: 0 }}>
              The classic "duck" shape: load stays high through the day, but midday solar pushes
              net load (what the grid has to serve) down — then demand shoots back up at dusk when
              the sun sets.
            </p>
          </div>
          <div className="flex gap-1.5">
            {[
              { id: "total", label: "Neighborhood" },
              { id: "type", label: "By type" },
              { id: "wealth", label: "By wealth" },
            ].map((o) => (
              <button
                key={o.id}
                className={`chip ${mode === (o.id as Mode) ? "on" : ""}`}
                onClick={() => setMode(o.id as Mode)}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <LineChart
            series={series}
            height={440}
            xLabel="Hour of day"
            yLabel="Net load per household (kWh / tick)"
            xDomain={[0, 23]}
            xTickFormat={(v) => `${String(v).padStart(2, "0")}:00`}
            yTickFormat={(v) => fmt.num(v, 2)}
            zeroLine
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <KPI label="Peak net-load hour" value={`${String(peaks.peak).padStart(2, "0")}:00`} />
        <KPI
          label="Lowest net-load hour"
          value={`${String(peaks.trough).padStart(2, "0")}:00`}
          sub="grid pressure is lowest here"
        />
        <KPI label="Peak production hour" value={`${String(peaks.genPeak).padStart(2, "0")}:00`} />
      </div>
    </div>
  );
}
