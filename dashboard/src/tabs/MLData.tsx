import { useMemo } from "react";
import * as d3 from "d3";
import KPI from "../components/KPI";
import ScatterPlot, { type ScatterPoint } from "../components/charts/ScatterPlot";
import LineChart, { type LineSeries } from "../components/charts/LineChart";
import BarChart from "../components/charts/BarChart";
import type { Dataset, MLDataset, MLPreparedRow } from "../types";
import { fmt } from "../components/charts/useChart";

interface Props {
  dataset: Dataset;
}

const COLORS = {
  base: "#60a5fa",
  alt: "#f472b6",
  da: "#f59e0b",
  ha4: "#34d399",
  diff: "#a78bfa",
};

const dayKey = (d: Date) => +new Date(d.getFullYear(), d.getMonth(), d.getDate());
const dayOfYear = (d: Date) =>
  Math.floor((dayKey(d) - +new Date(d.getFullYear(), 0, 0)) / 86400000);

function dailyMean(rows: MLPreparedRow[]) {
  return d3
    .rollups(
      rows,
      (rs) => ({
        date: rs[0].timestamp,
        actual: d3.mean(rs, (r) => r.actual_mw) ?? 0,
        da: d3.mean(rs, (r) => r.da_mw) ?? 0,
        ha4: d3.mean(rs, (r) => r.ha4_mw) ?? 0,
      }),
      (r) => dayKey(r.timestamp),
    )
    .map(([, v]) => v)
    .sort((a, b) => +a.date - +b.date);
}

function sampleScatter(rows: MLPreparedRow[], color: string, variant: string): ScatterPoint[] {
  return rows
    .filter((_, i) => i % 24 === 0)
    .map((r) => ({
      x: r.ghi,
      y: r.actual_mw,
      color,
      size: Math.max(1, r.capacity_factor * 5),
      label: `${variant} · ${r.timestamp.toISOString().slice(0, 16).replace("T", " ")}`,
    }));
}

function sampleWeek(rows: MLPreparedRow[]) {
  const start = new Date("2006-06-15T00:00:00");
  const end = new Date("2006-06-22T00:00:00");
  const selected = rows.filter((r) => r.timestamp >= start && r.timestamp < end);
  return selected.length ? selected : rows.slice(0, 96 * 7);
}

const splitSummary = (counts: Record<string, number>) =>
  `tr ${fmt.int(counts.train)} · val ${fmt.int(counts.validation)} · test ${fmt.int(counts.test)}`;

export default function MLData({ dataset }: Props) {
  const ml = dataset.mlData;

  if (!ml) {
    return (
      <div className="card max-w-2xl">
        <div className="card-title" style={{ color: "var(--color-red)" }}>
          ML data unavailable
        </div>
        <pre style={{ whiteSpace: "pre-wrap", color: "var(--color-ink-dim)" }}>
          Run cd simulation && ../venv/bin/python ml/prepare_data.py
        </pre>
      </div>
    );
  }

  return <MLDataContent ml={ml} />;
}

function MLDataContent({ ml }: { ml: MLDataset }) {
  const baseSummary = ml.summary.variants.base;
  const altSummary = ml.summary.variants.alt_1;

  const scatter = useMemo(
    () => [
      ...sampleScatter(ml.base, COLORS.base, "base"),
      ...sampleScatter(ml.alt1, COLORS.alt, "alt_1"),
    ],
    [ml],
  );

  const daily = useMemo(() => {
    const base = dailyMean(ml.base);
    const alt = dailyMean(ml.alt1);
    const altByDay = new Map(alt.map((d) => [dayKey(d.date), d]));
    const diff = base
      .map((d) => {
        const other = altByDay.get(dayKey(d.date));
        return other ? { date: d.date, diff: d.actual - other.actual } : null;
      })
      .filter(Boolean) as { date: Date; diff: number }[];
    return { base, alt, diff };
  }, [ml]);

  const week = useMemo(() => sampleWeek(ml.base), [ml.base]);
  const weekSeries = useMemo<LineSeries[]>(
    () => [
      {
        name: "Actual",
        color: COLORS.base,
        values: week.map((r, i) => ({ x: i, y: r.actual_mw })),
      },
      {
        name: "DA",
        color: COLORS.da,
        dash: "4 3",
        values: week.map((r, i) => ({ x: i, y: r.da_mw })),
      },
      {
        name: "HA4",
        color: COLORS.ha4,
        dash: "2 3",
        values: week.map((r, i) => ({ x: i, y: r.ha4_mw })),
      },
    ],
    [week],
  );

  const cloudGroups = useMemo(() => {
    const counts = d3.rollups(
      ml.base,
      (rs) => rs.length,
      (r) => String(r.cloud_type),
    );
    return counts
      .sort((a, b) => +a[0] - +b[0])
      .map(([label, value]) => ({
        label,
        values: [{ name: "Rows", value, color: "var(--color-accent)" }],
      }));
  }, [ml.base]);

  const variantDiff = ml.summary.variant_comparison.actual_mw;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI
          label="Base rows"
          value={fmt.int(baseSummary.rows)}
          sub={splitSummary(baseSummary.split_counts)}
        />
        <KPI
          label="Alt rows"
          value={fmt.int(altSummary.rows)}
          sub={splitSummary(altSummary.split_counts)}
        />
        <KPI
          label="Base GHI corr"
          value={fmt.num(baseSummary.congruence.actual_ghi_correlation, 3)}
          sub={`alt ${fmt.num(altSummary.congruence.actual_ghi_correlation, 3)}`}
        />
        <KPI
          label="Variant gap"
          value={`${fmt.num(variantDiff.mean_abs_difference, 2)} MW`}
          sub={`${fmt.int(variantDiff.rows_abs_difference_gt_5)} rows > 5 MW`}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI
          label="Low-GHI rows"
          value={`${baseSummary.congruence.low_ghi_high_production_rows}`}
          sub={`alt ${altSummary.congruence.low_ghi_high_production_rows}`}
        />
        <KPI
          label="Large jumps"
          value={`${baseSummary.congruence.large_15min_actual_jump_rows}`}
          sub={`alt ${altSummary.congruence.large_15min_actual_jump_rows}`}
        />
        <KPI
          label="DA MAE"
          value={`${fmt.num(baseSummary.forecast_metrics.da_mw.mae_mw, 2)} MW`}
          sub={`alt ${fmt.num(altSummary.forecast_metrics.da_mw.mae_mw, 2)} MW`}
        />
        <KPI
          label="HA4 MAE"
          value={`${fmt.num(baseSummary.forecast_metrics.ha4_mw.mae_mw, 2)} MW`}
          sub={`alt ${fmt.num(altSummary.forecast_metrics.ha4_mw.mae_mw, 2)} MW`}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Actual production vs GHI</div>
          <ScatterPlot
            points={scatter}
            height={390}
            xLabel="GHI (W/m²)"
            yLabel="Actual MW"
            xFmt={(v) => fmt.num(v, 0)}
            yFmt={(v) => `${fmt.num(v, 1)} MW`}
          />
        </div>

        <div className="card">
          <div className="card-title">Daily production over year</div>
          <LineChart
            series={[
              {
                name: "Base",
                color: COLORS.base,
                values: daily.base.map((d) => ({ x: dayOfYear(d.date), y: d.actual })),
              },
              {
                name: "Alt 1",
                color: COLORS.alt,
                values: daily.alt.map((d) => ({ x: dayOfYear(d.date), y: d.actual })),
              },
            ]}
            height={390}
            xLabel="Day of year"
            yLabel="Mean MW"
            xDomain={[1, 365]}
            xTickFormat={(v) => String(v)}
            yTickFormat={(v) => `${fmt.num(v, 1)} MW`}
            markers={false}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="card">
          <div className="card-title">Base minus alt daily actual</div>
          <LineChart
            series={[
              {
                name: "Base - Alt 1",
                color: COLORS.diff,
                values: daily.diff.map((d) => ({ x: dayOfYear(d.date), y: d.diff })),
              },
            ]}
            height={360}
            xLabel="Day of year"
            yLabel="MW difference"
            xDomain={[1, 365]}
            yTickFormat={(v) => `${fmt.num(v, 1)} MW`}
            markers={false}
            zeroLine
          />
        </div>

        <div className="card">
          <div className="card-title">Forecast vs actual sample week</div>
          <LineChart
            series={weekSeries}
            height={360}
            xLabel="Hours since start"
            yLabel="MW"
            xTickFormat={(v) => `${fmt.num(v / 4, 0)}h`}
            yTickFormat={(v) => `${fmt.num(v, 1)} MW`}
            markers={false}
          />
        </div>
      </div>

      <div className="card">
        <div className="card-title">Cloud type distribution</div>
        <BarChart
          groups={cloudGroups}
          height={340}
          yLabel="Rows"
          valueFormatter={(v) => fmt.int(v)}
        />
      </div>
    </div>
  );
}
