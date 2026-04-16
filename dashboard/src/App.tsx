import { useEffect, useMemo, useState } from "react";
import { loadDataset } from "./data/loader";
import type { Dataset, Filters, HouseType, WealthLevel } from "./types";
import { TYPE_ORDER, WEALTH_ORDER } from "./types";
import Sidebar from "./components/Sidebar";
import Overview from "./tabs/Overview";
import DuckCurve from "./tabs/DuckCurve";
import ByType from "./tabs/ByType";
import ByWealth from "./tabs/ByWealth";
import Economics from "./tabs/Economics";
import Adoption from "./tabs/Adoption";
import BatteryGrid from "./tabs/BatteryGrid";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "duck", label: "Duck Curve" },
  { id: "type", label: "By Type" },
  { id: "wealth", label: "By Wealth" },
  { id: "economics", label: "Economics" },
  { id: "adoption", label: "Adoption" },
  { id: "battery", label: "Battery & Grid" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("overview");
  const [filters, setFilters] = useState<Filters | null>(null);

  useEffect(() => {
    loadDataset()
      .then((d) => {
        setDataset(d);
        const types = Array.from(new Set(d.households.map((h) => h.type))) as HouseType[];
        const wealths = Array.from(new Set(d.households.map((h) => h.wealth))) as WealthLevel[];
        const strats = Array.from(new Set(d.households.map((h) => h.strategy)));
        const start = d.system[0]?.timestamp ?? new Date();
        const end = d.system[d.system.length - 1]?.timestamp ?? new Date();
        setFilters({
          types: TYPE_ORDER.filter((t) => types.includes(t)),
          wealths: WEALTH_ORDER.filter((w) => wealths.includes(w)),
          strategies: strats,
          solar: "all",
          battery: "all",
          start,
          end,
          granularity: "day",
        });
      })
      .catch((e: Error) =>
        setErr(
          `${e.message}. Run the simulation first:\n  cd simulation && python simulation.py`,
        ),
      );
  }, []);

  if (err) {
    return (
      <div className="h-full flex items-center justify-center p-10">
        <div className="card max-w-xl">
          <div className="card-title" style={{ color: "var(--color-red)" }}>
            Could not load data
          </div>
          <pre style={{ whiteSpace: "pre-wrap", color: "var(--color-ink-dim)" }}>
            {err}
          </pre>
        </div>
      </div>
    );
  }

  if (!dataset || !filters) {
    return (
      <div className="h-full flex items-center justify-center text-sm" style={{ color: "var(--color-ink-dim)" }}>
        Loading data…
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <Sidebar dataset={dataset} filters={filters} onChange={setFilters} />
      <main className="flex-1 flex flex-col min-w-0">
        <header
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: "1px solid var(--color-border)" }}
        >
          <div>
            <div
              style={{
                fontSize: 11,
                letterSpacing: "0.15em",
                textTransform: "uppercase",
                color: "var(--color-ink-dim)",
              }}
            >
              Digital Twin · SG1 Team 5
            </div>
            <h1
              style={{
                fontSize: 22,
                fontWeight: 600,
                letterSpacing: "-0.01em",
                margin: 0,
              }}
            >
              Green Grid — Neighborhood Solar Dashboard
            </h1>
          </div>
          <div
            style={{
              fontSize: 12,
              color: "var(--color-ink-dim)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {dataset.manifest?.start.slice(0, 10)} → {dataset.manifest?.end.slice(0, 10)}
          </div>
        </header>

        <nav
          className="flex gap-1 px-4 py-2"
          style={{ borderBottom: "1px solid var(--color-border)" }}
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? "active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="flex-1 overflow-y-auto p-6">
          <TabView tab={tab} dataset={dataset} filters={filters} />
        </div>
      </main>
    </div>
  );
}

function TabView({
  tab,
  dataset,
  filters,
}: {
  tab: TabId;
  dataset: Dataset;
  filters: Filters;
}) {
  const fd = useMemo(() => filterDaily(dataset, filters), [dataset, filters]);
  switch (tab) {
    case "overview":
      return <Overview dataset={dataset} filters={filters} fd={fd} />;
    case "duck":
      return <DuckCurve dataset={dataset} filters={filters} fd={fd} />;
    case "type":
      return <ByType dataset={dataset} filters={filters} fd={fd} />;
    case "wealth":
      return <ByWealth dataset={dataset} filters={filters} fd={fd} />;
    case "economics":
      return <Economics dataset={dataset} filters={filters} fd={fd} />;
    case "adoption":
      return <Adoption dataset={dataset} filters={filters} fd={fd} />;
    case "battery":
      return <BatteryGrid dataset={dataset} filters={filters} fd={fd} />;
  }
}

export function filterDaily(dataset: Dataset, f: Filters) {
  const ids = new Set(selectedHouseIds(dataset, f));
  const startTs = +new Date(f.start.getFullYear(), f.start.getMonth(), f.start.getDate());
  const endTs = +new Date(f.end.getFullYear(), f.end.getMonth(), f.end.getDate(), 23, 59);
  return dataset.daily.filter(
    (r) => ids.has(r.house_id) && +r.date >= startTs && +r.date <= endTs,
  );
}

export function selectedHouseIds(dataset: Dataset, f: Filters): number[] {
  return dataset.households
    .filter(
      (h) =>
        f.types.includes(h.type) &&
        f.wealths.includes(h.wealth) &&
        f.strategies.includes(h.strategy) &&
        (f.solar === "all" ? true : f.solar === "solar" ? h.has_solar : !h.has_solar) &&
        (f.battery === "all"
          ? true
          : f.battery === "battery"
            ? h.has_battery
            : !h.has_battery),
    )
    .map((h) => h.house_id);
}
