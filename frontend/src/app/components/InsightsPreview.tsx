import { Link } from "react-router-dom";
import { ArrowUpRight, Sparkles } from "lucide-react";
import type { AnalyticsSnapshot } from "../types";
import { money } from "../format";

import { suggestedQuestions } from "../data/suggestedQuestions";

export default function InsightsPreview({
  analytics,
}: {
  analytics: AnalyticsSnapshot;
}) {
  const top = analytics.categories[0];
  return (
    <section className="sa-card sa-insights">
      <div className="sa-card-heading">
        <div>
          <span className="sa-overline">A FRESH PERSPECTIVE</span>
          <h2>A little insight, a next step.</h2>
        </div>
        <span className="sa-icon-tile">
          <Sparkles size={20} />
        </span>
      </div>
      <div className="sa-insight-example">
        <span className="sa-badge">DEMONSTRATION · RULE-BASED</span>
        <h3>
          {top
            ? `${top.name} leads the way.`
            : "Your next insight starts with data."}
        </h3>
        <p>
          {top
            ? `${top.name} contributes ${top.share.toFixed(1)}% of sample revenue (${money(top.revenue)}) in this period. Compare the category mix to put the result in context.`
            : "Select Northstar Sales to explore a calculated example insight."}
        </p>
      </div>
      <span className="sa-overline">QUESTIONS TO EXPLORE NEXT</span>
      <div className="sa-question-links">
        {suggestedQuestions.map((question) => (
          <Link
            key={question}
            to={`/app/assistant?question=${encodeURIComponent(question)}`}
          >
            {question}
            <ArrowUpRight size={15} />
          </Link>
        ))}
      </div>
      <div className="sa-insight-footer">
        <small>Demo insight calculated locally.</small>
        <Link to="/app/assistant">
          Open AI Assistant <ArrowUpRight size={14} />
        </Link>
      </div>
    </section>
  );
}
