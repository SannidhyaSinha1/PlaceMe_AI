import { X, Download, Highlighter, Lightbulb, FileText } from "lucide-react";
import { API_BASE } from "../services/api";

export default function TailoredResumeModal({ open, onClose, resume, loading }) {
  if (!open) return null;

  const pdfUrl = resume?.pdf_url
    ? resume.pdf_url.startsWith("http")
      ? resume.pdf_url
      : `${API_BASE}${resume.pdf_url}`
    : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card animate-scale-in max-h-[85vh] w-full max-w-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h3 className="flex items-center gap-2 font-semibold text-ink">
            <Highlighter className="h-[18px] w-[18px] text-brand-600" /> Resume highlighted for this role
          </h3>
          <button onClick={onClose} className="text-ink-muted hover:text-ink" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[60vh] space-y-5 overflow-y-auto px-5 py-4">
          {loading ? (
            <div className="space-y-3 py-6">
              <p className="flex items-center gap-2 text-sm text-ink-muted">
                <Highlighter className="h-4 w-4 animate-pulse text-brand-600" />
                Matching keywords and highlighting your résumé…
              </p>
              <div className="skeleton h-3 w-full" />
              <div className="skeleton h-3 w-5/6" />
              <div className="skeleton h-3 w-2/3" />
            </div>
          ) : (
            <>
              {resume?.note && (
                <div className="flex items-start gap-2.5 rounded-lg bg-muted px-3 py-2.5">
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" />
                  <p className="text-sm text-ink-soft">{resume.note}</p>
                </div>
              )}

              {typeof resume?.ats_score === "number" && (
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                    Match for this role
                  </span>
                  <span className="tnum rounded-full bg-brand-500/10 px-2.5 py-0.5 text-sm font-bold text-brand-600 dark:text-brand-400">
                    {resume.ats_score}%
                  </span>
                </div>
              )}

              {resume?.highlighted?.length > 0 && (
                <div>
                  <p className="label">Highlighted on your résumé</p>
                  <div className="flex flex-wrap gap-1.5">
                    {resume.highlighted.map((s) => (
                      <span
                        key={s}
                        className="inline-flex items-center rounded-md bg-yellow-300/40 px-2 py-0.5 text-xs font-medium text-ink-soft ring-1 ring-yellow-500/30"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {resume?.suggestions?.length > 0 && (
                <div>
                  <p className="label">Tweak these in your own résumé</p>
                  <ul className="space-y-1.5">
                    {resume.suggestions.map((c, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-ink-soft">
                        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-line px-5 py-3.5">
          {pdfUrl && (
            <a href={pdfUrl} target="_blank" rel="noreferrer" className="btn-primary">
              <Download className="h-4 w-4" /> Download highlighted résumé
            </a>
          )}
          <button className="btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
