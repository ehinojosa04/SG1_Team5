import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

export interface LineSeries {
  name: string;
  color: string;
  width?: number;
  dash?: string;
  values: { x: number; y: number }[];
}

interface Props {
  series: LineSeries[];
  height?: number;
  xLabel?: string;
  yLabel?: string;
  xTickFormat?: (v: number) => string;
  yTickFormat?: (v: number) => string;
  xDomain?: [number, number];
  markers?: boolean;
  zeroLine?: boolean;
}

export default function LineChart({
  series,
  height = 360,
  xLabel,
  yLabel,
  xTickFormat = (v) => String(v),
  yTickFormat = (v) => fmt.num(v, 2),
  xDomain,
  markers = true,
  zeroLine = false,
}: Props) {
  const { ref, size } = useContainerSize<HTMLDivElement>(height);

  useEffect(() => {
    if (!ref.current || !size.width) return;
    const margin = { top: 18, right: 20, bottom: 44, left: 56 };
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

    if (!series.length) return;
    const all = series.flatMap((s) => s.values);
    if (!all.length) return;

    const xMin = xDomain?.[0] ?? (d3.min(all, (d) => d.x) ?? 0);
    const xMax = xDomain?.[1] ?? (d3.max(all, (d) => d.x) ?? 1);
    const yMin = Math.min(0, d3.min(all, (d) => d.y) ?? 0);
    const yMax = d3.max(all, (d) => d.y) ?? 1;

    const x = d3.scaleLinear().domain([xMin, xMax]).range([0, iw]);
    const y = d3
      .scaleLinear()
      .domain([yMin, yMax * 1.08 || 1])
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
          .ticks(Math.max(2, Math.floor(iw / 60)))
          .tickFormat((d) => xTickFormat(+d)),
      );
    g.append("g")
      .attr("class", "axis")
      .call(d3.axisLeft(y).ticks(5).tickFormat((d) => yTickFormat(+d)));

    if (zeroLine) {
      g.append("line")
        .attr("x1", 0)
        .attr("x2", iw)
        .attr("y1", y(0))
        .attr("y2", y(0))
        .attr("stroke", "#334155")
        .attr("stroke-dasharray", "2 3");
    }

    if (xLabel)
      svg
        .append("text")
        .attr("class", "axis-title")
        .attr("x", margin.left + iw / 2)
        .attr("y", h - 6)
        .attr("text-anchor", "middle")
        .text(xLabel);
    if (yLabel)
      svg
        .append("text")
        .attr("class", "axis-title")
        .attr("transform", `translate(14,${margin.top + ih / 2}) rotate(-90)`)
        .attr("text-anchor", "middle")
        .text(yLabel);

    const line = d3
      .line<{ x: number; y: number }>()
      .x((d) => x(d.x))
      .y((d) => y(d.y))
      .curve(d3.curveMonotoneX);

    for (const s of series) {
      g.append("path")
        .datum(s.values)
        .attr("fill", "none")
        .attr("stroke", s.color)
        .attr("stroke-width", s.width ?? 2)
        .attr("stroke-dasharray", s.dash || null)
        .attr("d", line);
      if (markers) {
        g.append("g")
          .selectAll("circle")
          .data(s.values)
          .join("circle")
          .attr("cx", (d) => x(d.x))
          .attr("cy", (d) => y(d.y))
          .attr("r", 2.5)
          .attr("fill", s.color)
          .attr("stroke", "#0b0f14")
          .attr("stroke-width", 0.8);
      }
    }

    // Legend
    if (series.length > 1 || series[0].name) {
      const legend = svg
        .append("g")
        .attr("transform", `translate(${margin.left},${h - 4})`);
      let offset = 0;
      series.forEach((s) => {
        const grp = legend
          .append("g")
          .attr("transform", `translate(${offset},0)`);
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
    }

    // Hover
    const focus = g.append("g").style("display", "none");
    focus
      .append("line")
      .attr("y1", 0)
      .attr("y2", ih)
      .attr("stroke", "#f59e0b")
      .attr("stroke-dasharray", "2 3")
      .attr("opacity", 0.5);

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
        const xi = Math.round(x.invert(mx));
        focus.attr("transform", `translate(${x(xi)},0)`);
        const rows = series
          .map((s) => {
            const p = s.values.find((v) => v.x === xi);
            if (!p) return "";
            return `<div><span style="display:inline-block;width:8px;height:8px;background:${s.color};border-radius:2px;margin-right:6px;"></span><span class="muted">${s.name}:</span> <b>${yTickFormat(p.y)}</b></div>`;
          })
          .filter(Boolean)
          .join("");
        tooltip.show(
          `<div style="margin-bottom:4px"><b>${xTickFormat(xi)}</b></div>${rows}`,
          event.clientX,
          event.clientY,
        );
      });
  }, [series, size.width, height, xLabel, yLabel, xTickFormat, yTickFormat, xDomain, markers, zeroLine, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
