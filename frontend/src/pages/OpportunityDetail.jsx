import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, MapPin, Wallet, Mail, ExternalLink } from "lucide-react";
import { opportunitiesApi } from "../services/api";
import DeadlineCountdown from "../components/DeadlineCountdown";

/** Requirements the email itself stated — labelled, in a fixed order. */
const CRITERIA_LABELS = [
  ["min_cgpa", "Minimum CGPA"],
  ["min_tenth", "Minimum 10th %"],
  ["min_twelfth", "Minimum 12th %"],
  ["allowed_branches", "Branches"],
  ["allowed_years", "Years"],
  ["no_backlogs_required", "Backlogs"],
];

function formatCriterion(key, value) {
  if (key === "no_backlogs_required") return value ? "No active backlogs" : null;
  if (Array.isArray(value)) return value.length ? value.join(", ") : null;
  return value ?? null;
}

export default function OpportunityDetail() {
  const { id } = useParams();
  const [opp, setOpp] = useState(null);
  const [email, setEmail] = useState(null);
  const [emailOpen, setEmailOpen] = useState(false);
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    opportunitiesApi
      .get(id)
      .then((r) => setOpp(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Could not load this opportunity"));
  }, [id]);

  const loadEmail = async () => {
    if (email) {
      setEmailOpen((o) => !o);
      return;
    }
    setLoadingEmail(true);
    setError(null);
    try {
      const { data } = await opportunitiesApi.getEmail(id);
      setEmail(data);
      setEmailOpen(true);
    } catch (e) {
      setError(e.response?.data?.detail || "Could not fetch the original email");
    }
    setLoadingEmail(false);
  };

  if (error && !opp) return <p className="text-sm text-red-600">{error}</p>;
  if (!opp) return <p className="text-sm text-ink-muted">Loading…</p>;

  const criteria = CRITERIA_LABELS.map(([key, label]) => [
    label,
    formatCriterion(key, opp.eligibility_criteria?.[key]),
  ]).filter(([, value]) => value !== null && value !== "");

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700">
        <ArrowLeft className="h-4 w-4" /> Back to companies
      </Link>

      <div className="card p-6">
        <h1 className="text-2xl font-bold text-ink">{opp.company_name}</h1>
        <p className="text-ink-muted">
          {[opp.role, opp.opportunity_type].filter(Boolean).join(" · ")}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-ink-muted">
          {opp.job_location && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-4 w-4" /> {opp.job_location}
            </span>
          )}
          {opp.salary_stipend && (
            <span className="inline-flex items-center gap-1 font-medium text-ink-soft">
              <Wallet className="h-4 w-4" /> {opp.salary_stipend}
            </span>
          )}
          <DeadlineCountdown deadline={opp.deadline} />
        </div>

        {opp.description && (
          <p className="mt-4 text-sm leading-relaxed text-ink-soft">{opp.description}</p>
        )}

        {opp.required_skills?.length > 0 && (
          <div className="mt-4">
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">Skills</p>
            <div className="flex flex-wrap gap-1">
              {opp.required_skills.map((s) => (
                <span key={s} className="chip">{s}</span>
              ))}
            </div>
          </div>
        )}

        {criteria.length > 0 && (
          <div className="mt-4 rounded-lg bg-canvas p-3">
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Stated requirements
            </p>
            <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
              {criteria.map(([label, value]) => (
                <div key={label} className="flex justify-between gap-3">
                  <dt className="text-ink-muted">{label}</dt>
                  <dd className="text-right font-medium text-ink-soft">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {opp.source_email_id && (
        <div className="flex flex-wrap gap-3">
          <button className="btn-secondary" onClick={loadEmail} disabled={loadingEmail}>
            <Mail className="h-4 w-4" />
            {loadingEmail ? "Loading…" : emailOpen ? "Hide original email" : "View original email"}
          </button>
          {opp.email_link && (
            <a
              className="btn-ghost"
              href={opp.email_link}
              target="_blank"
              rel="noopener noreferrer"
              title="Open the original email in Gmail"
            >
              <ExternalLink className="h-4 w-4" /> Open in Gmail
            </a>
          )}
        </div>
      )}

      {emailOpen && email && (
        <div className="card space-y-3 p-5">
          <div className="space-y-1 border-b border-line pb-3">
            <p className="text-xs text-ink-muted">From</p>
            <p className="text-sm font-medium text-ink-soft">{email.sender}</p>
          </div>
          <div className="space-y-1 border-b border-line pb-3">
            <p className="text-xs text-ink-muted">Subject</p>
            <p className="text-sm font-semibold text-ink">{email.subject}</p>
          </div>
          <div className="space-y-1 border-b border-line pb-3">
            <p className="text-xs text-ink-muted">Date</p>
            <p className="text-sm text-ink-soft">{email.received_at}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-ink-muted">Body</p>
            <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink-soft">
              {email.body}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
