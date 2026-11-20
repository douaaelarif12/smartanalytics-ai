import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Sparkles, Send } from "lucide-react";
import { datasetsApi } from "../api/datasetsApi";
import type { AssistantResponse } from "../api/types";
import { useWorkspace } from "../workspace";
import { LoadingState } from "../components/States";
const ExplorerChart = lazy(() => import("../components/ExplorerChart"));

type Turn = { question: string; response?: AssistantResponse; error?: string };
export function AssistantAnswer({ response }: { response: AssistantResponse }) {
  return (
    <div className="sa-assistant-answer">
      <span className="sa-overline">
        {response.status === "clarification"
          ? "Clarification needed"
          : response.status}
      </span>
      <p>{response.answer}</p>
      {response.warnings.map((warning) => (
        <p className="sa-assistant-note" key={warning}>
          {warning}
        </p>
      ))}
      {response.chart && (
        <Suspense fallback={<LoadingState label="Loading chart..." />}>
          <ExplorerChart chart={response.chart} type={response.chart.type} />
        </Suspense>
      )}
      {response.results && (
        <details open>
          <summary>
            Computed results - {response.results.total_rows} result rows
          </summary>
          <div className="sa-assistant-table">
            <table>
              <thead>
                <tr>
                  {response.results.columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {response.results.rows.map((row, index) => (
                  <tr key={index}>
                    {response.results!.columns.map((column) => (
                      <td key={column}>
                        {row[column] == null ? "Missing" : String(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      {response.query && (
        <details>
          <summary>Analytical details</summary>
          <pre>{JSON.stringify(response.query, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}
export default function Assistant() {
  const { uploadedDataset } = useWorkspace();
  return <DatasetAssistant key={uploadedDataset?.id ?? "none"} />;
}

function DatasetAssistant() {
  const { uploadedDataset, uploadedDatasets, selectDataset } = useWorkspace();
  const [params] = useSearchParams();
  const [question, setQuestion] = useState(params.get("question") || "");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const epoch = useRef(0);
  useEffect(() => () => {
    epoch.current += 1;
    controller.current?.abort();
  }, []);
  async function submit() {
    if (!uploadedDataset || !question.trim() || loading) return;
    const currentEpoch = epoch.current;
    const text = question.trim();
    const abort = new AbortController();
    controller.current = abort;
    setQuestion("");
    setLoading(true);
    setTurns((items) => [...items.slice(-19), { question: text }]);
    const timer = window.setTimeout(() => abort.abort(), 100_000);
    try {
      const response = await datasetsApi.ask(
        uploadedDataset.id,
        text,
        abort.signal,
      );
      if (currentEpoch === epoch.current)
        setTurns((items) =>
          items.map((item, index) =>
            index === items.length - 1 ? { ...item, response } : item,
          ),
        );
    } catch (error) {
      if (currentEpoch === epoch.current)
        setTurns((items) =>
          items.map((item, index) =>
            index === items.length - 1
              ? {
                  ...item,
                  error: abort.signal.aborted
                    ? "Request timed out. Please try again."
                    : error instanceof Error
                      ? error.message
                      : "Analysis failed.",
                }
              : item,
          ),
        );
    } finally {
      window.clearTimeout(timer);
      if (currentEpoch === epoch.current) setLoading(false);
    }
  }
  const numeric = uploadedDataset?.columns.find((column) =>
    ["integer", "number"].includes(column.type),
  );
  const category = uploadedDataset?.columns.find(
    (column) => column.type === "text",
  );
  const suggestions = [
    "How many rows are in this dataset?",
    ...(numeric ? [`What is the average of "${numeric.name}"?`] : []),
    ...(category ? [`Count rows grouped by "${category.name}".`] : []),
  ];
  return (
    <section className="sa-assistant">
      <div className="sa-assistant-heading">
        <Sparkles size={26} />
        <div>
          <span className="sa-overline">FROM QUESTION TO CLARITY</span>
          <h2>Your data, explained.</h2>
          <p>
            Ask about an uploaded dataset. Every analysis runs through the
            validated analytics engine.
          </p>
        </div>
      </div>
      <label className="sa-assistant-dataset">
        Dataset
        <select
          value={uploadedDataset?.id || ""}
          onChange={(event) => selectDataset(`upload:${event.target.value}`)}
        >
          <option value="" disabled>
            Choose an uploaded dataset
          </option>
          {uploadedDatasets.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <p className="sa-assistant-note">
        Your question, column metadata and bounded aggregate results are sent to
        OpenAI. Raw records stay local. Questions are independent; include
        column names and any clarification in your next question.
      </p>
      {!uploadedDataset ? (
        <p>
          Choose a dataset above or{" "}
          <Link to="/app/datasets">upload a CSV or Excel file</Link> to begin.
        </p>
      ) : (
        <>
          <div className="sa-assistant-suggestions">
            {suggestions.map((text) => (
              <button
                type="button"
                key={text}
                disabled={loading}
                onClick={() => setQuestion(text)}
              >
                {text}
              </button>
            ))}
          </div>
          <div
            role="log"
            aria-label="Analytical conversation"
            aria-live="polite"
          >
            {turns.map((turn, index) => (
              <article className="sa-assistant-turn" key={index}>
                <h3>{turn.question}</h3>
                {turn.response && <AssistantAnswer response={turn.response} />}
                {turn.error && (
                  <div role="alert" className="sa-inline-status is-error">
                    {turn.error}
                    <button
                      type="button"
                      onClick={() => setQuestion(turn.question)}
                    >
                      Edit and retry
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
          {loading && (
            <LoadingState label="Planning, validating and calculating your analysis..." />
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submit();
            }}
          >
            <label htmlFor="analyst-question">Ask your data</label>
            <textarea
              id="analyst-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={2000}
              rows={3}
              placeholder="Which categories have the highest total amount?"
              disabled={loading}
            />
            <div className="sa-assistant-compose">
              <small>{question.length}/2000</small>
              <button
                className="sa-btn"
                type="submit"
                disabled={loading || !question.trim()}
              >
                <Send size={16} />
                Analyze
              </button>
            </div>
          </form>
        </>
      )}
    </section>
  );
}
