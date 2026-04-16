import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

interface Cell {
  row: string;
  col: string;
  value: number;
}

interface Props {
  data: Cell[];
  rowOrder?: string[];
  colOrder?: string[];
  colorScheme?: "reds" | "blues" | "yellows" | "rdylgn";
  diverging?: boolean;
  height?: number;
  showValues?: boolean;
  valueFormatter?: (v: number) => string;
  unit?: string;
}

export default function Heatmap({
  data,
  rowOrder,
  colOrder,
  colorScheme = "reds",
  diverging = false,
  height = 320,
  showValues = false,
  valueFormatter = (v) => fmt.num(v, 1),
  unit = "",
}: Props) {
  const { ref, size } = useContainerSize<HTMLDivElement>(height);

  useEffect(() => {
    if (!ref.current || !size.width) return;
    const margin = { top: 16, right: 20, bottom: 28, left: 80 };
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
    if (!data.length) return;

    const rows = rowOrder ?? Array.from(new Set(data.map((d) => d.row)));
    const cols = colOrder ?? Array.from(new Set(data.map((d) => d.col)));

    const x = d3.scaleBand<string>().domain(cols).range([0, iw]).padding(0.03);
    const y = d3.scaleBand<string>().domain(rows).range([0, ih]).padding(0.03);

    const values = data.map((d) => d.value);
    const vMin = d3.min(values) ?? 0;
    const vMax = d3.max(values) ?? 1;
    const interp =
      colorScheme === "blues"
        ? d3.interpolateBlues
        : colorScheme === "yellows"
          ? d3.interpolateYlOrBr
          : colorScheme === "rdylgn"
            ? d3.interpolateRdYlGn
            : d3.interpolateReds;

    const color = diverging
      ? d3
          .scaleDiverging((t) => interp(t))
          .domain([Math.min(0, vMin), 0, Math.max(0, vMax)])
      : d3.scaleSequential(interp).domain([vMin, vMax]);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    g.append("g")
      .attr("class", "axis")
      .attr("transform", `translate(0,${ih})`)
      .call(d3.axisBottom(x).tickSizeOuter(0));
    g.append("g").attr("class", "axis").call(d3.axisLeft(y).tickSizeOuter(0));

    g.selectAll("rect.cell")
      .data(data)
      .join("rect")
      .attr("class", "cell")
      .attr("x", (d) => x(d.col)!)
      .attr("y", (d) => y(d.row)!)
      .attr("width", x.bandwidth())
      .attr("height", y.bandwidth())
      .attr("rx", 3)
      .attr("fill", (d) => color(d.value) as string)
      .on("pointerenter", (ev, d) =>
        tooltip.show(
          `<b>${d.row} · ${d.col}</b><br><span class="muted">value:</span> <b>${valueFormatter(d.value)}${unit ? ` ${unit}` : ""}</b>`,
          ev.clientX,
          ev.clientY,
        ),
      )
      .on("pointermove", (ev) => tooltip.move(ev.clientX, ev.clientY))
      .on("pointerleave", () => tooltip.hide());

    if (showValues) {
      g.selectAll("text.cell")
        .data(data)
        .join("text")
        .attr("class", "cell")
        .attr("x", (d) => (x(d.col) ?? 0) + x.bandwidth() / 2)
        .attr("y", (d) => (y(d.row) ?? 0) + y.bandwidth() / 2 + 4)
        .attr("text-anchor", "middle")
        .attr("fill", (d) => {
          const rgb = d3.color(color(d.value) as string)?.rgb();
          if (!rgb) return "#e5e7eb";
          const lum = 0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b;
          return lum > 140 ? "#0b0f14" : "#e5e7eb";
        })
        .attr("font-size", 11)
        .attr("font-weight", 600)
        .text((d) => valueFormatter(d.value));
    }
  }, [data, rowOrder, colOrder, colorScheme, diverging, size.width, height, showValues, valueFormatter, unit, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
