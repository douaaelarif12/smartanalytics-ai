import { Link, useLocation, useSearchParams } from "react-router-dom";
import { ArrowLeft, Construction } from "lucide-react";
import { appNavigation } from "../navigation";

export default function PlannedPage() {
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const page = appNavigation.find(
    (item) => item.path === pathname.replace(/\/$/, ""),
  );
  const question =
    page?.path === "/app/assistant" ? params.get("question") : null;
  return (
    <section className="sa-card sa-planned">
      <span className="sa-state-icon">
        <Construction size={29} />
      </span>
      <span className="sa-badge">
        {page ? "PLANNED · NOT AVAILABLE YET" : "PAGE NOT FOUND"}
      </span>
      <h1>{page?.title ?? "This page isn’t here."}</h1>
      <p>
        {page?.description ??
          "This address does not match an application page."}
      </p>
      {question && (
        <blockquote>
          <span>Suggested question · not submitted</span>
          {question.slice(0, 300)}
        </blockquote>
      )}
      <div className="sa-planned-actions">
        <Link className="sa-btn" to="/app">
          <ArrowLeft size={15} /> Back to Overview
        </Link>
      </div>
      <small>
        Dataset uploads, validated analytics and the AI assistant remain
        available from the workspace navigation. This page is intentionally
        reserved for a later product phase.
      </small>
    </section>
  );
}
