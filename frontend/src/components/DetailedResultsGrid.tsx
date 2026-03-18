import type { CustomerSegmentResult } from '../types/segment';

interface DetailedResultsGridProps {
  results: CustomerSegmentResult[];
  loading: boolean;
  activeSegment: string | null;
  expectedLabels: Record<string, string>;
}

function ResultsSkeleton() {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="skeleton h-64 rounded-[24px]" />
      ))}
    </div>
  );
}

export function DetailedResultsGrid({ results, loading, activeSegment, expectedLabels }: DetailedResultsGridProps) {
  if (loading) {
    return <ResultsSkeleton />;
  }

  if (!results.length) {
    return (
      <div className="rounded-[24px] border border-dashed border-line bg-white/50 px-6 py-12 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-copper/10 text-2xl text-copper">S</div>
        <h3 className="mt-4 text-lg font-semibold text-ink">No customer results yet</h3>
        <p className="mt-2 text-sm leading-6 text-muted">
          Run the analysis to populate the detailed results grid with customer email, core insight, and recommended actions.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {results.map((item) => (
        <article key={item.customer_id} className="rounded-[24px] border border-line bg-white/75 p-5 shadow-sm shadow-black/5">
          <div className="grid gap-5 xl:grid-cols-[0.78fr_1.22fr]">
            <div className="rounded-[20px] bg-[#fcf8f1] p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Customer</p>
              <h3 className="mt-2 text-lg font-semibold text-ink">{item.email ?? 'No email available'}</h3>
              <p className="mt-1 font-mono text-xs leading-5 text-muted">{item.customer_id}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-copper/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-copper">
                  {item.segment.segment_name}
                </span>
                <span className="rounded-full bg-black/5 px-3 py-1 text-xs text-muted">{item.segment_label}</span>
                {item.churn?.risk_level ? (
                  <span className="rounded-full bg-red-900/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-red-700">
                    churn {item.churn.risk_level}
                  </span>
                ) : null}
                {item.sentiment ? (
                  <span className="rounded-full bg-emerald-900/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-800">
                    {item.sentiment}
                  </span>
                ) : null}
              </div>
              {expectedLabels[item.customer_id] ? (
                <p
                  className={`mt-4 text-xs ${
                    expectedLabels[item.customer_id] === item.segment_label ? 'text-emerald-700' : 'text-red-700'
                  }`}
                >
                  Expected {expectedLabels[item.customer_id]} |{' '}
                  {expectedLabels[item.customer_id] === item.segment_label ? 'match' : 'mismatch'}
                </p>
              ) : null}
            </div>

            <div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Core Insight</p>
                  <p className="mt-2 text-sm leading-7 text-ink">{item.core_insight ?? 'No core insight available.'}</p>
                  {item.churn_risk !== null || item.sentiment_detail?.score !== undefined ? (
                    <p className="mt-3 text-xs text-muted">
                      {item.churn_risk !== null ? `Churn ${Math.round(item.churn_risk * 100)}%` : 'Churn n/a'}
                      {' | '}
                      {item.sentiment_detail?.score !== undefined
                        ? `Sentiment score ${item.sentiment_detail.score?.toFixed(2)}`
                        : 'Sentiment score n/a'}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-col items-start gap-2 sm:items-end">
                  <span className="rounded-full bg-copper/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-copper">
                    {activeSegment ? `Filtered by ${activeSegment}` : 'Detailed result'}
                  </span>
                </div>
              </div>

              {item.sentiment_detail?.topics?.length ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {item.sentiment_detail.topics.map((topic) => (
                    <span key={topic} className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs text-muted">
                      topic {topic}
                    </span>
                  ))}
                </div>
              ) : null}

              {item.top_signals.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {item.top_signals.map((signal) => (
                    <span key={signal} className="rounded-full bg-black/5 px-3 py-1 text-xs text-muted">
                      {signal}
                    </span>
                  ))}
                </div>
              ) : null}

              <div className="mt-5">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Recommendations</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.recommendations.length > 0 ? (
                    item.recommendations.map((recommendation) => (
                      <span
                        key={recommendation}
                        className="rounded-full border border-copper/15 bg-copper/10 px-3 py-2 text-xs leading-5 text-copper"
                      >
                        {recommendation}
                      </span>
                    ))
                  ) : (
                    <span className="rounded-full bg-black/5 px-3 py-2 text-xs text-muted">No recommendations</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
