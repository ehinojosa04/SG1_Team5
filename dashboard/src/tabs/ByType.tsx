import { useMemo, useState } from "react";
import * as d3 from "d3";
import BarChart from "../components/charts/BarChart";
import Heatmap from "../components/charts/Heatmap";
import BoxPlot from "../components/charts/BoxPlot";
import type { DailyHouseholdRow, Dataset, Filters, HouseType } from "../types";
import { TYPE_COLORS, TYPE_ORDER } from "../types";
import { fmt } from "../components/charts/useChart";

interface Props {
  dataset: Dataset;
  filters: Filters;
  fd: DailyHouseholdRow[];
}

export default function ByType({ dataset, fd, filters }: Props) {
  const [perHome, setPerHome] = useState(true);

  const byType = useMemo(() => {
    const grouped = d3.rollups(
      fd,
      (rs) => ({
        houses: new Set(rs.map((r) => r.house_id)).size,
        gen: d3.sum(rs, (r) => r.generation_kWh),
        load: d3.sum(rs, (r) => r.load_kWh),
        self: d3.sum(rs, (r) => r.self_consumption_kWh),
        imp: d3.sum(rs, (r) => r.grid_imports_kWh),
        exp: d3.sum(rs, (r) => r.grid_exports_kWh),
        savings: d3.sum(rs, (r) => r.savings),
      }),
      (r) => r.type,
    );
    return grouped
      .map(([type, v]) => ({
        type: type as HouseType,
        ...v,
        gen_per: v.gen / (v.houses || 1),
        load_per: v.load / (v.houses || 1),
      }))
      .sort((a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type));
  }, [fd]);

  const loadHeat = useMemo(() => {
    const seg = dataset.hourlySeg.filter((r) => filters.wealths.includes(r.wealth));
    const byTypeHour = d3.rollups(
      seg,
      (rs) => d3.mean(rs, (r) => r.mean_load_kWh) ?? 0,
      (r) => r.type,
      (r) => r.hour,
    );
    const cells: { row: string; col: string; value: number }[] = [];
    for (const [type, hours] of byTypeHour) {
      for (const [h, v] of hours) {
        cells.push({ row: type, col: String(h), value: v });
      }
    }
    return cells;
  }, [dataset, filters]);

  const boxBoxes = useMemo(() => {
    return TYPE_ORDER.filter((t) => fd.some((r) => r.type === t)).map((t) => ({
      label: t,
      color: TYPE_COLORS[t],
      values: fd.filter((r) => r.type === t).map((r) => r.load_kWh),
    }));
  }, [fd]);

  return (
    <div className="flex flex-col gap-5">
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="card-title" style={{ margin: 0 }}>
            Breakdown by household type
          </div>
          <label
            className="chip"
            style={{ cursor: "pointer" }}
            onClick={() => setPerHome((v) => !v)}
          >
            <span style={{ color: perHome ? "var(--color-accent)" : "var(--color-ink-dim)" }}>●</span>
            Per-household averages
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Production vs. consumption</div>
          <BarChart
            groups={byType.map((r) => ({
              label: r.type,
              values: [
                {
                  name: "Generation",
                  value: perHome ? r.gen_per : r.gen,
                  color: "var(--color-green)",
                },
                {
                  name: "Consumption",
                  value: perHome ? r.load_per : r.load,
                  color: "var(--color-red)",
                },
              ],
            }))}
            orderLabels={TYPE_ORDER.filter((t) => byType.some((r) => r.type === t))}
            yLabel={`kWh${perHome ? " / home" : ""}`}
            valueFormatter={(v) => fmt.int(v)}
          />
        </div>
        <div className="card">
          <div className="card-title">Hour-of-day load heatmap (avg kWh / tick)</div>
          <Heatmap
            data={loadHeat}
            rowOrder={TYPE_ORDER.filter((t) => loadHeat.some((c) => c.row === t))}
            colOrder={Array.from({ length: 24 }, (_, i) => String(i))}
            colorScheme="reds"
            valueFormatter={(v) => fmt.num(v, 2)}
            unit="kWh"
          />
        </div>
      </div>

      <div className="card">
        <div className="card-title">Daily load distribution per type</div>
        <BoxPlot boxes={boxBoxes} yLabel="Daily consumption (kWh)" />
      </div>

      <div className="card">
        <div className="card-title">Segment numbers</div>
        <div style={{ overflowX: "auto" }}>
          <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ color: "var(--color-ink-dim)", textAlign: "right" }}>
                {[
                  "type",
                  "houses",
                  "generation (kWh)",
                  "load (kWh)",
                  "self-cons (kWh)",
                  "imports (kWh)",
                  "exports (kWh)",
                  "savings ($)",
                ].map((h, i) => (
                  <th
                    key={h}
                    style={{
                      padding: "8px 10px",
                      textAlign: i === 0 ? "left" : "right",
                      borderBottom: "1px solid var(--color-border)",
                      fontWeight: 500,
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      fontSize: 11,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody style={{ fontVariantNumeric: "tabular-nums" }}>
              {byType.map((r) => {
                const f = (v: number) => fmt.int(perHome ? v / (r.houses || 1) : v);
                return (
                  <tr key={r.type}>
                    <td style={cell(true)}>{r.type}</td>
                    <td style={cell()}>{r.houses}</td>
                    <td style={cell()}>{f(r.gen)}</td>
                    <td style={cell()}>{f(r.load)}</td>
                    <td style={cell()}>{f(r.self)}</td>
                    <td style={cell()}>{f(r.imp)}</td>
                    <td style={cell()}>{f(r.exp)}</td>
                    <td style={cell()}>{fmt.money(perHome ? r.savings / (r.houses || 1) : r.savings)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function cell(first = false): React.CSSProperties {
  return {
    padding: "8px 10px",
    borderBottom: "1px solid rgba(31,42,55,0.6)",
    textAlign: first ? "left" : "right",
  };
}
