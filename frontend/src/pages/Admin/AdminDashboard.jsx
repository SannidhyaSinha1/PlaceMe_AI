import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Shield, Plus, Megaphone } from "lucide-react";
import { opportunitiesApi, announcementsApi } from "../../services/api";

export default function AdminDashboard() {
  const [opps, setOpps] = useState([]);
  const [announcements, setAnnouncements] = useState([]);

  useEffect(() => {
    opportunitiesApi.list({ limit: 100 }).then((r) => setOpps(r.data)).catch(() => {});
    announcementsApi.list().then((r) => setAnnouncements(r.data)).catch(() => {});
  }, []);

  const byType = opps.reduce((acc, o) => {
    acc[o.opportunity_type] = (acc[o.opportunity_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="animate-fade-up space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-ink">
          <Shield className="h-6 w-6 text-brand-600" /> Admin Dashboard
        </h1>
        <Link to="/admin/upload" className="btn-primary"><Plus className="h-4 w-4" /> Upload Opportunity</Link>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="card p-5">
          <p className="text-xs uppercase text-ink-muted">Total Opportunities</p>
          <p className="mt-1 text-3xl font-bold text-brand-600">{opps.length}</p>
        </div>
        {Object.entries(byType).slice(0, 3).map(([t, c]) => (
          <div key={t} className="card p-5">
            <p className="text-xs uppercase text-ink-muted">{t}</p>
            <p className="mt-1 text-3xl font-bold text-ink-soft">{c}</p>
          </div>
        ))}
      </div>

      <div className="card p-5">
        <h2 className="mb-3 font-semibold text-ink">All Opportunities</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase text-ink-muted">
                <th className="py-2">Company</th><th>Role</th><th>Type</th><th>Deadline</th><th>Source</th>
              </tr>
            </thead>
            <tbody>
              {opps.map((o) => (
                <tr key={o.id} className="border-b border-line">
                  <td className="py-2 font-medium text-ink-soft">{o.company_name}</td>
                  <td className="text-ink-muted">{o.role}</td>
                  <td className="text-ink-muted">{o.opportunity_type}</td>
                  <td className="text-ink-muted">{o.deadline || "—"}</td>
                  <td><span className="rounded bg-muted px-2 py-0.5 text-xs">{o.source}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card p-5">
        <h2 className="mb-3 flex items-center gap-2 font-semibold text-ink">
          <Megaphone className="h-[18px] w-[18px] text-ink-muted" /> Announcements
        </h2>
        <p className="mb-3 text-xs text-ink-muted">
          Broadcast to students from the Django admin portal (separate service).
        </p>
        <ul className="space-y-2 text-sm text-ink-soft">
          {announcements.length === 0 && <li className="text-ink-muted">No announcements yet.</li>}
          {announcements.map((a) => (
            <li key={a.id} className="border-l-2 border-brand-400 pl-3">
              <span className="font-medium">{a.title}</span> — {a.body}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
