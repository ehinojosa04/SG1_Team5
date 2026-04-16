import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

export interface ScatterPoint {
  x: number;
  y: number;
  size?: number;
  color: string;
  label?: string;
}

interface Props {
  points: ScatterPoint[];
  height?: number;
  xLabel?: string;
  yLabel?: string;
  xFmt?: (v: number) => string;
  yFmt?: (v: number) => string;
}

export default function ScatterPlot({
  points,
  height = 360,
  xLabel,
  yLabel,
  xFmt = (v) => fmt.num(v, 0),
  yFmt = (v) => fmt.num(v, 0),
}: Props) {
  const { ref, size } = useContainerSize<HTMLDivElement>(height);

  useEffect(() => {
    if (!ref.current || !size.width) return;
    const margin = { top: 16, right: 20, bottom: 44, left: 56 };
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
    if (!points.length) return;

    const xExt = d3.extent(points, (d) => d.x) as [number, number];
    const yExt = d3.extent(points, (d) => d.y) as [number, number];
    const x = d3.scaleLinear().domain(xExt).nice().range([0, iw]);
    const y = d3.scaleLinear().domain([Math.min(0, yExt[0]), yExt[1]]).nice().range([ih, 0]);
    const sMax = d3.max(points, (d) => d.size ?? 1) ?? 1;
    const sScale = d3.scaleSqrt().domain([0, sMax]).range([3, 18]);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
    g.append("g")
      .attr("class", "grid")
      .call(
        d3
          .axisLeft(y)
          .tickSize(-iw)
          .tickFormat(() => ""),
      );
    g.append("g").attr("class", "axis").attr("transform", `translate(0,${ih})`).call(d3.axisBottom(x).ticks(6).tickFormat((d) => xFmt(+d)));
    g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5).tickFormat((d) => yFmt(+d)));

    g.append("g")
      .selectAll("circle")
      .data(points)
      .join("circle")
      .attr("cx", (d) => x(d.x))
      .attr("cy", (d) => y(d.y))
      .attr("r", (d) => sScale(d.size ?? 1))
      .attr("fill", (d) => d.color)
      .attr("fill-opacity", 0.75)
      .attr("stroke", "#0b0f14")
      .attr("stroke-width", 1)
      .on("pointerenter", (ev, d) =>
        tooltip.show(
          `${d.label ? `<b>${d.label}</b><br>` : ""}` +
            `<span class="muted">${xLabel ?? "x"}:</span> ${xFmt(d.x)}<br>` +
            `<span class="muted">${yLabel ?? "y"}:</span> ${yFmt(d.y)}`,
          ev.clientX,
          ev.clientY,
        ),
      )
      .on("pointermove", (ev) => tooltip.move(ev.clientX, ev.clientY))
      .on("pointerleave", () => tooltip.hide());

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
  }, [points, size.width, height, xLabel, yLabel, xFmt, yFmt, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
