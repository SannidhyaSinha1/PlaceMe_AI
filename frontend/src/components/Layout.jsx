import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  LayoutDashboard,
  Target,
  ClipboardList,
  BarChart3,
  User,
  Shield,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { logout } from "../features/auth/authSlice";
import ThemeToggle from "./ThemeToggle";

const NAV = [
  ["/", "Dashboard", LayoutDashboard],
  ["/opportunities", "Opportunities", Target],
  ["/applications", "Tracker", ClipboardList],
  ["/analytics", "Analytics", BarChart3],
  ["/profile", "Profile", User],
];

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

function navClass({ isActive }) {
  return `group relative flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
    isActive ? "text-brand-700" : "text-ink-muted hover:text-ink"
  }`;
}

function NavItems({ user, onNavigate }) {
  const items = [...NAV];
  if (user?.is_admin) items.push(["/admin", "Admin", Shield]);
  return items.map(([to, label, Icon]) => (
    <NavLink key={to} to={to} end={to === "/"} className={navClass} onClick={onNavigate}>
      {({ isActive }) => (
        <>
          <Icon className="h-4 w-4" strokeWidth={2} />
          {label}
          {isActive && (
            <span className="absolute inset-x-2 -bottom-[13px] hidden h-0.5 rounded-full bg-brand-600 lg:block" />
          )}
        </>
      )}
    </NavLink>
  ));
}

export default function Layout() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const user = useSelector((s) => s.auth.user);
  const [menuOpen, setMenuOpen] = useState(false);

  const onLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  const initial = (user?.email?.[0] || "?").toUpperCase();

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-40 border-b border-line/70 bg-surface/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-8">
            <Brand />
            <nav className="hidden items-center gap-1 lg:flex">
              <NavItems user={user} />
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2.5 sm:flex">
              <div className="text-right leading-tight">
                <p className="max-w-[160px] truncate text-xs font-semibold text-ink">
                  {user?.email?.split("@")[0]}
                </p>
                <p className="text-[11px] text-ink-muted">{user?.is_admin ? "Admin" : "Student"}</p>
              </div>
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700 dark:bg-brand-500/20 dark:text-brand-300">
                {initial}
              </span>
            </div>
            <ThemeToggle />
            <button
              onClick={onLogout}
              title="Log out"
              className="hidden h-9 w-9 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-muted hover:text-ink sm:flex"
            >
              <LogOut className="h-4 w-4" />
            </button>
            <button
              onClick={() => setMenuOpen((o) => !o)}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-ink-soft hover:bg-muted lg:hidden"
              aria-label="Toggle menu"
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav className="animate-fade-in space-y-1 border-t border-line/70 px-3 py-3 lg:hidden">
            <NavItems user={user} onNavigate={() => setMenuOpen(false)} />
            <button
              onClick={onLogout}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-500/10 dark:text-red-400"
            >
              <LogOut className="h-4 w-4" /> Log out
            </button>
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
