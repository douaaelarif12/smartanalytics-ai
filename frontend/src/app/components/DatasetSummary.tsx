import { Database, Check, CircleAlert } from "lucide-react";
import type { SalesDataset } from "../types";
import { inspectQuality } from "../services/analytics";
import { displayDate, integer } from "../format";

export default function DatasetSummary({ dataset }: { dataset: SalesDataset }) {
  const quality = inspectQuality(dataset);
  return (
    <section className="sa-card sa-dataset-summary">
      <div className="sa-card-heading">
        <div>
          <span className="sa-overline">THE SOURCE OF YOUR STORY</span>
          <h2>Dataset at a glance</h2>
        </div>
        <span className="sa-icon-tile">
          <Database size={20} />
        </span>
      </div>
      <div className="sa-file-summary">
        <span>
          <Database size={20} />
        </span>
        <div>
          <strong>{dataset.name}</strong>
          <small>{dataset.description}</small>
        </div>
        <span className="sa-badge">SAMPLE</span>
      </div>
      <dl className="sa-dataset-facts">
        <div>
          <dt>Total rows</dt>
          <dd>{integer(dataset.rows.length)}</dd>
        </div>
        <div>
          <dt>Columns</dt>
          <dd>{dataset.columns.length}</dd>
        </div>
        <div>
          <dt>
            Last import <small>(fictional)</small>
          </dt>
          <dd>
            {dataset.importedAt
              ? displayDate(dataset.importedAt)
              : "Not imported"}
          </dd>
        </div>
      </dl>
      <div className="sa-quality-heading">
        <h3>Data quality overview</h3>
        <span>
          {quality.completeness === null
            ? "No rows to inspect"
            : `${quality.completeness.toFixed(1)}% complete`}
        </span>
      </div>
      {quality.completeness !== null && (
        <meter
          min={0}
          max={100}
          value={quality.completeness}
          aria-label="Dataset cell completeness"
        />
      )}
      <div className="sa-quality-details">
        <span>
          <CircleAlert size={14} />
          {quality.missingCells} missing cells
        </span>
        <span>
          <Check size={14} />
          {quality.duplicateOrderIds} duplicate order IDs
        </span>
      </div>
      <p className="sa-fine-print">
        Whole dataset · completeness measures populated cells, not accuracy.
        Missing regions do not affect revenue calculations.
      </p>
    </section>
  );
}
