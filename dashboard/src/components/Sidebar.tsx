import type { Dataset, Filters, Granularity, HouseType, WealthLevel } from "../types";
import { TYPE_ORDER, WEALTH_ORDER } from "../types";

interface Props {
  dataset: Dataset;
  filters: Filters;
  onChange: (next: Filters) => void;
}

const GRANULARITIES: Granularity[] = ["hour", "day", "week", "month"];

export default function Sidebar({ dataset, filters, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });
  const hh = dataset.households;
  const strategies = Array.from(new Set(hh.map((h) => h.strategy))).sort();

  const toggle = <T extends string>(list: T[], v: T): T[] =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v];

  const minDate = dataset.system[0]?.timestamp;
  const maxDate = dataset.system[dataset.system.length - 1]?.timestamp;

  const dateStr = (d: Date) => d.toISOString().slice(0, 10);

  return (
    <aside
      className="flex flex-col gap-5 p-5 h-full overflow-y-auto"
      style={{
        width: 300,
        background: "var(--color-panel)",
        borderRight: "1px solid var(--color-border)",
      }}
    >
      <div>
        <div style={{ fontSize: 11, letterSpacing: "0.15em", color: "var(--color-ink-dim)", textTransform: "uppercase" }}>
          Green Grid
        </div>
        <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em", marginTop: 2 }}>
          Neighborhood Solar
        </div>
        {dataset.manifest && (
          <div style={{ fontSize: 12, color: "var(--color-ink-dim)", marginTop: 6 }}>
            Scenario <b style={{ color: "var(--color-ink)" }}>{dataset.manifest.scenario}</b>
            {" · "}
            {dataset.manifest.n_households} houses
            <br />
            generated {dataset.manifest.generated_at.slice(0, 16).replace("T", " ")}
          </div>
        )}
      </div>

      <div className="field">
        <div className="field-label">Household type</div>
        <div className="flex flex-wrap gap-1.5">
          {TYPE_ORDER.filter((t) => hh.some((h) => h.type === t)).map((t) => (
            <button
              key={t}
              className={`chip ${filters.types.includes(t) ? "on" : ""}`}
              onClick={() => set({ types: toggle(filters.types, t as HouseType) })}
            >
              {t.toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <div className="field-label">Wealth level</div>
        <div className="flex flex-wrap gap-1.5">
          {WEALTH_ORDER.filter((w) => hh.some((h) => h.wealth === w)).map((w) => (
            <button
              key={w}
              className={`chip ${filters.wealths.includes(w) ? "on" : ""}`}
              onClick={() => set({ wealths: toggle(filters.wealths, w as WealthLevel) })}
            >
              {w.toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <div className="field-label">Charge strategy</div>
        <div className="flex flex-wrap gap-1.5">
          {strategies.map((s) => (
            <button
              key={s}
              className={`chip ${filters.strategies.includes(s) ? "on" : ""}`}
              onClick={() => set({ strategies: toggle(filters.strategies, s) })}
            >
              {s.toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <div className="field-label">Solar</div>
        <div className="flex gap-1.5">
          {(["all", "solar", "non-solar"] as const).map((o) => (
            <button
              key={o}
              className={`chip ${filters.solar === o ? "on" : ""}`}
              onClick={() => set({ solar: o })}
            >
              {o === "all" ? "all" : o === "solar" ? "only solar" : "no solar"}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <div className="field-label">Battery</div>
        <div className="flex gap-1.5">
          {(["all", "battery", "non-battery"] as const).map((o) => (
            <button
              key={o}
              className={`chip ${filters.battery === o ? "on" : ""}`}
              onClick={() => set({ battery: o })}
            >
              {o === "all" ? "all" : o === "battery" ? "only battery" : "no battery"}
            </button>
          ))}
        </div>
      </div>

      {minDate && maxDate && (
        <div className="field">
          <div className="field-label">Date range</div>
          <div className="flex gap-2">
            <input
              type="date"
              className="input"
              min={dateStr(minDate)}
              max={dateStr(maxDate)}
              value={dateStr(filters.start)}
              onChange={(e) => set({ start: new Date(e.target.value) })}
            />
            <input
              type="date"
              className="input"
              min={dateStr(minDate)}
              max={dateStr(maxDate)}
              value={dateStr(filters.end)}
              onChange={(e) => set({ end: new Date(e.target.value) })}
            />
          </div>
        </div>
      )}

      <div className="field">
        <div className="field-label">Granularity</div>
        <select
          className="select"
          value={filters.granularity}
          onChange={(e) => set({ granularity: e.target.value as Granularity })}
        >
          {GRANULARITIES.map((g) => (
            <option key={g} value={g}>
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginTop: "auto", fontSize: 11, color: "var(--color-ink-dim)" }}>
        <a
          href="https://d3js.org/"
          target="_blank"
          rel="noreferrer"
          style={{ color: "var(--color-accent)" }}
        >
          Charts powered by D3
        </a>
      </div>
    </aside>
  );
}
