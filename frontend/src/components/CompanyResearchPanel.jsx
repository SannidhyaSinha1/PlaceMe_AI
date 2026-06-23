import { Building2, Wrench, Mic, TrendingUp } from "lucide-react";

const SECTIONS = [
  ["overview", "Overview", Building2],
  ["tech_stack", "Tech Stack", Wrench],
  ["interview_tips", "Interview Tips", Mic],
  ["hiring_trends", "Hiring Trends", TrendingUp],
];

export default function CompanyResearchPanel({ research, loading }) {
  if (loading) {
    return (
      <div className="space-y-3">
        <div className="skeleton h-4 w-1/3" />
        <div className="skeleton h-3 w-full" />
        <div className="skeleton h-3 w-5/6" />
      </div>
    );
  }
  if (!research) return null;

  return (
    <div className="space-y-4">
      {research.cached && (
        <p className="text-xs text-ink-muted">
          Loaded from cache · {research.generated_at?.slice(0, 10)}
        </p>
      )}
      {SECTIONS.map(([key, title, Icon]) =>
        research[key] ? (
          <div key={key}>
            <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-ink-soft">
              <Icon className="h-4 w-4 text-ink-muted" /> {title}
            </p>
            <p className="text-sm leading-relaxed text-ink-muted">{research[key]}</p>
          </div>
        ) : null
      )}
      {research.sources?.length > 0 && (
        <div>
          <p className="label">Sources</p>
          <ul className="space-y-1">
            {research.sources.map((url) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noreferrer" className="break-all text-xs text-brand-600 hover:underline">
                  {url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
