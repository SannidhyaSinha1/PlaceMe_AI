import { Link } from "react-router-dom";
import { MapPin, Wallet, Mail, Plus, Check, ArrowUpRight } from "lucide-react";
import EligibilityBadge from "./EligibilityBadge";
import DeadlineCountdown from "./DeadlineCountdown";

const TYPE_COLORS = {
  Internship: "bg-blue-500/10 text-blue-600 ring-blue-600/20 dark:text-blue-400",
  "Full-Time Placement": "bg-indigo-500/10 text-indigo-600 ring-indigo-600/20 dark:text-indigo-400",
  Hackathon: "bg-purple-500/10 text-purple-600 ring-purple-600/20 dark:text-purple-400",
  Competition: "bg-pink-500/10 text-pink-600 ring-pink-600/20 dark:text-pink-400",
  Workshop: "bg-teal-500/10 text-teal-600 ring-teal-600/20 dark:text-teal-400",
  Scholarship: "bg-emerald-500/10 text-emerald-600 ring-emerald-600/20 dark:text-emerald-400",
  Other: "bg-muted text-ink-soft ring-line",
};

function initials(name) {
  return (name || "?")
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

export default function OpportunityCard({ opp, onInterested, busy }) {
  const typeCls = TYPE_COLORS[opp.opportunity_type] || TYPE_COLORS.Other;

  return (
    <div className="card card-hover flex flex-col gap-3.5 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold text-ink-soft">
            {initials(opp.company_name)}
          </span>
          <div className="min-w-0">
            <Link
              to={`/opportunities/${opp.id}`}
              className="block truncate font-semibold text-ink transition-colors hover:text-brand-600"
            >
              {opp.company_name || "Unknown company"}
            </Link>
            <p className="truncate text-sm text-ink-muted">{opp.role || "—"}</p>
          </div>
        </div>
        <span className={`badge shrink-0 ring-1 ring-inset ${typeCls}`}>{opp.opportunity_type}</span>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-ink-muted">
        {opp.job_location && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5" /> {opp.job_location}
          </span>
        )}
        {opp.salary_stipend && (
          <span className="inline-flex items-center gap-1 font-medium text-ink-soft">
            <Wallet className="h-3.5 w-3.5" /> {opp.salary_stipend}
          </span>
        )}
        <DeadlineCountdown deadline={opp.deadline} />
        {opp.email_link && (
          <a
            href={opp.email_link}
            target="_blank"
            rel="noopener noreferrer"
            title="Open the original email in Gmail"
            className="inline-flex items-center gap-1 font-medium text-brand-600 hover:text-brand-700"
          >
            <Mail className="h-3.5 w-3.5" /> Email
          </a>
        )}
      </div>

      {opp.required_skills?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {opp.required_skills.slice(0, 5).map((s) => (
            <span key={s} className="chip">{s}</span>
          ))}
          {opp.required_skills.length > 5 && (
            <span className="chip">+{opp.required_skills.length - 5}</span>
          )}
        </div>
      )}

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-line pt-3.5">
        <EligibilityBadge eligibility={opp.eligibility} />
        {opp.application_status ? (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-600">
            <Check className="h-3.5 w-3.5" /> {opp.application_status}
          </span>
        ) : (
          <button
            className="btn-secondary px-3 py-1.5 text-xs"
            disabled={busy}
            onClick={() => onInterested(opp.id)}
          >
            {busy ? (
              "Adding…"
            ) : (
              <>
                <Plus className="h-3.5 w-3.5" /> I'm Interested
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
