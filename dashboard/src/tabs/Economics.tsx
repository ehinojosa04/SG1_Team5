import { useMemo } from "react";
import * as d3 from "d3";
import KPI from "../components/KPI";
import TimeSeriesChart from "../components/charts/TimeSeriesChart";
import Histogram from "../components/charts/Histogram";
import BarChart from "../components/charts/BarChart";
import type { DailyHouseholdRow, Dataset, Filters } from "../types";
import { fmt } from "../components/charts/useChart";

interface Props {
  dataset: Dataset;
  filters: Filters;
  fd: DailyHouseholdRow[];
}

export default function Economics({ dataset, fd }: Props) {
  const importCost = dataset.manifest?.import_cost ?? 0.75;
  const exportCost = dataset.manifest?.export_cost ?? 0.9;

  const totals = useMemo(() => {
    const imp = d3.sum(fd, (r) => r.grid_imports_kWh);
    const exp = d3.sum(fd, (r) => r.grid_exports_kWh);
    const savings = d3.sum(fd, (r) => r.savings);
    const load = d3.sum(fd, (r) => r.load_kWh);
    return {
      balance: exp * exportCost - imp * importCost,
      savings,
      baseline: load * importCost,
    };
  }, [fd, importCost, exportCost]);

  const cumulative = useMemo(() => {
    const daily = d3.rollups(
      fd,
      (rs) => ({
        savings: d3.sum(rs, (r) => r.savings),
        cost: d3.sum(rs, (r) => r.cost),
      }),
      (r) => +r.date,
    );
    daily.sort((a, b) => a[0] - b[0]);
    let cs = 0;
    let cc = 0;
    return daily.map(([ts, v]) => {
      cs += v.savings;
      cc += v.cost;
      return { t: new Date(ts), cs, cc };
    });
  }, [fd]);

  const perHome = useMemo(() => {
    const grouped = d3.rollups(
      fd,
      (rs) => ({
        total: d3.sum(rs, (r) => r.savings),
        solar: rs[0]?.has_solar ?? false,
      }),
      (r) => r.house_id,
    );
    const solar = grouped.filter(([, v]) => v.solar).map(([, v]) => v.total);
    const noSolar = grouped.filter(([, v]) => !v.solar).map(([, v]) => v.total);
    return { solar, noSolar };
  }, [fd]);

  const segEcon = useMemo(() => {
    const grouped = d3.rollups(
      fd,
      (rs) => ({
        houses: new Set(rs.map((r) => r.house_id)).size,
        savings: d3.sum(rs, (r) => r.savings),
      }),
      (r) => r.type,
      (r) => r.wealth,
    );
    const rows: { label: string; value: number }[] = [];
    for (const [type, wealths] of grouped)
      for (const [w, v] of wealths)
        rows.push({ label: `${type} / ${w}`, value: v.savings / (v.houses || 1) });
    return rows.sort((a, b) => a.value - b.value);
  }, [fd]);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <KPI label="Neighborhood net balance" value={fmt.money(totals.balance)} accent="var(--color-violet)" />
        <KPI label="Savings vs no-solar baseline" value={fmt.money(totals.savings)} accent="var(--color-green)" />
        <KPI
          label="Counter-factual bill (all grid)"
          value={fmt.money(totals.baseline)}
          sub={`effective saving rate: ${fmt.pct(totals.baseline ? (totals.savings / totals.baseline) * 100 : 0, 1)}`}
        />
      </div>

      <div className="card">
        <div className="card-title">Cumulative savings over time</div>
        <TimeSeriesChart
          series={[
            {
              name: "Cumulative savings",
              color: "var(--color-green)",
              kind: "area",
              values: cumulative.map((d) => ({ t: d.t, v: d.cs })),
            },
            {
              name: "Cumulative grid cost",
              color: "var(--color-red)",
              dash: "3 3",
              values: cumulative.map((d) => ({ t: d.t, v: d.cc })),
            },
          ]}
          valueFormatter={(v) => fmt.money(v)}
          yLabel="$"
          height={360}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Per-household savings distribution</div>
          <Histogram
            series={[
              { name: "Solar homes", color: "var(--color-green)", values: perHome.solar },
              { name: "Non-solar homes", color: "#94a3b8", values: perHome.noSolar },
            ]}
            bins={24}
            xLabel="Total savings ($)"
          />
        </div>
        <div className="card">
          <div className="card-title">Winners & losers by segment</div>
          <BarChart
            groups={segEcon.map((r) => ({
              label: r.label,
              values: [
                {
                  name: "Savings / home",
                  value: r.value,
                  color: r.value >= 0 ? "var(--color-green)" : "var(--color-red)",
                },
              ],
            }))}
            horizontal
            height={Math.max(320, 24 * segEcon.length + 60)}
            yLabel="Savings per home ($)"
            valueFormatter={(v) => fmt.money(v)}
          />
        </div>
      </div>
    </div>
  );
}
