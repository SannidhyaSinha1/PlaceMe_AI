import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useDispatch } from "react-redux";
import {
  ArrowLeft, MapPin, Wallet, FileText, PenLine, Search, Mail, ExternalLink, Plus, Check, Wand2, FileCode2,
} from "lucide-react";
import { opportunitiesApi, aiApi } from "../services/api";
import { markInterested } from "../features/applications/applicationsSlice";
import EligibilityBadge from "../components/EligibilityBadge";
import DeadlineCountdown from "../components/DeadlineCountdown";
import ResumeAnalysis from "../components/ResumeAnalysis";
import CoverLetterModal from "../components/CoverLetterModal";
import TailoredResumeModal from "../components/TailoredResumeModal";
import LatexTailorModal from "../components/LatexTailorModal";
import CompanyResearchPanel from "../components/CompanyResearchPanel";

export default function OpportunityDetail() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const [opp, setOpp] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [research, setResearch] = useState(null);
  const [coverLetter, setCoverLetter] = useState(null);
  const [tailored, setTailored] = useState(null);
  const [tailorOpen, setTailorOpen] = useState(false);
  const [latexResult, setLatexResult] = useState(null);
  const [latexOpen, setLatexOpen] = useState(false);
  const [loading, setLoading] = useState({ resume: false, research: false, cover: false, email: false, tailor: false, latex: false });
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState(null);
  const [email, setEmail] = useState(null);
  const [emailOpen, setEmailOpen] = useState(false);

  const load = () => opportunitiesApi.get(id).then((r) => setOpp(r.data));
  useEffect(() => { load(); }, [id]);

  const runResume = async () => {
    setLoading((l) => ({ ...l, resume: true }));
    setError(null);
    try {
      const { data } = await aiApi.optimizeResume(id);
      setAnalysis(data);
    } catch (e) {
      setError(e.response?.data?.detail || "Resume analysis failed");
    }
    setLoading((l) => ({ ...l, resume: false }));
  };

  const runResearch = async () => {
    setLoading((l) => ({ ...l, research: true }));
    try {
      const { data } = await aiApi.research(id);
      setResearch(data);
    } catch (e) {
      setError(e.response?.data?.detail || "Research failed");
    }
    setLoading((l) => ({ ...l, research: false }));
  };

  const runCover = async () => {
    setModalOpen(true);
    setLoading((l) => ({ ...l, cover: true }));
    try {
      const { data } = await aiApi.coverLetter(id);
      setCoverLetter(data);
    } catch (e) {
      setError(e.response?.data?.detail || "Cover letter failed");
      setModalOpen(false);
    }
    setLoading((l) => ({ ...l, cover: false }));
  };

  const runTailor = async () => {
    setTailorOpen(true);
    setLoading((l) => ({ ...l, tailor: true }));
    try {
      const { data } = await aiApi.tailorResume(id);
      setTailored(data);
    } catch (e) {
      setError(e.response?.data?.detail || "Resume tailoring failed");
      setTailorOpen(false);
    }
    setLoading((l) => ({ ...l, tailor: false }));
  };

  const runLatex = async () => {
    setError(null);
    setLatexOpen(true);
    setLoading((l) => ({ ...l, latex: true }));
    try {
      const { data } = await aiApi.tailorLatex(id);
      setLatexResult(data);
    } catch (e) {
      setLatexOpen(false);
      setError(e.response?.data?.detail || "LaTeX tailoring failed");
    }
    setLoading((l) => ({ ...l, latex: false }));
  };

  const loadEmail = async () => {
    if (email) { setEmailOpen((o) => !o); return; }
    setLoading((l) => ({ ...l, email: true }));
    try {
      const { data } = await opportunitiesApi.getEmail(id);
      setEmail(data);
      setEmailOpen(true);
    } catch (e) {
      setError(e.response?.data?.detail || "Could not fetch email");
    }
    setLoading((l) => ({ ...l, email: false }));
  };

  const onInterested = async () => {
    await dispatch(markInterested(Number(id)));
    load();
  };

  if (!opp) return <p className="text-sm text-ink-muted">Loading…</p>;

  return (
    <div className="space-y-6">
      <Link to="/opportunities" className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700">
        <ArrowLeft className="h-4 w-4" /> Back to opportunities
      </Link>

      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-ink">{opp.company_name}</h1>
            <p className="text-ink-muted">{opp.role} · {opp.opportunity_type}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-ink-muted">
              {opp.job_location && <span className="inline-flex items-center gap-1"><MapPin className="h-4 w-4" /> {opp.job_location}</span>}
              {opp.salary_stipend && <span className="inline-flex items-center gap-1 font-medium text-ink-soft"><Wallet className="h-4 w-4" /> {opp.salary_stipend}</span>}
              <DeadlineCountdown deadline={opp.deadline} />
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <EligibilityBadge eligibility={opp.eligibility} />
            {opp.application_status ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-3 py-1 text-xs font-semibold text-green-600 ring-1 ring-inset ring-green-600/20 dark:text-green-400">
                <Check className="h-3.5 w-3.5" /> {opp.application_status}
              </span>
            ) : (
              <button className="btn-primary" onClick={onInterested}>
                <Plus className="h-4 w-4" /> I'm Interested
              </button>
            )}
          </div>
        </div>

        {opp.eligibility?.reasons?.length > 0 && (
          <div className="mt-4 rounded-lg bg-canvas p-3 text-sm text-ink-soft">
            <p className="font-semibold">Eligibility notes</p>
            <ul className="list-inside list-disc">
              {opp.eligibility.reasons.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}

        {opp.required_skills?.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1">
            {opp.required_skills.map((s) => (
              <span key={s} className="chip">{s}</span>
            ))}
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-wrap gap-3">
        <button className="btn-secondary" onClick={runLatex}><FileCode2 className="h-4 w-4" /> Tailor My Résumé (LaTeX)</button>
        <button className="btn-ghost" onClick={runTailor}><Wand2 className="h-4 w-4" /> Highlight on PDF</button>
        <button className="btn-ghost" onClick={runResume}><FileText className="h-4 w-4" /> Analyze My Resume</button>
        <button className="btn-ghost" onClick={runCover}><PenLine className="h-4 w-4" /> Generate Cover Letter</button>
        <button className="btn-ghost" onClick={runResearch}><Search className="h-4 w-4" /> Research Company</button>
        {opp.source_email_id && (
          <button className="btn-ghost" onClick={loadEmail} disabled={loading.email}>
            <Mail className="h-4 w-4" /> {loading.email ? "Loading…" : emailOpen ? "Hide Email" : "View Email"}
          </button>
        )}
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

      {emailOpen && email && (
        <div className="card p-5 space-y-3">
          <div className="border-b pb-3 space-y-1">
            <p className="text-xs text-ink-muted">From</p>
            <p className="text-sm font-medium text-ink-soft">{email.sender}</p>
          </div>
          <div className="border-b pb-3 space-y-1">
            <p className="text-xs text-ink-muted">Subject</p>
            <p className="text-sm font-semibold text-ink">{email.subject}</p>
          </div>
          <div className="border-b pb-3 space-y-1">
            <p className="text-xs text-ink-muted">Date</p>
            <p className="text-sm text-ink-soft">{email.received_at}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-ink-muted">Body</p>
            <pre className="whitespace-pre-wrap text-sm text-ink-soft font-sans leading-relaxed max-h-96 overflow-y-auto">
              {email.body}
            </pre>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {(analysis || loading.resume) && (
          <div className="card p-5">
            <h2 className="mb-3 font-semibold text-ink">Resume Match</h2>
            <ResumeAnalysis analysis={analysis} loading={loading.resume} />
          </div>
        )}
        {(research || loading.research) && (
          <div className="card p-5">
            <h2 className="mb-3 font-semibold text-ink">Company Research</h2>
            <CompanyResearchPanel research={research} loading={loading.research} />
          </div>
        )}
      </div>

      <CoverLetterModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        coverLetter={coverLetter}
        loading={loading.cover}
      />

      <TailoredResumeModal
        open={tailorOpen}
        onClose={() => setTailorOpen(false)}
        resume={tailored}
        loading={loading.tailor}
      />

      <LatexTailorModal
        open={latexOpen}
        onClose={() => setLatexOpen(false)}
        result={latexResult}
        loading={loading.latex}
      />
    </div>
  );
}
