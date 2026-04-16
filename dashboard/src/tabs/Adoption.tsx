import { useMemo } from "react";
import * as d3 from "d3";
import Heatmap from "../components/charts/Heatmap";
import ScatterPlot from "../components/charts/ScatterPlot";
import type { DailyHouseholdRow, Dataset, Filters } from "../types";
import { TYPE_ORDER, WEALTH_COLORS, WEALTH_ORDER } from "../types";
import { fmt } from "../components/charts/useChart";

interface Props {
  dataset: Dataset;
  filters: Filters;
  fd: DailyHouseholdRow[];
}

export default function Adoption({ dataset, fd }: Props) {
  const solarCells = useMemo(
    () =>
      dataset.adoption.map((r) => ({
        row: r.type,
        col: r.wealth,
        value: r.solar_adoption_pct,
      })),
    [dataset],
  );
  const batteryCells = useMemo(
    () =>
      dataset.adoption.map((r) => ({
        row: r.type,
        col: r.wealth,
        value: r.battery_adoption_pct,
      })),
    [dataset],
  );

  const savingsBySegment = useMemo(() => {
    return d3.rollups(
      fd,
      (rs) => ({
        houses: new Set(rs.map((r) => r.house_id)).size,
        savings: d3.sum(rs, (r) => r.savings),
      }),
      (r) => r.type,
      (r) => r.wealth,
    );
  }, [fd]);

  const scatter = useMemo(() => {
    const lookup = new Map<string, { houses: number; savings: number }>();
    for (const [type, ws] of savingsBySegment)
      for (const [w, v] of ws) lookup.set(`${type}|${w}`, v);
    return dataset.adoption.flatMap((r) => {
      const sv = lookup.get(`${r.type}|${r.wealth}`);
      if (!sv) return [];
      return [
        {
          x: r.solar_adoption_pct,
          y: sv.savings / (sv.houses || 1),
          size: r.houses,
          color: WEALTH_COLORS[r.wealth],
          label: `${r.type} / ${r.wealth}`,
        },
      ];
    });
  }, [dataset, savingsBySegment]);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Solar adoption rate (%) · type × wealth</div>
          <Heatmap
            data={solarCells}
            rowOrder={TYPE_ORDER}
            colOrder={WEALTH_ORDER}
            colorScheme="yellows"
            height={360}
            showValues
            valueFormatter={(v) => fmt.num(v, 0)}
            unit="%"
          />
        </div>
        <div className="card">
          <div className="card-title">Battery adoption rate (%) · type × wealth</div>
          <Heatmap
            data={batteryCells}
            rowOrder={TYPE_ORDER}
            colOrder={WEALTH_ORDER}
            colorScheme="blues"
            height={360}
            showValues
            valueFormatter={(v) => fmt.num(v, 0)}
            unit="%"
          />
        </div>
      </div>

      <div className="card">
        <div className="card-title">Adoption vs. per-home savings</div>
        <ScatterPlot
          points={scatter}
          height={380}
          xLabel="Solar adoption %"
          yLabel="Savings per home ($)"
          xFmt={(v) => fmt.num(v, 0)}
          yFmt={(v) => fmt.money(v)}
        />
      </div>
    </div>
  );
}
