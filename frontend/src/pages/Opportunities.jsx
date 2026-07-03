import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Search, SlidersHorizontal, SearchX } from "lucide-react";
import { fetchOpportunities, setFilter } from "../features/opportunities/opportunitiesSlice";
import { markInterested } from "../features/applications/applicationsSlice";
import OpportunityCard from "../components/OpportunityCard";

const TYPES = ["Internship", "Full-Time Placement", "Hackathon", "Competition", "Workshop", "Scholarship"];
const SORTS = [
  ["newest", "Newest"],
  ["deadline", "Deadline"],
  ["salary", "Salary"],
  ["company", "Company"],
];
const TOGGLES = [
  ["eligibleOnly", "Eligible only"],
  ["upcoming", "Upcoming"],
  ["applied", "Applied"],
];

function Toggle({ active, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
        active
          ? "border-brand-200 bg-brand-50 text-brand-700"
          : "border-line bg-surface text-ink-muted hover:bg-muted"
      }`}
    >
      {label}
    </button>
  );
}

export default function Opportunities() {
  const dispatch = useDispatch();
  const { items, filters, status } = useSelector((s) => s.opportunities);
  const [busyId, setBusyId] = useState(null);
  const [searchInput, setSearchInput] = useState(filters.search);

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

  const onInterested = async (id) => {
    setBusyId(id);
    await dispatch(markInterested(id));
    await dispatch(fetchOpportunities());
    setBusyId(null);
  };

  const toggleVal = (key) => (key === "applied" ? filters.applied === true : filters[key]);
  const onToggle = (key) =>
    update(key === "applied" ? { applied: filters.applied === true ? null : true } : { [key]: !filters[key] });

  return (
    <div className="animate-fade-up space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Opportunities</h1>
          <p className="mt-0.5 text-sm text-ink-muted">Internships, placements, hackathons & more.</p>
        </div>
        <span className="tnum rounded-full bg-muted px-3 py-1 text-xs font-semibold text-ink-soft">
          {items.length} results
        </span>
      </div>

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
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
          <SlidersHorizontal className="h-3.5 w-3.5 text-ink-muted" />
          {TOGGLES.map(([key, label]) => (
            <Toggle key={key} label={label} active={toggleVal(key)} onClick={() => onToggle(key)} />
          ))}
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
          <p className="font-semibold text-ink">No opportunities found</p>
          <p className="max-w-xs text-sm text-ink-muted">
            Try clearing a filter, or sync your inbox to pull in new postings.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((opp, i) => (
            <div key={opp.id} className="animate-fade-up" style={{ animationDelay: `${Math.min(i, 8) * 40}ms` }}>
              <OpportunityCard opp={opp} onInterested={onInterested} busy={busyId === opp.id} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
