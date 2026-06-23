import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from "lucide-react";

const CONFIG = {
  Eligible: ["bg-green-500/10 text-green-600 ring-green-600/20 dark:text-green-400", CheckCircle2],
  "Potentially Eligible": ["bg-amber-500/10 text-amber-600 ring-amber-600/25 dark:text-amber-400", AlertTriangle],
  "Not Eligible": ["bg-red-500/10 text-red-600 ring-red-600/20 dark:text-red-400", XCircle],
  Unknown: ["bg-muted text-ink-muted ring-line", HelpCircle],
};

export default function EligibilityBadge({ eligibility }) {
  const status = eligibility?.status || "Unknown";
  const [cls, Icon] = CONFIG[status] || CONFIG.Unknown;
  const title = (eligibility?.reasons || []).join(" • ");

  return (
    <span title={title} className={`badge ring-1 ring-inset ${cls}`}>
      <Icon className="h-3.5 w-3.5" strokeWidth={2.2} />
      {status}
      {eligibility?.score != null && status !== "Unknown" && (
        <span className="tnum opacity-70">{Math.round(eligibility.score * 100)}%</span>
      )}
    </span>
  );
}
