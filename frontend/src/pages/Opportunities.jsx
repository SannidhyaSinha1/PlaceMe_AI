import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useSearchParams } from "react-router-dom";
import { Search, SearchX, RefreshCw, ExternalLink, Inbox, CheckCircle2 } from "lucide-react";
import { fetchOpportunities, setFilter } from "../features/opportunities/opportunitiesSlice";
import { fetchMe } from "../features/auth/authSlice";
import { authApi, gmailApi } from "../services/api";
import OpportunityCard from "../components/OpportunityCard";

const TYPES = ["Internship", "Full-Time Placement", "Hackathon", "Competition", "Workshop", "Scholarship"];
const SORTS = [
  ["newest", "Newest"],
  ["deadline", "Deadline"],
  ["company", "Company"],
];

/** Connect the mailbox, then pull new placement emails out of it. */
function InboxBar({ connected, onSynced }) {
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const connect = async () => {
    setMsg(null);
    try {
      const { data } = await authApi.gmailConnect();
      window.location.href = data.auth_url;
    } catch (e) {
      setMsg({ tone: "error", text: e.response?.data?.detail || "Gmail OAuth is not configured on the server" });
    }
  };

  const sync = async () => {
    setBusy(true);
    setMsg({ tone: "info", text: "Reading your inbox…" });
    try {
      const { data } = await gmailApi.sync();
      const added = `${data.new_opportunities} new compan${data.new_opportunities === 1 ? "y" : "ies"}`;
      // Each sync parses a bounded batch, so say plainly when more is waiting.
      setMsg(
        data.remaining > 0
          ? { tone: "info", text: `${added} · ${data.remaining} more email${data.remaining === 1 ? "" : "s"} left — sync again to continue` }
          : { tone: "ok", text: `${added} · inbox fully parsed` }
      );
      onSynced();
    } catch (e) {
      setMsg({ tone: "error", text: e.response?.data?.detail || "Sync failed" });
    }
    setBusy(false);
  };

  const toneCls = {
    ok: "text-green-600 dark:text-green-400",
    error: "text-red-600 dark:text-red-400",
    info: "text-ink-muted",
  };

  return (
    <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          <Inbox className="h-[18px] w-[18px] text-ink-soft" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-ink">
            {connected ? "Gmail connected" : "Connect your Gmail"}
          </p>
          <p className="truncate text-xs text-ink-muted">
            {msg ? (
              <span className={toneCls[msg.tone]}>{msg.text}</span>
            ) : connected ? (
              "Sync to parse new placement emails into company listings."
            ) : (
              "Read-only access, used only to find placement emails."
            )}
          </p>
        </div>
      </div>
      {connected ? (
        <button className="btn-secondary" onClick={sync} disabled={busy}>
          <RefreshCw className={`h-4 w-4 ${busy ? "animate-spin" : ""}`} />
          {busy ? "Syncing…" : "Sync inbox"}
        </button>
      ) : (
        <button className="btn-primary" onClick={connect}>
          <ExternalLink className="h-4 w-4" /> Connect Gmail
        </button>
      )}
    </div>
  );
}

export default function Opportunities() {
  const dispatch = useDispatch();
  const { items, filters, status } = useSelector((s) => s.opportunities);
  const user = useSelector((s) => s.auth.user);
  const [searchInput, setSearchInput] = useState(filters.search);
  const [params, setParams] = useSearchParams();
  const justConnected = params.get("gmail") === "connected";

  // Clear the OAuth callback marker once it has been shown.
  useEffect(() => {
    if (!justConnected) return;
    const t = setTimeout(() => setParams({}, { replace: true }), 6000);
    return () => clearTimeout(t);
  }, [justConnected, setParams]);

  // Debounce typing: only push the search term into filters (and refetch)
  // after a 300ms pause instead of on every keystroke.
  useEffect(() => {
    if (searchInput === filters.search) return;
    const t = setTimeout(() => dispatch(setFilter({ search: searchInput })), 300);
    return () => clearTimeout(t);
  }, [searchInput, filters.search, dispatch]);

  useEffect(() => {
    const promise = dispatch(fetchOpportunities());
    // Abort the in-flight request when filters change again before it lands.
    return () => promise.abort();
  }, [dispatch, filters]);

  const update = (patch) => dispatch(setFilter(patch));

  const onSynced = () => {
    dispatch(fetchOpportunities());
    dispatch(fetchMe());
  };

  return (
    <div className="animate-fade-up space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Companies</h1>
          <p className="mt-0.5 text-sm text-ink-muted">Parsed from your placement emails.</p>
        </div>
        <span className="tnum rounded-full bg-muted px-3 py-1 text-xs font-semibold text-ink-soft">
          {items.length} listed
        </span>
      </div>

      {justConnected && (
        <p className="flex items-center gap-2 rounded-lg bg-green-500/10 px-3 py-2 text-sm text-green-700 dark:text-green-400">
          <CheckCircle2 className="h-4 w-4" /> Gmail connected — hit “Sync inbox” to pull your emails in.
        </p>
      )}

      <InboxBar connected={!!user?.gmail_connected} onSynced={onSynced} />

      <div className="card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
            <input
              className="input pl-9"
              placeholder="Search company or role…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>
          <div className="flex gap-3">
            <select className="input lg:w-[180px]" value={filters.type} onChange={(e) => update({ type: e.target.value })}>
              <option value="">All types</option>
              {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <select className="input lg:w-[160px]" value={filters.sort} onChange={(e) => update({ sort: e.target.value })}>
              {SORTS.map(([v, l]) => <option key={v} value={v}>Sort: {l}</option>)}
            </select>
            <button
              onClick={() => update({ upcoming: !filters.upcoming })}
              className={`shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                filters.upcoming
                  ? "border-brand-200 bg-brand-50 text-brand-700"
                  : "border-line bg-surface text-ink-muted hover:bg-muted"
              }`}
            >
              Closing soon
            </button>
          </div>
        </div>
      </div>

      {status === "loading" ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card space-y-3 p-5">
              <div className="flex gap-3">
                <div className="skeleton h-10 w-10 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <div className="skeleton h-4 w-2/3" />
                  <div className="skeleton h-3 w-1/2" />
                </div>
              </div>
              <div className="skeleton h-3 w-full" />
              <div className="skeleton h-8 w-full" />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="card flex flex-col items-center justify-center gap-2 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <SearchX className="h-6 w-6 text-ink-muted" />
          </span>
          <p className="font-semibold text-ink">Nothing here yet</p>
          <p className="max-w-xs text-sm text-ink-muted">
            {user?.gmail_connected
              ? "Sync your inbox to parse placement emails, or clear a filter."
              : "Connect your Gmail above to get started."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((opp, i) => (
            <div key={opp.id} className="animate-fade-up" style={{ animationDelay: `${Math.min(i, 8) * 40}ms` }}>
              <OpportunityCard opp={opp} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
