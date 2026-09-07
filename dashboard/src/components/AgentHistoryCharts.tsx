import {
  Brush,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { HistoryChartPoint } from '../utils/history'
import styles from '../pages/Pages.module.css'

const CHARTS = [
  { key: 'cpu', title: 'CPU', color: '#2563eb', unit: '%' },
  { key: 'memory', title: 'Memory', color: '#7c3aed', unit: '%' },
  { key: 'disk', title: 'Disk', color: '#0f766e', unit: '%' },
  { key: 'temperature', title: 'Temperature', color: '#c2410c', unit: '°C' },
] as const

interface AgentHistoryChartsProps {
  data: HistoryChartPoint[]
}

export function AgentHistoryCharts({ data }: AgentHistoryChartsProps) {
  return (
    <section className={styles.chartGrid} aria-label="Metric history charts">
      {CHARTS.map((chart) => (
        <article className={styles.chartPanel} key={chart.key}>
          <h3 className={styles.groupTitle}>{chart.title}</h3>
          <div className={styles.chartSurface}>
            <ResponsiveContainer
              width="100%"
              height={256}
              initialDimension={{ width: 800, height: 256 }}
            >
              <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis dataKey="label" minTickGap={24} />
                <YAxis
                  domain={chart.key === 'temperature' ? ['auto', 'auto'] : [0, 100]}
                  unit={chart.unit === '%' ? '%' : undefined}
                />
                <Tooltip />
                <Legend />
                <Brush dataKey="label" height={18} stroke={chart.color} />
                <Line
                  type="monotone"
                  dataKey={chart.key}
                  name={chart.title}
                  stroke={chart.color}
                  dot={false}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>
      ))}
    </section>
  )
}
