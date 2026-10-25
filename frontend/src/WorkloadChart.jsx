import React from 'react';
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

function AxisTick({ x, y, payload, textAnchor }) {
  return <text x={x} y={y} dy=".35em" textAnchor={textAnchor} className="chart-axis-tick">{payload.value}</text>;
}
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip">{label}: {payload[0].value} cases</div>;
}
export default function WorkloadChart({ data }) {
  if (!data.length) return <p className="empty-state">No bureau workload to display.</p>;
  return <>
    <div className="chart-frame" role="img" aria-label={'Bureau case totals. ' + data.map(row => row.bureau + ': ' + row.total).join(', ')}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" accessibilityLayer>
          <CartesianGrid horizontal={false} stroke="var(--color-border)" />
          <XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} tick={<AxisTick />} />
          <YAxis type="category" dataKey="bureau" axisLine={false} tickLine={false} tick={<AxisTick />} />
          <Tooltip cursor={false} content={<ChartTooltip />} />
          <Bar dataKey="total" name="Cases" fill="var(--color-accent)" isAnimationActive={false}>
            <LabelList dataKey="total" position="insideRight" fill="var(--color-text)" className="chart-value" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
    <table className="sr-only"><caption>Bureau workload data</caption><thead><tr><th scope="col">Bureau</th><th scope="col" className="numeric">Cases</th></tr></thead><tbody>{data.map(row => <tr key={row.bureau}><th scope="row">{row.bureau}</th><td className="numeric">{row.total}</td></tr>)}</tbody></table>
    <p className="chart-caption">All cases across all bureaus, including disposed records.</p>
  </>;
}
