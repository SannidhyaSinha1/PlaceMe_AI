import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { Sparkles } from "lucide-react";
import { fetchDashboard, fetchCharts } from "../features/analytics/analyticsSlice";
import { aiApi } from "../services/api";
import { useState } from "react";

const BAR_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#3b82f6", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"];

export default function Analytics() {
  const dispatch = useDispatch();
  const { dashboard, charts } = useSelector((s) => s.analytics);
  const [advice, setAdvice] = useState(null);
  const [loadingAdvice, setLoadingAdvice] = useState(false);

  useEffect(() => {
    dispatch(fetchDashboard());
    const theme = () => (document.documentElement.classList.contains("dark") ? "dark" : "light");
    dispatch(fetchCharts(theme()));
    // Re-render the server PNG charts with matching colours when the theme flips.
    const observer = new MutationObserver(() => dispatch(fetchCharts(theme())));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, [dispatch]);

  const getAdvice = async () => {
    setLoadingAdvice(true);
    try {
      const { data } = await aiApi.recommend();
      setAdvice(data);
    } catch (_) {}
    setLoadingAdvice(false);
  };

  const skillDemand = dashboard?.skill_demand || [];

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">Analytics</h1>
        <p className="mt-0.5 text-sm text-ink-muted">Skill demand, application breakdown & AI guidance.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recharts: live skill demand */}
        <div className="card p-5">
          <h2 className="mb-3 font-semibold text-ink">Skill Demand (Recharts)</h2>
          {skillDemand.length === 0 ? (
            <p className="text-sm text-ink-muted">Apply to opportunities to see skill demand.</p>
          ) : (
            <div className="text-ink-muted">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={skillDemand} layout="vertical" margin={{ left: 20 }}>
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: "currentColor" }} stroke="currentColor" strokeOpacity={0.3} />
                  <YAxis type="category" dataKey="skill" width={90} tick={{ fontSize: 12, fill: "currentColor" }} stroke="currentColor" strokeOpacity={0.3} />
                  <Tooltip
                    cursor={{ fill: "currentColor", fillOpacity: 0.06 }}
                    contentStyle={{
                      background: "rgb(var(--surface))",
                      border: "1px solid rgb(var(--line))",
                      borderRadius: 10,
                      color: "rgb(var(--ink))",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {skillDemand.map((_, i) => (
                      <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Server-rendered matplotlib pie (base64 PNG) */}
        <div className="card p-5">
          <h2 className="mb-3 font-semibold text-ink">Application Status (server PNG)</h2>
          {charts?.status_pie ? (
            <img src={`data:image/png;base64,${charts.status_pie}`} alt="Status pie chart" className="mx-auto max-h-72" />
          ) : (
            <p className="text-sm text-ink-muted">No application data yet.</p>
          )}
        </div>
      </div>

      <div className="card p-5">
        <h2 className="mb-3 font-semibold text-ink">Skill Gap (server PNG)</h2>
        {charts?.skill_gap_bar ? (
          <img src={`data:image/png;base64,${charts.skill_gap_bar}`} alt="Skill gap chart" className="mx-auto max-h-80" />
        ) : (
          <p className="text-sm text-ink-muted">No skill gaps detected — nice!</p>
        )}
      </div>

      <div className="card p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-semibold text-ink">
            <Sparkles className="h-[18px] w-[18px] text-brand-600" /> AI Career Recommendations
          </h2>
          <button className="btn-primary px-3 py-1.5 text-xs" onClick={getAdvice} disabled={loadingAdvice}>
            {loadingAdvice ? "Thinking…" : "Generate"}
          </button>
        </div>
        {advice ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <p className="sm:col-span-2 text-sm text-ink-soft">{advice.summary}</p>
            <Reco title="Target Companies" items={advice.target_companies} />
            <Reco title="Skills to Learn" items={advice.skills_to_learn} />
            <Reco title="Certifications" items={advice.certifications} />
            <Reco title="Project Ideas" items={advice.project_ideas} />
            <Reco title="Hackathons" items={advice.hackathons} />
          </div>
        ) : (
          <p className="text-sm text-ink-muted">Generate personalized guidance from your profile and history.</p>
        )}
      </div>
    </div>
  );
}

function Reco({ title, items }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className="label">{title}</p>
      <ul className="list-inside list-disc space-y-1 text-sm text-ink-soft">
        {items.map((it, i) => <li key={i}>{it}</li>)}
      </ul>
    </div>
  );
}
