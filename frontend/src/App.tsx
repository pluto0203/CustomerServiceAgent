import { useEffect, useMemo, useState } from 'react';

import { DetailedResultsGrid } from './components/DetailedResultsGrid';
import { PayloadEditor } from './components/PayloadEditor';
import { SummarySection } from './components/SummarySection';
import type { AnalysisPayload, AnalysisResponse, CustomerSegmentResult } from './types/segment';

const SAMPLE_URL = '/segment-insights/sample-payload.json';
const EXPECTED_URL = '/segment-insights/expected-labels.json';

export default function App() {
  const [payloadText, setPayloadText] = useState('');
  const [endpointPath, setEndpointPath] = useState('/api/v1/agent/input/sync');
  const [loading, setLoading] = useState(false);
  const [rawVisible, setRawVisible] = useState(false);
  const [rawOutput, setRawOutput] = useState('');
  const [requestState, setRequestState] = useState<'idle' | 'ready' | 'running' | 'success' | 'error'>('idle');
  const [responseCode, setResponseCode] = useState('no response');
  const [analysisPayload, setAnalysisPayload] = useState<AnalysisPayload | null>(null);
  const [expectedLabels, setExpectedLabels] = useState<Record<string, string>>({});
  const [activeSegment, setActiveSegment] = useState<string | null>(null);

  useEffect(() => {
    void loadSample();
  }, []);

  const detailedResults = useMemo<CustomerSegmentResult[]>(() => {
    const results = analysisPayload?.results ?? [];
    if (!activeSegment) {
      return results;
    }
    return results.filter((item) => item.segment_label === activeSegment);
  }, [analysisPayload, activeSegment]);

  async function loadSample() {
    try {
      const [sampleResponse, expectedResponse] = await Promise.all([fetch(SAMPLE_URL), fetch(EXPECTED_URL)]);
      if (!sampleResponse.ok) {
        throw new Error('Unable to load sample payload.');
      }

      const [samplePayload, expectedPayload] = await Promise.all([
        sampleResponse.json() as Promise<unknown>,
        expectedResponse.ok ? (expectedResponse.json() as Promise<Record<string, string>>) : Promise.resolve({}),
      ]);

      setPayloadText(JSON.stringify(samplePayload, null, 2));
      setExpectedLabels(expectedPayload);
      setRequestState('ready');
    } catch (error) {
      setRequestState('error');
      setRawVisible(true);
      setRawOutput(error instanceof Error ? error.message : String(error));
    }
  }

  async function runAnalysis() {
    let parsedPayload: unknown;
    try {
      parsedPayload = JSON.parse(payloadText);
    } catch {
      setRequestState('error');
      setResponseCode('client error');
      setRawVisible(true);
      setRawOutput('Payload is not valid JSON.');
      return;
    }

    setLoading(true);
    setRequestState('running');
    setResponseCode('waiting');
    setActiveSegment(null);

    try {
      const response = await fetch(endpointPath.trim() || '/api/v1/agent/input/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsedPayload),
      });

      const text = await response.text();
      let parsedResponse: AnalysisResponse | { raw: string };
      try {
        parsedResponse = JSON.parse(text) as AnalysisResponse;
      } catch {
        parsedResponse = { raw: text };
      }

      setRawOutput(JSON.stringify(parsedResponse, null, 2));
      setResponseCode(String(response.status));

      if (!response.ok || !('payload' in parsedResponse)) {
        setAnalysisPayload(null);
        setRequestState('error');
        setRawVisible(true);
        return;
      }

      const enrichedResults = parsedResponse.payload.results.map((item) => ({
        ...item,
        core_insight: item.core_insight ?? item.segment.summary ?? null,
        recommendations:
          item.recommendations?.length
            ? item.recommendations
            : [
                ...item.segment.recommended_actions,
                ...(item.churn?.recommended_actions ?? []),
                ...(item.sentiment_detail?.recommended_actions ?? []),
              ],
      }));

      setAnalysisPayload({
        ...parsedResponse.payload,
        results: enrichedResults.map((item) => ({
          ...item,
          email: item.email ?? null,
          top_signals: item.top_signals ?? item.segment.top_signals ?? [],
        })),
      });
      setRequestState('success');
    } catch (error) {
      setAnalysisPayload(null);
      setRequestState('error');
      setResponseCode('network');
      setRawVisible(true);
      setRawOutput(error instanceof Error ? error.message : String(error));
    } finally {
      setLoading(false);
    }
  }

  function toggleSegment(segment: string) {
    setActiveSegment((current) => (current === segment ? null : segment));
  }

  const resultCountLabel = activeSegment
    ? `${detailedResults.length} rows in ${activeSegment}`
    : `${detailedResults.length} rows`;

  return (
    <main className="mx-auto w-[min(1380px,calc(100vw-24px))] py-6 lg:py-8">
      <PayloadEditor
        value={payloadText}
        onChange={setPayloadText}
        endpointPath={endpointPath}
        onEndpointChange={setEndpointPath}
        onLoadSample={() => void loadSample()}
        onRun={() => void runAnalysis()}
        onToggleRaw={() => setRawVisible((current) => !current)}
        loading={loading}
      />

      <section className="mt-5">
        <SummarySection
          payload={analysisPayload}
          loading={loading}
          activeSegment={activeSegment}
          onSegmentToggle={toggleSegment}
          responseCode={responseCode}
        />

        <section className="panel-surface mt-5 p-6 lg:p-7">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-ink">Detailed Results Data Grid</h2>
              <p className="mt-1 text-sm text-muted">
                Email, assigned segment, churn risk, sentiment, and recommendations for each customer.
              </p>
            </div>
            <span
              className={`status-pill ${
                requestState === 'error'
                  ? 'status-error'
                  : requestState === 'success'
                    ? 'status-success'
                    : requestState === 'running'
                      ? 'status-warning'
                      : 'status-neutral'
              }`}
            >
              {resultCountLabel}
            </span>
          </div>

          <div className="mt-5">
            <DetailedResultsGrid
              results={detailedResults}
              loading={loading}
              activeSegment={activeSegment}
              expectedLabels={expectedLabels}
            />
          </div>
        </section>
      </section>

      <section className="panel-surface mt-5 p-6 lg:p-7">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-ink">Raw Response</h2>
            <p className="mt-1 text-sm text-muted">Inspect the exact API response while validating data contracts.</p>
          </div>
          <span className={`status-pill ${rawVisible ? 'status-success' : 'status-neutral'}`}>
            {rawVisible ? 'visible' : 'hidden'}
          </span>
        </div>
        {rawVisible ? (
          <pre className="mt-5 min-h-[220px] overflow-auto rounded-[24px] border border-black/5 bg-[#1f1610] px-5 py-4 font-mono text-sm leading-6 text-[#f5e7d4]">
            {rawOutput || '{ }'}
          </pre>
        ) : (
          <div className="mt-5 rounded-[24px] border border-dashed border-line bg-white/50 px-6 py-10 text-sm text-muted">
            Toggle Raw JSON to inspect the exact payload returned by the backend.
          </div>
        )}

        {analysisPayload?.note ? (
          <div className="mt-5 rounded-[20px] border border-copper/10 bg-copper/5 px-4 py-3 text-sm text-muted">
            {analysisPayload.note}
          </div>
        ) : null}

        {analysisPayload && Object.keys(expectedLabels).length > 0 ? (
          <div className="mt-5 rounded-[20px] border border-line bg-white/60 px-4 py-3 text-sm text-muted">
            Expected labels are loaded from the sample fixture and shown inline per customer card for visual QA.
          </div>
        ) : null}
      </section>
    </main>
  );
}
