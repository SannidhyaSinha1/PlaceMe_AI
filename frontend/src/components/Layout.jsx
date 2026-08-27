import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { LogOut } from "lucide-react";
import { logout } from "../features/auth/authSlice";
import ThemeToggle from "./ThemeToggle";

function Brand() {
  return (
    <NavLink to="/" className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-soft">
        <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 21V11l7 6 7-6v10" />
        </svg>
      </span>
      <span className="text-[15px] font-bold tracking-tight text-ink">
        Place<span className="text-brand-600">Me</span>
      </span>
    </NavLink>
  );
}

export default function Layout() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const user = useSelector((s) => s.auth.user);

  const onLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  const initial = (user?.email?.[0] || "?").toUpperCase();

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-40 border-b border-line/70 bg-surface/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Brand />

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2.5 sm:flex">
              <p className="max-w-[180px] truncate text-xs font-semibold text-ink">
                {user?.email}
              </p>
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700 dark:bg-brand-500/20 dark:text-brand-300">
                {initial}
              </span>
            </div>
            <ThemeToggle />
            <button
              onClick={onLogout}
              title="Log out"
              className="flex h-9 w-9 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-muted hover:text-ink"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
