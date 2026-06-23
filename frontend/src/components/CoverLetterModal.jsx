import { API_BASE } from "../services/api";

export default function CoverLetterModal({ open, onClose, coverLetter, loading }) {
  if (!open) return null;
  const pdfUrl = coverLetter?.pdf_url
    ? coverLetter.pdf_url.startsWith("http")
      ? coverLetter.pdf_url
      : `${API_BASE}${coverLetter.pdf_url}`
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="card max-h-[85vh] w-full max-w-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-5 py-3">
          <h3 className="font-semibold text-ink">AI Cover Letter</h3>
          <button onClick={onClose} className="text-ink-muted hover:text-ink-soft">✕</button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto px-5 py-4">
          {loading ? (
            <p className="text-sm text-ink-muted">Generating a tailored cover letter…</p>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink-soft">
              {coverLetter?.text}
            </pre>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t border-line px-5 py-3">
          {pdfUrl && (
            <a href={pdfUrl} target="_blank" rel="noreferrer" className="btn-ghost">
              ⬇ Download PDF
            </a>
          )}
          <button className="btn-primary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
