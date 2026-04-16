import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

export interface BarGroup {
  label: string;
  values: { name: string; value: number; color: string }[];
}

interface Props {
  groups: BarGroup[];
  height?: number;
  yLabel?: string;
  mode?: "grouped" | "diverging";
  /** If set, bars are drawn horizontally. */
  horizontal?: boolean;
  valueFormatter?: (v: number) => string;
  orderLabels?: string[];
}

export default function BarChart({
  groups,
  height = 340,
  yLabel,
  mode = "grouped",
  horizontal = false,
  valueFormatter = (v) => fmt.num(v, 1),
  orderLabels,
}: Props) {
  const { ref, size } = useContainerSize<HTMLDivElement>(height);

  useEffect(() => {
    if (!ref.current || !size.width) return;
    const margin = horizontal
      ? { top: 12, right: 20, bottom: 30, left: 140 }
      : { top: 12, right: 20, bottom: 40, left: 56 };
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

    if (!groups.length) return;
    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const labels = orderLabels ?? groups.map((g) => g.label);
    const allValues = groups.flatMap((grp) => grp.values.map((v) => v.value));
    const seriesNames = Array.from(
      new Set(groups.flatMap((grp) => grp.values.map((v) => v.name))),
    );

    if (horizontal) {
      const yScale = d3.scaleBand().domain(labels).range([0, ih]).padding(0.25);
      const min = Math.min(0, d3.min(allValues) ?? 0);
      const max = d3.max(allValues) ?? 1;
      const xScale = d3
        .scaleLinear()
        .domain([min, max])
        .nice()
        .range([0, iw]);

      g.append("g")
        .attr("class", "grid")
        .call(
          d3
            .axisBottom(xScale)
            .tickSize(ih)
            .tickFormat(() => ""),
        )
        .attr("transform", `translate(0,0)`);

      g.append("g")
        .attr("class", "axis")
        .attr("transform", `translate(0,${ih})`)
        .call(d3.axisBottom(xScale).ticks(5).tickFormat((d) => valueFormatter(+d)));
      g.append("g").attr("class", "axis").call(d3.axisLeft(yScale));

      groups.forEach((grp) => {
        const v = grp.values[0];
        if (!v) return;
        const y0 = yScale(grp.label)!;
        g.append("rect")
          .attr("x", xScale(Math.min(0, v.value)))
          .attr("y", y0)
          .attr("width", Math.abs(xScale(v.value) - xScale(0)))
          .attr("height", yScale.bandwidth())
          .attr("rx", 3)
          .attr("fill", v.color)
          .on("pointerenter", (ev) =>
            tooltip.show(
              `<b>${grp.label}</b><br><span class="muted">${v.name}:</span> <b>${valueFormatter(v.value)}</b>`,
              ev.clientX,
              ev.clientY,
            ),
          )
          .on("pointermove", (ev) => tooltip.move(ev.clientX, ev.clientY))
          .on("pointerleave", () => tooltip.hide());
      });
      if (yLabel)
        svg
          .append("text")
          .attr("class", "axis-title")
          .attr("x", margin.left + iw / 2)
          .attr("y", h - 4)
          .attr("text-anchor", "middle")
          .text(yLabel);
      return;
    }

    const x0 = d3.scaleBand().domain(labels).range([0, iw]).padding(0.2);
    const x1 = d3
      .scaleBand()
      .domain(seriesNames)
      .range([0, x0.bandwidth()])
      .padding(0.1);

    const yMin =
      mode === "diverging"
        ? d3.min(allValues) ?? 0
        : Math.min(0, d3.min(allValues) ?? 0);
    const yMax = d3.max(allValues) ?? 1;
    const y = d3
      .scaleLinear()
      .domain([yMin * 1.05, yMax * 1.08 || 1])
      .nice()
      .range([ih, 0]);

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
      .call(d3.axisBottom(x0).tickSizeOuter(0));
    g.append("g")
      .attr("class", "axis")
      .call(d3.axisLeft(y).ticks(5).tickFormat((d) => valueFormatter(+d)));

    if (mode === "diverging") {
      g.append("line")
        .attr("x1", 0)
        .attr("x2", iw)
        .attr("y1", y(0))
        .attr("y2", y(0))
        .attr("stroke", "#334155")
        .attr("stroke-dasharray", "2 3");
    }

    groups.forEach((grp) => {
      const gx = x0(grp.label)!;
      grp.values.forEach((v) => {
        const bx = x1(v.name)!;
        const y0v = v.value >= 0 ? y(v.value) : y(0);
        const bh = Math.abs(y(v.value) - y(0));
        g.append("rect")
          .attr("x", gx + bx)
          .attr("y", y0v)
          .attr("width", x1.bandwidth())
          .attr("height", bh)
          .attr("rx", 3)
          .attr("fill", v.color)
          .on("pointerenter", (ev) =>
            tooltip.show(
              `<b>${grp.label}</b><br><span class="muted">${v.name}:</span> <b>${valueFormatter(v.value)}</b>`,
              ev.clientX,
              ev.clientY,
            ),
          )
          .on("pointermove", (ev) => tooltip.move(ev.clientX, ev.clientY))
          .on("pointerleave", () => tooltip.hide());
      });
    });

    if (yLabel)
      svg
        .append("text")
        .attr("class", "axis-title")
        .attr("transform", `translate(14,${margin.top + ih / 2}) rotate(-90)`)
        .attr("text-anchor", "middle")
        .text(yLabel);

    if (seriesNames.length > 1) {
      const legend = svg
        .append("g")
        .attr("transform", `translate(${margin.left},${h - 4})`);
      let off = 0;
      const nameColors = new Map<string, string>();
      groups.forEach((grp) => grp.values.forEach((v) => nameColors.set(v.name, v.color)));
      seriesNames.forEach((name) => {
        const color = nameColors.get(name) ?? "#888";
        const grp = legend.append("g").attr("transform", `translate(${off},0)`);
        grp
          .append("rect")
          .attr("width", 10)
          .attr("height", 10)
          .attr("y", -10)
          .attr("rx", 2)
          .attr("fill", color);
        const txt = grp
          .append("text")
          .attr("x", 14)
          .attr("y", -1)
          .attr("fill", "currentColor")
          .text(name);
        off += 24 + (txt.node()?.getComputedTextLength() ?? 40);
      });
    }
  }, [groups, size.width, height, yLabel, mode, horizontal, valueFormatter, orderLabels, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
