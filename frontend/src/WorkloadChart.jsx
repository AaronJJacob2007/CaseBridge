import React from 'react';
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function WorkloadChart({ data }) {
  if (!data.length) return <p className="empty-state">No bureau workload to display.</p>;
  return <>
    <div className="chart-frame" role="img" aria-label={'Bureau case totals. ' + data.map((row) => row.bureau + ': ' + row.total).join(', ')}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 16, right: 40, left: 0, bottom: 4 }} accessibilityLayer>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e9ef" />
          <XAxis type="number" allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#62768a', fontSize: 12 }} />
          <YAxis type="category" dataKey="bureau" width={62} axisLine={false} tickLine={false} tick={{ fill: '#17344d', fontSize: 13 }} />
          <Tooltip cursor={{ fill: '#eff7f7' }} contentStyle={{ borderRadius: 10, border: '1px solid #dce6ec' }} />
          <Bar dataKey="total" name="Cases" fill="#148b87" radius={[0, 6, 6, 0]} barSize={30} isAnimationActive={false}>
            <LabelList dataKey="total" position="right" fill="#17344d" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
    <table className="sr-only"><caption>Bureau workload data</caption><thead><tr><th scope="col">Bureau</th><th scope="col">Cases</th></tr></thead><tbody>{data.map((row) => <tr key={row.bureau}><th scope="row">{row.bureau}</th><td>{row.total}</td></tr>)}</tbody></table>
    <p className="chart-caption">Workload reflects the complete register across all bureaus.</p>
  </>;
}
