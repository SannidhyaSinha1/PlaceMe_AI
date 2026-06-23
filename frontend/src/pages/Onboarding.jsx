import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { Check, UploadCloud, FileCheck2, ArrowRight, ArrowLeft } from "lucide-react";
import { profileApi } from "../services/api";
import { fetchMe, logout } from "../features/auth/authSlice";
import ThemeToggle from "../components/ThemeToggle";

// [key, label, type, required]
const ACADEMIC = [
  ["name", "Full Name", "text", true],
  ["college", "College", "text", false],
  ["branch", "Branch (e.g. CSE)", "text", true],
  ["current_year", "Current Year", "number", true],
  ["cgpa", "CGPA (out of 10)", "number", true],
  ["tenth_pct", "10th %", "number", true],
  ["twelfth_pct", "12th %", "number", true],
  ["active_backlogs", "Active Backlogs", "number", false],
];

const REQUIRED = ACADEMIC.filter(([, , , req]) => req).map(([k]) => k);

const errText = (e) => {
  const d = e.response?.data?.detail;
  if (Array.isArray(d)) return d.map((x) => `${x.loc?.slice(-1)[0]}: ${x.msg}`).join("; ");
  return d || "Something went wrong";
};

export default function Onboarding() {
  const user = useSelector((s) => s.auth.user);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [form, setForm] = useState({});
  const [hasResume, setHasResume] = useState(false);
  const [resumeName, setResumeName] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  // Prefill from any saved profile so a reload mid-onboarding isn't lost.
  useEffect(() => {
    profileApi.get().then(({ data }) => {
      setForm(data || {});
      setHasResume(Boolean(data?.resume_url));
      const academicsDone = REQUIRED.every((k) => data?.[k] != null && data[k] !== "");
      if (academicsDone) setStep(2);
    }).catch(() => {});
  }, []);

  // Already onboarded (or an admin) → no gate.
  if (user && (user.is_admin || user.profile_complete)) return <Navigate to="/" replace />;

  const onChange = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const num = (v, int) => {
    if (v === "" || v == null) return null;
    const n = int ? parseInt(v, 10) : parseFloat(v);
    return Number.isNaN(n) ? null : n;
  };

  const saveAcademics = async (e) => {
    e.preventDefault();
    setErr(null);
    for (const k of REQUIRED) {
      if (form[k] == null || form[k] === "") {
        setErr("Please fill in all required (*) fields.");
        return;
      }
    }
    const payload = {
      name: form.name || null,
      college: form.college || null,
      branch: form.branch || null,
      current_year: num(form.current_year, true),
      active_backlogs: num(form.active_backlogs, true) ?? 0,
      cgpa: num(form.cgpa),
      tenth_pct: num(form.tenth_pct),
      twelfth_pct: num(form.twelfth_pct),
    };
    setBusy(true);
    try {
      await profileApi.update(payload);
      setStep(2);
    } catch (e2) {
      setErr(errText(e2));
    }
    setBusy(false);
  };

  const onResume = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErr(null);
    setBusy(true);
    try {
      await profileApi.uploadResume(file);
      setHasResume(true);
      setResumeName(file.name);
    } catch (e2) {
      setErr(errText(e2));
    }
    setBusy(false);
  };

  const finish = async () => {
    setBusy(true);
    await dispatch(fetchMe()); // refresh user.profile_complete -> unlocks the gate
    navigate("/", { replace: true });
  };

  const Progress = () => (
    <div className="mb-6 flex items-center gap-2">
      {[1, 2].map((s) => (
        <div key={s} className="flex flex-1 items-center gap-2">
          <span
            className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
              step >= s ? "bg-brand-600 text-white" : "bg-muted text-ink-muted"
            }`}
          >
            {step > s ? <Check className="h-4 w-4" /> : s}
          </span>
          <span className={`text-sm ${step >= s ? "text-ink-soft" : "text-ink-muted"}`}>
            {s === 1 ? "Academic details" : "Upload CV"}
          </span>
          {s === 1 && <div className="mx-2 h-px flex-1 bg-muted" />}
        </div>
      ))}
    </div>
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="card w-full max-w-xl p-8">
        <div className="mb-1 flex items-center justify-between">
          <h1 className="text-2xl font-bold tracking-tight text-ink">Welcome to PlaceMe</h1>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              className="text-xs text-ink-muted hover:text-ink-soft"
              onClick={() => {
                dispatch(logout());
                navigate("/login");
              }}
            >
              Log out
            </button>
          </div>
        </div>
        <p className="mb-6 text-sm text-ink-muted">
          We need a few details to check your eligibility and tailor opportunities.
          This unlocks the rest of the app.
        </p>

        <Progress />

        {err && (
          <div className="mb-4 rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">{err}</div>
        )}

        {step === 1 && (
          <form onSubmit={saveAcademics} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              {ACADEMIC.map(([key, label, type, req]) => (
                <div key={key}>
                  <label className="label">
                    {label} {req && <span className="text-red-500">*</span>}
                  </label>
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
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? "Saving…" : <>Continue <ArrowRight className="h-4 w-4" /></>}
            </button>
          </form>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <p className="text-sm text-ink-soft">
              Upload your CV (PDF). We parse it to extract your skills and power resume matching.
            </p>
            <label
              className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center ${
                hasResume ? "border-green-500/40 bg-green-500/10" : "border-line hover:bg-muted"
              }`}
            >
              {hasResume ? (
                <FileCheck2 className="h-8 w-8 text-green-600" />
              ) : (
                <UploadCloud className="h-8 w-8 text-ink-muted" />
              )}
              <span className="mt-2 text-sm font-medium text-ink-soft">
                {hasResume ? `${resumeName || "CV uploaded"}` : "Click to upload your CV (PDF)"}
              </span>
              {hasResume && (
                <span className="mt-1 text-xs text-ink-muted">Click again to replace</span>
              )}
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={onResume}
                disabled={busy}
              />
            </label>
            <div className="flex gap-3">
              <button className="btn-ghost" onClick={() => setStep(1)} disabled={busy}>
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
              <button
                className="btn-primary flex-1"
                onClick={finish}
                disabled={busy || !hasResume}
                title={!hasResume ? "Upload your CV to continue" : undefined}
              >
                {busy ? "Finishing…" : "Finish & explore opportunities"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
