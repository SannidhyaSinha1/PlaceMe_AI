import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import {
  CheckCircle2,
  Send,
  Trophy,
  TrendingUp,
  Megaphone,
  CalendarClock,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { fetchDashboard } from "../features/analytics/analyticsSlice";
import { fetchOpportunities } from "../features/opportunities/opportunitiesSlice";
import { announcementsApi } from "../services/api";
import EligibilityBadge from "../components/EligibilityBadge";
import DeadlineCountdown from "../components/DeadlineCountdown";

function Stat({ label, value, Icon, tint }) {
  return (
    <div className="card card-hover p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${tint}`}>
          <Icon className="h-4 w-4" strokeWidth={2.2} />
        </span>
      </div>
      <p className="tnum mt-2 text-3xl font-bold tracking-tight text-ink">{value}</p>
    </div>
  );
}

function SectionHeader({ Icon, title, to, cta }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="flex items-center gap-2 font-semibold text-ink">
        <Icon className="h-[18px] w-[18px] text-ink-muted" /> {title}
      </h2>
      <Link
        to={to}
        className="inline-flex items-center gap-0.5 text-xs font-semibold text-brand-600 hover:text-brand-700"
      >
        {cta} <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}

export default function Dashboard() {
  const dispatch = useDispatch();
  const { dashboard } = useSelector((s) => s.analytics);
  const { items } = useSelector((s) => s.opportunities);
  const user = useSelector((s) => s.auth.user);
  const [announcements, setAnnouncements] = useState([]);

  useEffect(() => {
    dispatch(fetchDashboard());
    dispatch(fetchOpportunities());
    announcementsApi.list().then((r) => setAnnouncements(r.data)).catch(() => {});
  }, [dispatch]);

  const stats = dashboard?.stats || {};
  const upcoming = dashboard?.upcoming_deadlines || [];
  const eligibleNew = items
    .filter((o) => o.eligibility?.status === "Eligible" && !o.application_status)
    .slice(0, 4);

  return (
    <div className="animate-fade-up space-y-7">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">
          Welcome back{user?.email ? `, ${user.email.split("@")[0]}` : ""}
        </h1>
        <p className="mt-0.5 text-sm text-ink-muted">Here's your placement snapshot.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Eligible" value={stats.eligible ?? 0} Icon={CheckCircle2} tint="bg-green-500/10 text-green-600 dark:text-green-400" />
        <Stat label="Applied" value={stats.applied ?? 0} Icon={Send} tint="bg-brand-500/10 text-brand-600 dark:text-brand-400" />
        <Stat label="Offers" value={stats.offers ?? 0} Icon={Trophy} tint="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" />
        <Stat label="Success Rate" value={`${stats.success_rate ?? 0}%`} Icon={TrendingUp} tint="bg-accent-500/15 text-accent-600 dark:text-accent-400" />
      </div>

      {announcements.length > 0 && (
        <div className="card overflow-hidden">
          <div className="flex items-center gap-2 border-b border-line bg-brand-500/[0.07] px-5 py-3">
            <Megaphone className="h-4 w-4 text-brand-600 dark:text-brand-400" />
            <p className="text-sm font-semibold text-brand-700 dark:text-brand-300">Announcements</p>
          </div>
          <ul className="divide-y divide-line">
            {announcements.slice(0, 3).map((a) => (
              <li key={a.id} className="px-5 py-3 text-sm">
                <span className="font-semibold text-ink">{a.title}</span>
                <span className="text-ink-muted"> — {a.body}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <SectionHeader Icon={CalendarClock} title="Upcoming Deadlines" to="/applications" cta="View tracker" />
          {upcoming.length === 0 ? (
            <div className="rounded-xl border border-dashed border-line py-8 text-center">
              <p className="text-sm text-ink-muted">No upcoming deadlines.</p>
              <p className="mt-0.5 text-xs text-ink-muted">Mark opportunities as interested to track them.</p>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {upcoming.map((d, i) => (
                <li key={i} className="flex items-center justify-between py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">{d.company_name}</p>
                    <p className="truncate text-xs text-ink-muted">{d.role}</p>
                  </div>
                  <DeadlineCountdown deadline={d.deadline} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-5">
          <SectionHeader Icon={Sparkles} title="Recommended for You" to="/opportunities" cta="Browse all" />
          {eligibleNew.length === 0 ? (
            <div className="rounded-xl border border-dashed border-line py-8 text-center">
              <p className="text-sm text-ink-muted">No new eligible opportunities right now.</p>
              <p className="mt-0.5 text-xs text-ink-muted">Check back after the next inbox sync.</p>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {eligibleNew.map((o) => (
                <li key={o.id} className="flex items-center justify-between gap-2 py-2.5">
                  <Link
                    to={`/opportunities/${o.id}`}
                    className="min-w-0 truncate text-sm font-medium text-ink hover:text-brand-600"
                  >
                    {o.company_name} <span className="text-ink-muted">· {o.role}</span>
                  </Link>
                  <EligibilityBadge eligibility={o.eligibility} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
