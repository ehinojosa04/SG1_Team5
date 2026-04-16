import { useMemo } from "react";
import KPI from "../components/KPI";
import TimeSeriesChart from "../components/charts/TimeSeriesChart";
import DivergentBars from "../components/charts/DivergentBars";
import type {
  DailyHouseholdRow,
  Dataset,
  Filters,
} from "../types";
import { fmt } from "../components/charts/useChart";
import { selectedHouseIds } from "../App";
import * as d3 from "d3";

interface Props {
  dataset: Dataset;
  filters: Filters;
  fd: DailyHouseholdRow[];
}

export default function Overview({ dataset, filters, fd }: Props) {
  const importCost = dataset.manifest?.import_cost ?? 0.75;
  const exportCost = dataset.manifest?.export_cost ?? 0.9;

  const selHh = useMemo(() => {
    const ids = new Set(selectedHouseIds(dataset, filters));
    return dataset.households.filter((h) => ids.has(h.house_id));
  }, [dataset, filters]);

  const agg = useMemo(() => {
    const gen = d3.sum(fd, (d) => d.generation_kWh);
    const load = d3.sum(fd, (d) => d.load_kWh);
    const self = d3.sum(fd, (d) => d.self_consumption_kWh);
    const imp = d3.sum(fd, (d) => d.grid_imports_kWh);
    const exp = d3.sum(fd, (d) => d.grid_exports_kWh);
    const savings = d3.sum(fd, (d) => d.savings);
    return { gen, load, self, imp, exp, savings };
  }, [fd]);

  const cost = agg.imp * importCost;
  const credit = agg.exp * exportCost;
  const balance = credit - cost;

  const byDate = useMemo(() => {
    const m = d3.rollups(
      fd,
      (rows) => ({
        gen: d3.sum(rows, (r) => r.generation_kWh),
        load: d3.sum(rows, (r) => r.load_kWh),
        imp: d3.sum(rows, (r) => r.grid_imports_kWh),
        exp: d3.sum(rows, (r) => r.grid_exports_kWh),
      }),
      (r) => +r.date,
    );
    return m
      .map(([ts, v]) => ({ t: new Date(ts), ...v }))
      .sort((a, b) => +a.t - +b.t);
  }, [fd]);

  const cloudMean = useMemo(
    () => d3.mean(dataset.system, (s) => s.cloud_coverage) ?? 0,
    [dataset],
  );

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI label="Households in view" value={`${selHh.length}`} />
        <KPI
          label="Solar homes"
          value={`${selHh.filter((h) => h.has_solar).length}`}
          sub={`${fmt.pct(
            selHh.length ? (selHh.filter((h) => h.has_solar).length / selHh.length) * 100 : 0,
          )} of view`}
        />
        <KPI
          label="Battery homes"
          value={`${selHh.filter((h) => h.has_battery).length}`}
          sub={`${fmt.pct(
            selHh.length ? (selHh.filter((h) => h.has_battery).length / selHh.length) * 100 : 0,
          )} of view`}
        />
        <KPI label="Avg cloud cover" value={fmt.num(cloudMean, 2)} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI label="Total generation" value={`${fmt.int(agg.gen)} kWh`} />
        <KPI label="Total consumption" value={`${fmt.int(agg.load)} kWh`} />
        <KPI
          label="Self-consumption"
          value={`${fmt.int(agg.self)} kWh`}
          sub={`${fmt.pct(agg.load ? (agg.self / agg.load) * 100 : 0, 1)} of load`}
        />
        <KPI
          label="Net grid flow"
          value={`${fmt.int(agg.exp - agg.imp)} kWh`}
          sub={`imports ${fmt.int(agg.imp)} · exports ${fmt.int(agg.exp)}`}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <KPI label="Import cost" value={fmt.money(cost)} accent="var(--color-red)" />
        <KPI label="Export credit" value={fmt.money(credit)} accent="var(--color-green)" />
        <KPI
          label="Net balance"
          value={fmt.money(balance)}
          sub={`savings vs no-solar baseline: ${fmt.money(agg.savings)}`}
          accent="var(--color-accent)"
        />
      </div>

      <div className="card">
        <div className="card-title">Production vs. consumption</div>
        <TimeSeriesChart
          series={[
            {
              name: "Consumption",
              color: "var(--color-red)",
              values: byDate.map((d) => ({ t: d.t, v: d.load })),
            },
            {
              name: "Production",
              color: "var(--color-green)",
              kind: "area",
              values: byDate.map((d) => ({ t: d.t, v: d.gen })),
            },
          ]}
          yLabel="kWh / day"
          valueFormatter={(v) => `${fmt.int(v)} kWh`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Grid imports vs exports</div>
          <DivergentBars
            data={byDate.map((d) => ({ t: d.t, pos: d.exp, neg: d.imp }))}
            posLabel="Exports"
            negLabel="Imports"
            posColor="var(--color-green)"
            negColor="var(--color-red)"
            yLabel="kWh / day"
          />
        </div>
        <div className="card">
          <div className="card-title">Surplus vs. deficit (gen − load)</div>
          <TimeSeriesChart
            series={[
              {
                name: "Net",
                color: "var(--color-violet)",
                kind: "area",
                values: byDate.map((d) => ({ t: d.t, v: d.gen - d.load })),
              },
            ]}
            yLabel="kWh / day"
            valueFormatter={(v) => `${fmt.num(v, 0)} kWh`}
          />
        </div>
      </div>
    </div>
  );
}
