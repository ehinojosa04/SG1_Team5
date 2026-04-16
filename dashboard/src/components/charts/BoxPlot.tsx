import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

interface Box {
  label: string;
  values: number[];
  color: string;
}

interface Props {
  boxes: Box[];
  height?: number;
  yLabel?: string;
}

export default function BoxPlot({ boxes, height = 340, yLabel }: Props) {
  const { ref, size } = useContainerSize<HTMLDivElement>(height);

  useEffect(() => {
    if (!ref.current || !size.width) return;
    const margin = { top: 12, right: 20, bottom: 32, left: 56 };
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
    if (!boxes.length) return;

    const stats = boxes.map((b) => {
      const vs = b.values.slice().sort(d3.ascending);
      const q1 = d3.quantile(vs, 0.25) ?? 0;
      const med = d3.quantile(vs, 0.5) ?? 0;
      const q3 = d3.quantile(vs, 0.75) ?? 0;
      const iqr = q3 - q1;
      const lo = Math.max(vs[0] ?? 0, q1 - 1.5 * iqr);
      const hi = Math.min(vs[vs.length - 1] ?? 0, q3 + 1.5 * iqr);
      return { ...b, q1, med, q3, lo, hi, min: vs[0] ?? 0, max: vs[vs.length - 1] ?? 0 };
    });

    const x = d3.scaleBand<string>().domain(boxes.map((b) => b.label)).range([0, iw]).padding(0.35);
    const yMin = Math.min(0, d3.min(stats, (s) => s.lo) ?? 0);
    const yMax = d3.max(stats, (s) => s.hi) ?? 1;
    const y = d3.scaleLinear().domain([yMin, yMax * 1.05]).nice().range([ih, 0]);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
    g.append("g")
      .attr("class", "grid")
      .call(
        d3
          .axisLeft(y)
          .tickSize(-iw)
          .tickFormat(() => ""),
      );
    g.append("g").attr("class", "axis").attr("transform", `translate(0,${ih})`).call(d3.axisBottom(x).tickSizeOuter(0));
    g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5).tickFormat((d) => fmt.num(+d, 0)));

    stats.forEach((s) => {
      const cx = (x(s.label) ?? 0) + x.bandwidth() / 2;
      const bw = x.bandwidth();
      // whiskers
      g.append("line")
        .attr("x1", cx)
        .attr("x2", cx)
        .attr("y1", y(s.lo))
        .attr("y2", y(s.hi))
        .attr("stroke", s.color)
        .attr("stroke-width", 1.5);
      [s.lo, s.hi].forEach((v) =>
        g.append("line")
          .attr("x1", cx - bw / 4)
          .attr("x2", cx + bw / 4)
          .attr("y1", y(v))
          .attr("y2", y(v))
          .attr("stroke", s.color)
          .attr("stroke-width", 1.5),
      );
      // box
      g.append("rect")
        .attr("x", cx - bw / 2)
        .attr("y", y(s.q3))
        .attr("width", bw)
        .attr("height", Math.max(1, y(s.q1) - y(s.q3)))
        .attr("fill", s.color)
        .attr("fill-opacity", 0.3)
        .attr("stroke", s.color)
        .attr("stroke-width", 1.4)
        .attr("rx", 3)
        .on("pointerenter", (ev) =>
          tooltip.show(
            `<b>${s.label}</b><br>` +
              `<span class="muted">median:</span> <b>${fmt.num(s.med, 1)}</b><br>` +
              `<span class="muted">IQR:</span> ${fmt.num(s.q1, 1)} – ${fmt.num(s.q3, 1)}<br>` +
              `<span class="muted">min/max:</span> ${fmt.num(s.min, 1)} / ${fmt.num(s.max, 1)}`,
            ev.clientX,
            ev.clientY,
          ),
        )
        .on("pointermove", (ev) => tooltip.move(ev.clientX, ev.clientY))
        .on("pointerleave", () => tooltip.hide());
      // median line
      g.append("line")
        .attr("x1", cx - bw / 2)
        .attr("x2", cx + bw / 2)
        .attr("y1", y(s.med))
        .attr("y2", y(s.med))
        .attr("stroke", "#fff")
        .attr("stroke-width", 2);
    });

    if (yLabel)
      svg
        .append("text")
        .attr("class", "axis-title")
        .attr("transform", `translate(14,${margin.top + ih / 2}) rotate(-90)`)
        .attr("text-anchor", "middle")
        .text(yLabel);
  }, [boxes, size.width, height, yLabel, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
