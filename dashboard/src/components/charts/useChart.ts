import { useEffect, useRef, useState } from "react";

export interface Size {
  width: number;
  height: number;
}

/** Observes a container and returns its content-box size. */
export function useContainerSize<T extends HTMLElement>(
  defaultHeight = 320,
): { ref: React.RefObject<T>; size: Size } {
  const ref = useRef<T>(null);
  const [size, setSize] = useState<Size>({ width: 0, height: defaultHeight });

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const cr = entry.contentRect;
        setSize({
          width: Math.max(0, Math.floor(cr.width)),
          height: defaultHeight,
        });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [defaultHeight]);

  return { ref, size };
}

/** Tiny singleton DOM tooltip (no React re-renders). */
let tooltipEl: HTMLDivElement | null = null;
function ensureTooltip(): HTMLDivElement {
  if (tooltipEl) return tooltipEl;
  tooltipEl = document.createElement("div");
  tooltipEl.className = "d3-tooltip";
  document.body.appendChild(tooltipEl);
  return tooltipEl;
}

export const tooltip = {
  show(html: string, x: number, y: number) {
    const el = ensureTooltip();
    el.innerHTML = html;
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    el.classList.add("visible");
  },
  move(x: number, y: number) {
    const el = ensureTooltip();
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
  },
  hide() {
    if (!tooltipEl) return;
    tooltipEl.classList.remove("visible");
  },
};

export const fmt = {
  int: (n: number) =>
    Number.isFinite(n)
      ? n.toLocaleString(undefined, { maximumFractionDigits: 0 })
      : "—",
  num: (n: number, d = 1) =>
    Number.isFinite(n)
      ? n.toLocaleString(undefined, {
          minimumFractionDigits: d,
          maximumFractionDigits: d,
        })
      : "—",
  money: (n: number) =>
    Number.isFinite(n)
      ? `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
      : "—",
  pct: (n: number, d = 0) =>
    Number.isFinite(n) ? `${n.toFixed(d)}%` : "—",
};
