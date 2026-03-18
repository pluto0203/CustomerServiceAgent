interface PayloadEditorProps {
  value: string;
  onChange: (value: string) => void;
  endpointPath: string;
  onEndpointChange: (value: string) => void;
  onLoadSample: () => void;
  onRun: () => void;
  onToggleRaw: () => void;
  loading: boolean;
}

export function PayloadEditor({
  value,
  onChange,
  endpointPath,
  onEndpointChange,
  onLoadSample,
  onRun,
  onToggleRaw,
  loading,
}: PayloadEditorProps) {
  return (
    <section className="panel-surface p-6 lg:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-copper">Customer Behavior Agent</p>
          <h1 className="mt-2 max-w-[12ch] text-4xl font-bold leading-none text-ink lg:text-6xl">
            Segment Insights Workbench
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-muted lg:text-base">
            Paste A2A JSON, run segment analysis, then inspect segment distribution and detailed customer-level recommendations.
          </p>
        </div>

        <div className="flex flex-col gap-3 lg:w-[320px]">
          <span className="inline-flex w-fit rounded-full border border-dashed border-black/15 px-3 py-2 font-mono text-[11px] text-muted">
            Full stack mode: frontend proxies API requests inside Docker
          </span>
          <label className="text-sm text-muted" htmlFor="api-path-input">
            Endpoint path
          </label>
          <input
            id="api-path-input"
            value={endpointPath}
            onChange={(event) => onEndpointChange(event.target.value)}
            className="rounded-2xl border border-line bg-white/70 px-4 py-3 text-sm outline-none transition focus:border-copper/40 focus:ring-2 focus:ring-copper/10"
          />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onLoadSample}
          className="rounded-full bg-gradient-to-br from-copper to-[#7b3214] px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-copper/20 transition hover:-translate-y-0.5"
        >
          Load Sample Payload
        </button>
        <button
          type="button"
          onClick={onRun}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-full border border-line bg-white/70 px-5 py-3 text-sm font-semibold text-ink transition hover:-translate-y-0.5 disabled:translate-y-0 disabled:opacity-70"
        >
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-copper/30 border-t-copper" />
              Running...
            </>
          ) : (
            'Run Analysis'
          )}
        </button>
        <button
          type="button"
          onClick={onToggleRaw}
          className="rounded-full border border-line bg-white/70 px-5 py-3 text-sm font-semibold text-ink transition hover:-translate-y-0.5"
        >
          Toggle Raw JSON
        </button>
      </div>

      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-ink">Request Payload</h2>
          <span className="font-mono text-xs text-muted">{value.length} chars</span>
        </div>
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          spellCheck={false}
          className="min-h-[400px] w-full rounded-[24px] border border-black/5 bg-[#1f1610] px-5 py-4 font-mono text-sm leading-6 text-[#f5e7d4] outline-none transition focus:border-copper/40 focus:ring-2 focus:ring-copper/10 lg:min-h-[500px]"
        />
      </div>
    </section>
  );
}
