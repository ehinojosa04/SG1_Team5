import { useEffect } from "react";
import * as d3 from "d3";
import { fmt, tooltip, useContainerSize } from "./useChart";

interface Props {
  data: { t: Date; pos: number; neg: number }[];
  posLabel: string;
  negLabel: string;
  posColor: string;
  negColor: string;
  height?: number;
  yLabel?: string;
}

export default function DivergentBars({
  data,
  posLabel,
  negLabel,
  posColor,
  negColor,
  height = 320,
  yLabel,
}: Props) {
  const { ref, size } = useContainerSize<HTMLDivElement>(height);

  useEffect(() => {
    if (!ref.current || !size.width) return;
    const margin = { top: 16, right: 20, bottom: 28, left: 56 };
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

    const xExtent = d3.extent(data, (d) => d.t) as [Date, Date];
    const yMax = d3.max(data, (d) => d.pos) ?? 1;
    const yMin = -(d3.max(data, (d) => d.neg) ?? 1);

    const x = d3.scaleTime().domain(xExtent).range([0, iw]);
    const y = d3.scaleLinear().domain([yMin, yMax]).nice().range([ih, 0]);
    const bw = Math.max(1, iw / data.length - 1);

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
      .call(d3.axisLeft(y).ticks(5).tickFormat((d) => fmt.num(+d, 0)));

    g.append("line")
      .attr("x1", 0)
      .attr("x2", iw)
      .attr("y1", y(0))
      .attr("y2", y(0))
      .attr("stroke", "#334155");

    const mk = (
      getValue: (d: { pos: number; neg: number }) => number,
      color: string,
      name: string,
    ) =>
      g
        .append("g")
        .selectAll("rect")
        .data(data)
        .join("rect")
        .attr("x", (d) => x(d.t) - bw / 2)
        .attr("y", (d) => (getValue(d) >= 0 ? y(getValue(d)) : y(0)))
        .attr("width", bw)
        .attr("height", (d) => Math.abs(y(getValue(d)) - y(0)))
        .attr("fill", color)
        .on("pointerenter", (ev, d) =>
          tooltip.show(
            `<b>${d3.timeFormat("%b %d, %H:%M")(d.t)}</b><br>` +
              `<span class="muted">${name}:</span> <b>${fmt.num(Math.abs(getValue(d)), 1)}</b>`,
            ev.clientX,
            ev.clientY,
          ),
        )
        .on("pointermove", (ev) => tooltip.move(ev.clientX, ev.clientY))
        .on("pointerleave", () => tooltip.hide());

    mk((d) => d.pos, posColor, posLabel);
    mk((d) => -d.neg, negColor, negLabel);

    if (yLabel)
      svg
        .append("text")
        .attr("class", "axis-title")
        .attr("x", margin.left)
        .attr("y", 12)
        .text(yLabel);

    // Legend
    const legend = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${h - 2})`);
    [
      { name: posLabel, color: posColor },
      { name: negLabel, color: negColor },
    ].forEach((s, i) => {
      const grp = legend
        .append("g")
        .attr("transform", `translate(${i * 110},-10)`);
      grp
        .append("rect")
        .attr("width", 10)
        .attr("height", 10)
        .attr("rx", 2)
        .attr("fill", s.color);
      grp
        .append("text")
        .attr("x", 14)
        .attr("y", 9)
        .attr("fill", "currentColor")
        .text(s.name);
    });
  }, [data, posLabel, negLabel, posColor, negColor, size.width, height, yLabel, ref]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
