import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

export interface HistSeries {
  name: string;
  color: string;
  values: number[];
}

interface Props {
  series: HistSeries[];
  bins?: number;
  height?: number;
  xLabel?: string;
}

export default function Histogram({ series, bins = 30, height = 320, xLabel }: Props) {
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
    if (!series.length) return;

    const all = series.flatMap((s) => s.values);
    if (!all.length) return;
    const xExt = d3.extent(all) as [number, number];
    const x = d3.scaleLinear().domain(xExt).nice().range([0, iw]);
    const binner = d3
      .bin<number, number>()
      .domain(x.domain() as [number, number])
      .thresholds(bins);

    const seriesBins = series.map((s) => ({
      ...s,
      bins: binner(s.values),
    }));

    const yMax = d3.max(seriesBins.flatMap((s) => s.bins.map((b) => b.length))) ?? 1;
    const y = d3.scaleLinear().domain([0, yMax]).nice().range([ih, 0]);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
    g.append("g")
      .attr("class", "grid")
      .call(
        d3
          .axisLeft(y)
          .tickSize(-iw)
          .tickFormat(() => ""),
      );
    g.append("g").attr("class", "axis").attr("transform", `translate(0,${ih})`).call(d3.axisBottom(x).ticks(6).tickFormat((d) => fmt.num(+d, 0)));
    g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(5));

    seriesBins.forEach((s) => {
      g.append("g")
        .selectAll("rect")
        .data(s.bins)
        .join("rect")
        .attr("x", (d) => x(d.x0 ?? 0) + 1)
        .attr("y", (d) => y(d.length))
        .attr("width", (d) => Math.max(0, x(d.x1 ?? 0) - x(d.x0 ?? 0) - 1))
        .attr("height", (d) => ih - y(d.length))
        .attr("fill", s.color)
        .attr("fill-opacity", 0.55)
        .on("pointerenter", (ev, d) =>
          tooltip.show(
            `<b>${s.name}</b><br>range: ${fmt.num(d.x0 ?? 0, 0)} – ${fmt.num(d.x1 ?? 0, 0)}<br>count: <b>${d.length}</b>`,
            ev.clientX,
            ev.clientY,
          ),
        )
        .on("pointermove", (ev) => tooltip.move(ev.clientX, ev.clientY))
        .on("pointerleave", () => tooltip.hide());
    });

    if (xLabel)
      svg
        .append("text")
        .attr("class", "axis-title")
        .attr("x", margin.left + iw / 2)
        .attr("y", h - 6)
        .attr("text-anchor", "middle")
        .text(xLabel);

    // Legend
    if (series.length > 1) {
      const legend = svg.append("g").attr("transform", `translate(${margin.left},${h - 22})`);
      let off = 0;
      series.forEach((s) => {
        const grp = legend.append("g").attr("transform", `translate(${off},0)`);
        grp.append("rect").attr("width", 10).attr("height", 10).attr("y", -10).attr("rx", 2).attr("fill", s.color);
        const txt = grp.append("text").attr("x", 14).attr("y", -1).attr("fill", "currentColor").text(s.name);
        off += 24 + (txt.node()?.getComputedTextLength() ?? 40);
      });
    }
  }, [series, bins, size.width, height, xLabel, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
