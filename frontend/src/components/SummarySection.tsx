import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

import type { AnalysisPayload, SegmentDistribution } from '../types/segment';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

interface SummarySectionProps {
  payload: AnalysisPayload | null;
  loading: boolean;
  activeSegment: string | null;
  onSegmentToggle: (segment: string) => void;
  responseCode: string;
}

const chartPalette = ['#9f4b1d', '#c56b31', '#d99158', '#7e8b62', '#4f6d5c', '#bfa38c', '#6f5b4b'];

function SummarySkeleton() {
  return (
    <section className="panel-surface p-6 lg:p-7">
      <div className="grid gap-3 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="skeleton h-28" />
        ))}
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="skeleton h-[280px]" />
        <div className="grid gap-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="skeleton h-16" />
          ))}
        </div>
      </div>
    </section>
  );
}

function buildChartData(distribution: SegmentDistribution) {
  const labels = Object.keys(distribution);
  const values = Object.values(distribution);

  return {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: labels.map((_, index) => chartPalette[index % chartPalette.length]),
        borderWidth: 0,
      },
    ],
  };
}

export function SummarySection({ payload, loading, activeSegment, onSegmentToggle, responseCode }: SummarySectionProps) {
  if (loading) {
    return <SummarySkeleton />;
  }

  const summaryItems = [
    { label: 'HTTP', value: responseCode || 'n/a' },
    { label: 'Records', value: payload?.record_count ?? 0 },
    { label: 'Succeeded', value: payload?.records_succeeded ?? 0 },
    { label: 'Workflow', value: payload?.workflow_run_id ?? 'n/a' },
  ];

  const distribution = payload?.segment_distribution ?? {};
  const distributionEntries = Object.entries(distribution);
  const hasDistribution = distributionEntries.length > 0;

  return (
    <section className="panel-surface p-6 lg:p-7">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-ink">Summary</h2>
          <p className="mt-1 text-sm text-muted">Run overview, segment mix, and interactive segment filters.</p>
        </div>
        <span className={`status-pill ${payload ? 'status-success' : 'status-neutral'}`}>
          {payload?.status ?? 'no data'}
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {summaryItems.map((item) => (
          <article key={item.label} className="rounded-[22px] border border-line bg-white/75 p-4">
            <span className="text-xs uppercase tracking-[0.12em] text-muted">{item.label}</span>
            <strong className="mt-3 block break-all text-2xl font-semibold text-ink">{item.value}</strong>
          </article>
        ))}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="rounded-[26px] border border-line bg-white/75 p-4 lg:p-5">
          <div className="mb-3 flex items-center justify-between gap-4">
            <h3 className="text-base font-semibold text-ink">Segment Visualization</h3>
            <span className="font-mono text-xs text-muted">{distributionEntries.length} groups</span>
          </div>
          {hasDistribution ? (
            <div className="mx-auto max-w-[360px]">
              <Doughnut
                data={buildChartData(distribution)}
                options={{
                  responsive: true,
                  maintainAspectRatio: true,
                  plugins: {
                    legend: {
                      position: 'bottom',
                      labels: {
                        usePointStyle: true,
                        boxWidth: 10,
                        color: '#6d6258',
                        font: { family: 'IBM Plex Mono', size: 11 },
                      },
                    },
                  },
                }}
              />
            </div>
          ) : (
            <div className="empty-state rounded-[22px] border border-dashed border-line px-4 py-10 text-sm text-muted">
              No response yet. Run the analysis to see segment distribution.
            </div>
          )}
        </div>

        <div className="rounded-[26px] border border-line bg-white/75 p-4 lg:p-5">
          <div className="mb-3 flex items-center justify-between gap-4">
            <h3 className="text-base font-semibold text-ink">Interactive Segment Filters</h3>
            <span className="font-mono text-xs text-muted">
              {activeSegment ? `filter: ${activeSegment}` : 'showing all'}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {hasDistribution ? (
              distributionEntries.map(([segment, count]) => {
                const isActive = activeSegment === segment;
                return (
                  <button
                    key={segment}
                    type="button"
                    onClick={() => onSegmentToggle(segment)}
                    className={`rounded-[22px] border px-4 py-4 text-left transition ${
                      isActive
                        ? 'border-copper/40 bg-copper/10 shadow-lg shadow-copper/10'
                        : 'border-line bg-white/70 hover:border-copper/30 hover:bg-white'
                    }`}
                  >
                    <span className="block font-mono text-[11px] uppercase tracking-[0.14em] text-muted">{segment}</span>
                    <strong className="mt-2 block text-3xl font-semibold text-ink">{count}</strong>
                    <span className="mt-3 inline-flex rounded-full bg-black/5 px-3 py-1 text-xs text-muted">
                      {isActive ? 'Click to clear filter' : 'Click to filter details'}
                    </span>
                  </button>
                );
              })
            ) : (
              <div className="empty-state rounded-[22px] border border-dashed border-line px-4 py-10 text-sm text-muted sm:col-span-2">
                Segment buttons will appear after the first successful run.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
