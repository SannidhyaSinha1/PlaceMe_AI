import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Navigate } from "react-router-dom";
import { Mail, Lock, Eye, EyeOff, Sparkles, Target, FileCheck2, ArrowRight } from "lucide-react";
import { login, register } from "../features/auth/authSlice";
import ThemeToggle from "../components/ThemeToggle";

const HIGHLIGHTS = [
  [Target, "Auto-tracked opportunities", "Internships & placements pulled straight from your inbox."],
  [FileCheck2, "Instant eligibility checks", "Know if you qualify before you spend time applying."],
  [Sparkles, "AI resumes & cover letters", "Tailored to every role in one click."],
];

export default function Login() {
  const dispatch = useDispatch();
  const { token, status, error } = useSelector((s) => s.auth);
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);

  if (token) return <Navigate to="/" replace />;

  const submit = (e) => {
    e.preventDefault();
    dispatch((mode === "login" ? login : register)({ email, password }));
  };

  return (
    <div className="relative grid min-h-dvh lg:grid-cols-2">
      <div className="absolute right-4 top-4 z-20">
        <ThemeToggle />
      </div>
      {/* Brand panel */}
      <div className="relative hidden overflow-hidden bg-brand-700 lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background:
              "radial-gradient(60rem 40rem at 10% -10%, rgba(129,140,248,0.45), transparent), radial-gradient(40rem 30rem at 90% 110%, rgba(217,119,6,0.30), transparent)",
          }}
        />
        <div className="relative flex items-center gap-3 text-white">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 ring-1 ring-white/25 backdrop-blur">
            <svg viewBox="0 0 32 32" className="h-6 w-6" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21V11l7 6 7-6v10" />
            </svg>
          </span>
          <span className="text-lg font-bold tracking-tight">PlaceMe AI</span>
        </div>

        <div className="relative max-w-md">
          <h2 className="text-3xl font-bold leading-tight text-white">
            Your placement season,<br />on autopilot.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-brand-100">
            One workspace for every opportunity, deadline, and application —
            powered by AI that actually understands your profile.
          </p>
          <div className="mt-9 space-y-5">
            {HIGHLIGHTS.map(([Icon, title, desc]) => (
              <div key={title} className="flex gap-3.5">
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-white/15">
                  <Icon className="h-[18px] w-[18px] text-white" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-white">{title}</p>
                  <p className="text-[13px] text-brand-200">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-brand-200">
          Built to run free · Trusted by campus placement cells
        </p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center bg-canvas px-5 py-10">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="mb-8 lg:hidden">
            <div className="flex items-center justify-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700">
                <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21V11l7 6 7-6v10" />
                </svg>
              </span>
              <span className="text-lg font-bold tracking-tight text-ink">PlaceMe AI</span>
            </div>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-ink">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            {mode === "login"
              ? "Sign in to pick up where you left off."
              : "Start tracking opportunities in minutes."}
          </p>

          <div className="mt-6 flex rounded-xl bg-muted p-1 text-sm font-semibold">
            {[["login", "Sign in"], ["register", "Register"]].map(([m, lbl]) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 rounded-lg py-2 transition-all duration-200 ${
                  mode === m ? "bg-surface text-brand-700 shadow-soft" : "text-ink-muted hover:text-ink"
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="label">College Email</label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
                <input
                  type="email"
                  required
                  autoComplete="email"
                  className="input pl-9"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@college.edu"
                />
              </div>
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
                <input
                  type={show ? "text" : "password"}
                  required
                  minLength={8}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  className="input px-9"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink-soft"
                  aria-label={show ? "Hide password" : "Show password"}
                >
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <p role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
                {error}
              </p>
            )}

            <button type="submit" className="btn-primary w-full" disabled={status === "loading"}>
              {status === "loading" ? (
                "Please wait…"
              ) : (
                <>
                  {mode === "login" ? "Sign in" : "Create account"}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-ink-muted">
            By continuing you agree to our terms & privacy policy.
          </p>
        </div>
      </div>
    </div>
  );
}
