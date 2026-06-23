import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { UserRound, FileText, Mail, Upload, RefreshCw, ExternalLink, FileCode2 } from "lucide-react";
import { fetchProfile, saveProfile, uploadResume } from "../features/profile/profileSlice";
import { authApi, gmailApi, API_BASE } from "../services/api";

const FIELDS = [
  ["name", "Full Name", "text"],
  ["college", "College", "text"],
  ["branch", "Branch", "text"],
  ["current_year", "Current Year", "number"],
  ["cgpa", "CGPA", "number"],
  ["tenth_pct", "10th %", "number"],
  ["twelfth_pct", "12th %", "number"],
  ["active_backlogs", "Active Backlogs", "number"],
];

export default function Profile() {
  const dispatch = useDispatch();
  const { data, saving } = useSelector((s) => s.profile);
  const [form, setForm] = useState({});
  const [skillsText, setSkillsText] = useState("");
  const [resumeMsg, setResumeMsg] = useState("");
  const [gmailMsg, setGmailMsg] = useState("");
  const [saveMsg, setSaveMsg] = useState(null);
  const [latexMsg, setLatexMsg] = useState(null);

  useEffect(() => {
    dispatch(fetchProfile());
  }, [dispatch]);

  useEffect(() => {
    if (data) {
      setForm(data);
      setSkillsText((data.skills || []).join(", "));
    }
  }, [data]);

  const onChange = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async (e) => {
    e.preventDefault();
    // Build an explicit payload — only the editable profile fields. Blank
    // numeric inputs become null (an empty string fails backend validation).
    const num = (v, int) => {
      if (v === "" || v == null) return null;
      const n = int ? parseInt(v, 10) : parseFloat(v);
      return Number.isNaN(n) ? null : n;
    };
    const payload = {
      name: form.name || null,
      college: form.college || null,
      branch: form.branch || null,
      current_year: num(form.current_year, true),
      active_backlogs: num(form.active_backlogs, true),
      cgpa: num(form.cgpa),
      tenth_pct: num(form.tenth_pct),
      twelfth_pct: num(form.twelfth_pct),
      skills: skillsText.split(",").map((s) => s.trim()).filter(Boolean),
      resume_latex: form.resume_latex || null,
    };
    setSaveMsg(null);
    const res = await dispatch(saveProfile(payload));
    if (res.meta.requestStatus === "fulfilled") {
      setSaveMsg({ ok: true, text: "✓ Profile saved" });
    } else {
      const detail = res.payload;
      const text = Array.isArray(detail)
        ? detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join("; ")
        : detail || "Save failed";
      setSaveMsg({ ok: false, text });
    }
  };

  const onResume = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setResumeMsg("Uploading & parsing…");
    const res = await dispatch(uploadResume(file));
    setResumeMsg(res.meta.requestStatus === "fulfilled" ? "✓ Resume parsed and skills updated" : "Upload failed");
  };

  const onLatexFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onChange("resume_latex", String(reader.result || ""));
    reader.readAsText(file);
    e.target.value = "";
  };

  const saveLatex = async () => {
    setLatexMsg(null);
    const res = await dispatch(saveProfile({ resume_latex: form.resume_latex || null }));
    setLatexMsg(
      res.meta.requestStatus === "fulfilled"
        ? { ok: true, text: "✓ LaTeX source saved" }
        : { ok: false, text: "Save failed" }
    );
  };

  const connectGmail = async () => {
    try {
      const { data } = await authApi.gmailConnect();
      window.location.href = data.auth_url;
    } catch (e) {
      setGmailMsg(e.response?.data?.detail || "Gmail OAuth not configured on the server");
    }
  };

  const syncGmail = async () => {
    setGmailMsg("Syncing inbox…");
    try {
      const { data } = await gmailApi.sync();
      setGmailMsg(`✓ Fetched ${data.fetched} emails, ${data.new_opportunities} new opportunities`);
    } catch (e) {
      setGmailMsg(e.response?.data?.detail || "Sync failed");
    }
  };

  const resumeUrl = data?.resume_url
    ? data.resume_url.startsWith("http") ? data.resume_url : `${API_BASE}${data.resume_url}`
    : null;

  return (
    <div className="animate-fade-up space-y-6">
      <div className="grid gap-6 lg:grid-cols-3">
      <form onSubmit={save} className="card space-y-4 p-6 lg:col-span-2">
        <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight text-ink">
          <UserRound className="h-5 w-5 text-brand-600" /> Student Profile
        </h1>
        <div className="grid gap-4 sm:grid-cols-2">
          {FIELDS.map(([key, label, type]) => (
            <div key={key}>
              <label className="label">{label}</label>
              <input
                type={type}
                step={type === "number" ? "0.01" : undefined}
                className="input"
                value={form[key] ?? ""}
                onChange={(e) => onChange(key, e.target.value)}
              />
            </div>
          ))}
        </div>
        <div>
          <label className="label">Skills (comma separated)</label>
          <textarea
            className="input h-20"
            value={skillsText}
            onChange={(e) => setSkillsText(e.target.value)}
            placeholder="python, react, sql, machine learning"
          />
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-primary" disabled={saving}>{saving ? "Saving…" : "Save Profile"}</button>
          {saveMsg && (
            <span className={`text-sm ${saveMsg.ok ? "text-green-600" : "text-red-600"}`}>{saveMsg.text}</span>
          )}
        </div>
      </form>

      <div className="space-y-6">
        <div className="card p-6">
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-ink">
            <FileText className="h-[18px] w-[18px] text-ink-muted" /> Resume
          </h2>
          {resumeUrl && (
            <a href={resumeUrl} target="_blank" rel="noreferrer" className="mb-2 block text-sm text-brand-600 hover:underline">
              View current resume
            </a>
          )}
          <label className="btn-ghost w-full cursor-pointer">
            <Upload className="h-4 w-4" /> Upload PDF
            <input type="file" accept="application/pdf" className="hidden" onChange={onResume} />
          </label>
          {resumeMsg && <p className="mt-2 text-xs text-ink-muted">{resumeMsg}</p>}
          {data?.resume_parsed?.skills?.length > 0 && (
            <div className="mt-3">
              <p className="label">Parsed skills</p>
              <div className="flex flex-wrap gap-1">
                {data.resume_parsed.skills.slice(0, 12).map((s) => (
                  <span key={s} className="rounded bg-muted px-2 py-0.5 text-xs text-ink-soft">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="card p-6">
          <h2 className="mb-2 flex items-center gap-2 font-semibold text-ink">
            <Mail className="h-[18px] w-[18px] text-ink-muted" /> Gmail Sync
          </h2>
          <p className="mb-3 text-xs text-ink-muted">
            Connect your college Gmail so PlaceMe can auto-detect opportunities.
          </p>
          <div className="flex flex-col gap-2">
            <button className="btn-primary" onClick={connectGmail}><ExternalLink className="h-4 w-4" /> Connect Gmail</button>
            <button className="btn-ghost" onClick={syncGmail}><RefreshCw className="h-4 w-4" /> Sync Now</button>
          </div>
          {gmailMsg && <p className="mt-2 text-xs text-ink-muted">{gmailMsg}</p>}
        </div>
      </div>
      </div>

      <div className="card p-6">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 font-semibold text-ink">
            <FileCode2 className="h-[18px] w-[18px] text-ink-muted" /> Résumé LaTeX source
          </h2>
          <label className="btn-ghost cursor-pointer px-3 py-1.5 text-xs">
            <Upload className="h-3.5 w-3.5" /> Upload .tex
            <input
              type="file"
              accept=".tex,text/plain,application/x-tex"
              className="hidden"
              onChange={onLatexFile}
            />
          </label>
        </div>
        <p className="mb-3 text-xs text-ink-muted">
          Paste your résumé's LaTeX (e.g. straight from Overleaf). The AI edits this source for
          each role — bolding, adding, and removing keywords — and hands back tailored,
          compilable LaTeX in your exact template.
        </p>
        <textarea
          className="input h-56 font-mono text-xs leading-relaxed"
          spellCheck={false}
          value={form.resume_latex ?? ""}
          onChange={(e) => onChange("resume_latex", e.target.value)}
          placeholder={"\\documentclass{article}\n% paste your full .tex source here…"}
        />
        <div className="mt-3 flex items-center gap-3">
          <button type="button" className="btn-primary" disabled={saving} onClick={saveLatex}>
            {saving ? "Saving…" : "Save LaTeX source"}
          </button>
          {latexMsg && (
            <span className={`text-sm ${latexMsg.ok ? "text-green-600" : "text-red-600"}`}>
              {latexMsg.text}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
