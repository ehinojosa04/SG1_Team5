import { useMemo } from "react";
import * as d3 from "d3";
import BarChart from "../components/charts/BarChart";
import Heatmap from "../components/charts/Heatmap";
import type { DailyHouseholdRow, Dataset, Filters, WealthLevel } from "../types";
import { TYPE_ORDER, WEALTH_COLORS, WEALTH_ORDER } from "../types";
import { fmt } from "../components/charts/useChart";

interface Props {
  dataset: Dataset;
  filters: Filters;
  fd: DailyHouseholdRow[];
}

export default function ByWealth({ dataset, fd }: Props) {
  const importCost = dataset.manifest?.import_cost ?? 0.75;
  const exportCost = dataset.manifest?.export_cost ?? 0.9;

  const byWealth = useMemo(() => {
    const grouped = d3.rollups(
      fd,
      (rs) => ({
        houses: new Set(rs.map((r) => r.house_id)).size,
        gen: d3.sum(rs, (r) => r.generation_kWh),
        load: d3.sum(rs, (r) => r.load_kWh),
        imp: d3.sum(rs, (r) => r.grid_imports_kWh),
        exp: d3.sum(rs, (r) => r.grid_exports_kWh),
        savings: d3.sum(rs, (r) => r.savings),
      }),
      (r) => r.wealth,
    );
    return grouped
      .map(([wealth, v]) => ({
        wealth: wealth as WealthLevel,
        ...v,
        savings_per_home: v.savings / (v.houses || 1),
      }))
      .sort((a, b) => WEALTH_ORDER.indexOf(a.wealth) - WEALTH_ORDER.indexOf(b.wealth));
  }, [fd]);

  const heatCells = useMemo(() => {
    const grouped = d3.rollups(
      fd,
      (rs) => ({
        imp: d3.sum(rs, (r) => r.grid_imports_kWh),
        exp: d3.sum(rs, (r) => r.grid_exports_kWh),
      }),
      (r) => r.type,
      (r) => r.wealth,
    );
    const cells: { row: string; col: string; value: number }[] = [];
    for (const [type, wealths] of grouped)
      for (const [w, v] of wealths)
        cells.push({
          row: type,
          col: w,
          value: v.exp * exportCost - v.imp * importCost,
        });
    return cells;
  }, [fd, importCost, exportCost]);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Production vs. consumption (totals)</div>
          <BarChart
            groups={byWealth.map((r) => ({
              label: r.wealth,
              values: [
                { name: "Generation", value: r.gen, color: "var(--color-green)" },
                { name: "Consumption", value: r.load, color: "var(--color-red)" },
              ],
            }))}
            orderLabels={WEALTH_ORDER.filter((w) => byWealth.some((r) => r.wealth === w))}
            yLabel="kWh"
            valueFormatter={(v) => fmt.int(v)}
          />
        </div>
        <div className="card">
          <div className="card-title">Savings per household</div>
          <BarChart
            groups={byWealth.map((r) => ({
              label: r.wealth,
              values: [
                {
                  name: "Savings / home",
                  value: r.savings_per_home,
                  color: WEALTH_COLORS[r.wealth],
                },
              ],
            }))}
            orderLabels={WEALTH_ORDER.filter((w) => byWealth.some((r) => r.wealth === w))}
            yLabel="$"
            valueFormatter={(v) => fmt.money(v)}
          />
        </div>
      </div>

      <div className="card">
        <div className="card-title">Wealth × Type — net $ balance</div>
        <Heatmap
          data={heatCells}
          rowOrder={TYPE_ORDER.filter((t) => heatCells.some((c) => c.row === t))}
          colOrder={WEALTH_ORDER.filter((w) => heatCells.some((c) => c.col === w))}
          colorScheme="rdylgn"
          diverging
          height={360}
          showValues
          valueFormatter={(v) => fmt.money(v)}
        />
      </div>
    </div>
  );
}
