import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

export interface Series {
  name: string;
  color: string;
  values: { t: Date; v: number }[];
  kind?: "line" | "area";
  dash?: string;
}

interface Props {
  series: Series[];
  height?: number;
  yLabel?: string;
  valueFormatter?: (v: number) => string;
}

export default function TimeSeriesChart({
  series,
  height = 320,
  yLabel,
  valueFormatter = (v) => fmt.num(v, 1),
}: Props) {
  const { ref, size } = useContainerSize<HTMLDivElement>(height);

  useEffect(() => {
    if (!ref.current || !size.width) return;
    const margin = { top: 16, right: 20, bottom: 28, left: 54 };
    const w = size.width;
    const h = height;
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    const container = d3.select(ref.current);
    container.selectAll("svg").remove();
    const svg = container
      .append("svg")
      .attr("class", "chart")
      .attr("width", w)
      .attr("height", h);

    if (!series.length || !series.some((s) => s.values.length)) return;

    const all = series.flatMap((s) => s.values);
    const xExtent = d3.extent(all, (d) => d.t) as [Date, Date];
    const yMax = d3.max(all, (d) => d.v) ?? 1;
    const yMin = Math.min(0, d3.min(all, (d) => d.v) ?? 0);

    const x = d3.scaleTime().domain(xExtent).range([0, iw]);
    const y = d3
      .scaleLinear()
      .domain([yMin, yMax * 1.05 || 1])
      .nice()
      .range([ih, 0]);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    g.append("g")
      .attr("class", "grid")
      .call(
        d3
          .axisLeft(y)
          .tickSize(-iw)
          .tickFormat(() => ""),
      );

    g.append("g")
      .attr("class", "axis")
      .attr("transform", `translate(0,${ih})`)
      .call(
        d3
          .axisBottom(x)
          .ticks(Math.max(2, Math.floor(iw / 110)))
          .tickSizeOuter(0),
      );

    g.append("g")
      .attr("class", "axis")
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickFormat((d) => fmt.num(+d, 0)),
      );

    if (yLabel) {
      svg
        .append("text")
        .attr("class", "axis-title")
        .attr("x", margin.left)
        .attr("y", 12)
        .text(yLabel);
    }

    for (const s of series) {
      if (!s.values.length) continue;
      if (s.kind === "area") {
        const area = d3
          .area<{ t: Date; v: number }>()
          .x((d) => x(d.t))
          .y0(y(0))
          .y1((d) => y(d.v))
          .curve(d3.curveMonotoneX);
        g.append("path")
          .datum(s.values)
          .attr("fill", s.color)
          .attr("fill-opacity", 0.18)
          .attr("d", area);
      }
      const line = d3
        .line<{ t: Date; v: number }>()
        .x((d) => x(d.t))
        .y((d) => y(d.v))
        .curve(d3.curveMonotoneX);
      g.append("path")
        .datum(s.values)
        .attr("fill", "none")
        .attr("stroke", s.color)
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", s.dash || null)
        .attr("d", line);
    }

    // Legend
    const legend = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${h - 4})`);
    let offset = 0;
    series.forEach((s) => {
      const grp = legend.append("g").attr("transform", `translate(${offset},0)`);
      grp
        .append("rect")
        .attr("width", 10)
        .attr("height", 10)
        .attr("y", -10)
        .attr("rx", 2)
        .attr("fill", s.color);
      const txt = grp
        .append("text")
        .attr("x", 14)
        .attr("y", -1)
        .attr("fill", "currentColor")
        .text(s.name);
      offset += 24 + (txt.node()?.getComputedTextLength() ?? 40);
    });

    // Hover overlay
    const bisect = d3.bisector<{ t: Date; v: number }, Date>((d) => d.t).left;
    const focus = g.append("g").style("display", "none");
    focus
      .append("line")
      .attr("y1", 0)
      .attr("y2", ih)
      .attr("stroke", "#f59e0b")
      .attr("stroke-dasharray", "2 3")
      .attr("opacity", 0.6);
    const dots = series.map((s) =>
      focus
        .append("circle")
        .attr("r", 3.5)
        .attr("fill", s.color)
        .attr("stroke", "#0b0f14")
        .attr("stroke-width", 1),
    );

    g.append("rect")
      .attr("width", iw)
      .attr("height", ih)
      .attr("fill", "transparent")
      .on("pointerenter", () => focus.style("display", null))
      .on("pointerleave", () => {
        focus.style("display", "none");
        tooltip.hide();
      })
      .on("pointermove", (event) => {
        const [mx] = d3.pointer(event);
        const t = x.invert(mx);
        focus.attr("transform", `translate(${mx},0)`);
        const rows: string[] = [];
        series.forEach((s, i) => {
          if (!s.values.length) return;
          const idx = Math.max(
            0,
            Math.min(s.values.length - 1, bisect(s.values, t)),
          );
          const p = s.values[idx];
          const px = x(p.t) - mx;
          const py = y(p.v);
          dots[i].attr("cx", px).attr("cy", py);
          rows.push(
            `<div><span style="display:inline-block;width:8px;height:8px;background:${s.color};border-radius:2px;margin-right:6px;"></span>` +
              `<span class="muted">${s.name}:</span> <b>${valueFormatter(p.v)}</b></div>`,
          );
        });
        const t0 = series[0].values[
          Math.max(0, Math.min(series[0].values.length - 1, bisect(series[0].values, t)))
        ].t;
        const label = d3.timeFormat("%b %d, %H:%M")(t0);
        tooltip.show(
          `<div style="margin-bottom:4px"><b>${label}</b></div>${rows.join("")}`,
          event.clientX,
          event.clientY,
        );
      });
  }, [series, size.width, height, yLabel, valueFormatter, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
