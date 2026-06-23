import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";
import {
  fetchApplications,
  updateApplicationStatus,
} from "../features/applications/applicationsSlice";
import { ChevronLeft, ChevronRight, Paperclip } from "lucide-react";
import EligibilityBadge from "../components/EligibilityBadge";
import { API_BASE } from "../services/api";

const COLUMNS = [
  "Interested",
  "Applied",
  "Assessment Scheduled",
  "Interview Scheduled",
  "Offer Received",
  "Rejected",
];

const COLUMN_ACCENT = {
  Interested: "border-t-slate-400",
  Applied: "border-t-blue-500",
  "Assessment Scheduled": "border-t-amber-500",
  "Interview Scheduled": "border-t-purple-500",
  "Offer Received": "border-t-green-500",
  Rejected: "border-t-red-400",
};

export default function ApplicationTracker() {
  const dispatch = useDispatch();
  const { items } = useSelector((s) => s.applications);

  useEffect(() => {
    dispatch(fetchApplications());
  }, [dispatch]);

  const onDrop = (e, status) => {
    e.preventDefault();
    const id = Number(e.dataTransfer.getData("appId"));
    const app = items.find((a) => a.id === id);
    if (app && app.status !== status) {
      dispatch(updateApplicationStatus({ id, status }));
    }
  };

  const move = (app, dir) => {
    const idx = COLUMNS.indexOf(app.status);
    const next = COLUMNS[idx + dir];
    if (next) dispatch(updateApplicationStatus({ id: app.id, status: next }));
  };

  return (
    <div className="animate-fade-up space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">Application Tracker</h1>
        <p className="mt-0.5 text-sm text-ink-muted">Drag cards between stages, or use the arrows.</p>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {COLUMNS.map((col) => {
          const cards = items.filter((a) => a.status === col);
          return (
            <div
              key={col}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => onDrop(e, col)}
              className={`w-72 flex-shrink-0 rounded-xl border-t-4 bg-muted/60 p-3 ${COLUMN_ACCENT[col]}`}
            >
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink-soft">{col}</h3>
                <span className="rounded-full bg-surface px-2 text-xs text-ink-muted">{cards.length}</span>
              </div>
              <div className="space-y-2">
                {cards.map((app) => (
                  <div
                    key={app.id}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("appId", app.id)}
                    className="card cursor-grab p-3 active:cursor-grabbing"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <Link
                        to={`/opportunities/${app.opportunity.id}`}
                        className="text-sm font-semibold text-ink-soft hover:text-brand-600"
                      >
                        {app.opportunity.company_name}
                      </Link>
                      <EligibilityBadge eligibility={{ status: app.eligibility_status, reasons: app.eligibility_reasons }} />
                    </div>
                    <p className="text-xs text-ink-muted">{app.opportunity.role}</p>
                    {app.cover_letter_url && (
                      <a
                        href={app.cover_letter_url.startsWith("http") ? app.cover_letter_url : `${API_BASE}${app.cover_letter_url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
                      >
                        <Paperclip className="h-3 w-3" /> Cover letter
                      </a>
                    )}
                    <div className="mt-2.5 flex justify-between border-t border-line pt-2">
                      <button onClick={() => move(app, -1)} className="rounded p-0.5 text-ink-muted hover:bg-muted hover:text-ink-soft disabled:opacity-30" disabled={COLUMNS.indexOf(app.status) === 0} aria-label="Move back"><ChevronLeft className="h-4 w-4" /></button>
                      <button onClick={() => move(app, 1)} className="rounded p-0.5 text-ink-muted hover:bg-muted hover:text-ink-soft disabled:opacity-30" disabled={COLUMNS.indexOf(app.status) === COLUMNS.length - 1} aria-label="Move forward"><ChevronRight className="h-4 w-4" /></button>
                    </div>
                  </div>
                ))}
                {cards.length === 0 && <p className="py-4 text-center text-xs text-ink-muted">Empty</p>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
