export default function ResumeAnalysis({ analysis, loading }) {
  if (loading) return <p className="text-sm text-ink-muted">Analyzing resume against this role…</p>;
  if (!analysis) return null;

  const score = analysis.ats_score ?? 0;
  const ring = score >= 75 ? "text-green-600" : score >= 50 ? "text-amber-600" : "text-red-600";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className={`text-4xl font-bold ${ring}`}>{score}</div>
        <div>
          <p className="text-sm font-semibold text-ink-soft">ATS Match Score</p>
          <p className="text-xs text-ink-muted">
            {analysis.matched_keywords?.length || 0} matched ·{" "}
            {analysis.missing_keywords?.length || 0} missing keywords
          </p>
        </div>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={score >= 75 ? "bg-green-500" : score >= 50 ? "bg-amber-500" : "bg-red-500"}
          style={{ width: `${score}%`, height: "100%" }}
        />
      </div>

      {analysis.skill_gaps?.length > 0 && (
        <div>
          <p className="label">Skill gaps</p>
          <div className="flex flex-wrap gap-1">
            {analysis.skill_gaps.map((s) => (
              <span key={s} className="rounded bg-red-50 px-2 py-0.5 text-xs text-red-600">{s}</span>
            ))}
          </div>
        </div>
      )}

      {analysis.missing_keywords?.length > 0 && (
        <div>
          <p className="label">Missing keywords</p>
          <div className="flex flex-wrap gap-1">
            {analysis.missing_keywords.slice(0, 15).map((s) => (
              <span key={s} className="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-700">{s}</span>
            ))}
          </div>
        </div>
      )}

      {analysis.suggestions?.length > 0 && (
        <div>
          <p className="label">Suggestions</p>
          <ul className="list-inside list-disc space-y-1 text-sm text-ink-soft">
            {analysis.suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
