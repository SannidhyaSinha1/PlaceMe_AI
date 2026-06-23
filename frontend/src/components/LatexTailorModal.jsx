import { useState } from "react";
import { X, Download, Copy, Check, FileCode2, Wand2, ExternalLink } from "lucide-react";

function openInOverleaf(latex) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "https://www.overleaf.com/docs";
  form.target = "_blank";
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = "encoded_snip";
  input.value = encodeURIComponent(latex);
  form.appendChild(input);
  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}

export default function LatexTailorModal({ open, onClose, result, loading }) {
  const [copied, setCopied] = useState(false);
  if (!open) return null;

  const latex = result?.latex || "";

  const download = () => {
    const blob = new Blob([latex], { type: "application/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = result?.filename || "resume_tailored.tex";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(latex);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      /* ignore */
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="card animate-scale-in flex max-h-[88vh] w-full max-w-3xl flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h3 className="flex items-center gap-2 font-semibold text-ink">
            <FileCode2 className="h-[18px] w-[18px] text-brand-600" /> Tailored LaTeX résumé
          </h3>
          <button onClick={onClose} className="text-ink-muted hover:text-ink" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          {loading ? (
            <div className="space-y-3 py-6">
              <p className="flex items-center gap-2 text-sm text-ink-muted">
                <Wand2 className="h-4 w-4 animate-pulse text-brand-600" />
                Editing your LaTeX for this role…
              </p>
              <div className="skeleton h-3 w-full" />
              <div className="skeleton h-3 w-5/6" />
              <div className="skeleton h-40 w-full" />
            </div>
          ) : (
            <>
              {result?.used_llm === false && (
                <p className="rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
                  AI couldn't edit it this time (likely rate-limited) — your original LaTeX is shown
                  below unchanged. Try again shortly.
                </p>
              )}

              {result?.changes?.length > 0 && (
                <div>
                  <p className="label">What the AI changed for this role</p>
                  <ul className="space-y-1.5">
                    {result.changes.map((c, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-ink-soft">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <p className="label">Tailored .tex (edits in your exact template)</p>
                <pre className="max-h-[34vh] overflow-auto rounded-lg border border-line bg-muted/60 p-3 font-mono text-[11px] leading-relaxed text-ink-soft">
                  {latex}
                </pre>
              </div>
            </>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line px-5 py-3.5">
          {!loading && latex && (
            <>
              <button className="btn-ghost" onClick={copy}>
                {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied" : "Copy"}
              </button>
              <button className="btn-ghost" onClick={() => openInOverleaf(latex)}>
                <ExternalLink className="h-4 w-4" /> Open in Overleaf
              </button>
              <button className="btn-primary" onClick={download}>
                <Download className="h-4 w-4" /> Download .tex
              </button>
            </>
          )}
          <button className="btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
