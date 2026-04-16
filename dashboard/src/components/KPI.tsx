interface Props {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}

export default function KPI({ label, value, sub, accent }: Props) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div
        className="card-title"
        style={{ marginBottom: 6, color: accent ?? undefined }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 24,
          fontWeight: 600,
          letterSpacing: "-0.01em",
          fontVariantNumeric: "tabular-nums",
          color: "#f3f4f6",
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            marginTop: 6,
            fontSize: 12,
            color: "var(--color-ink-dim)",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}
