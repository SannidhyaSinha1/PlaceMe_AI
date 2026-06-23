import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { opportunitiesApi } from "../../services/api";

const TYPES = ["Internship", "Full-Time Placement", "Hackathon", "Competition", "Workshop", "Scholarship", "Other"];

export default function UploadOpportunity() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    company_name: "", role: "", opportunity_type: "Internship",
    deadline: "", salary_stipend: "", job_location: "",
    required_skills: "", description: "",
    min_cgpa: "", allowed_branches: "", allowed_years: "", min_tenth: "", min_twelfth: "",
    no_backlogs_required: false,
  });
  const [msg, setMsg] = useState(null);
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    const list = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
    const payload = {
      company_name: form.company_name,
      role: form.role || null,
      opportunity_type: form.opportunity_type,
      description: form.description || null,
      deadline: form.deadline || null,
      salary_stipend: form.salary_stipend || null,
      job_location: form.job_location || null,
      required_skills: list(form.required_skills),
      eligibility_criteria: {
        min_cgpa: form.min_cgpa ? parseFloat(form.min_cgpa) : null,
        min_tenth: form.min_tenth ? parseFloat(form.min_tenth) : null,
        min_twelfth: form.min_twelfth ? parseFloat(form.min_twelfth) : null,
        allowed_branches: list(form.allowed_branches),
        allowed_years: list(form.allowed_years).map(Number).filter((n) => !isNaN(n)),
        required_skills: list(form.required_skills),
        no_backlogs_required: form.no_backlogs_required,
      },
    };
    try {
      await opportunitiesApi.create(payload);
      setMsg({ ok: true, text: "✓ Opportunity published" });
      setTimeout(() => navigate("/admin"), 800);
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Failed to create" });
    }
    setSaving(false);
  };

  const Field = ({ k, label, type = "text", ph }) => (
    <div>
      <label className="label">{label}</label>
      <input type={type} className="input" value={form[k]} placeholder={ph} onChange={(e) => set(k, e.target.value)} />
    </div>
  );

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-2xl font-bold text-ink">📤 Upload Opportunity</h1>
      <form onSubmit={submit} className="card space-y-4 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field k="company_name" label="Company *" />
          <Field k="role" label="Role" />
          <div>
            <label className="label">Type</label>
            <select className="input" value={form.opportunity_type} onChange={(e) => set("opportunity_type", e.target.value)}>
              {TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <Field k="deadline" label="Deadline" type="date" />
          <Field k="salary_stipend" label="Salary / Stipend" ph="50k/month" />
          <Field k="job_location" label="Location" />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea className="input h-20" value={form.description} onChange={(e) => set("description", e.target.value)} />
        </div>
        <Field k="required_skills" label="Required Skills (comma separated)" ph="python, sql, react" />

        <div className="border-t border-line pt-4">
          <p className="mb-2 text-sm font-semibold text-ink-soft">Eligibility Criteria</p>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field k="min_cgpa" label="Min CGPA" type="number" />
            <Field k="min_tenth" label="Min 10th %" type="number" />
            <Field k="min_twelfth" label="Min 12th %" type="number" />
            <Field k="allowed_branches" label="Branches (comma)" ph="Computer Science, IT" />
            <Field k="allowed_years" label="Years (comma)" ph="3, 4" />
            <label className="flex items-center gap-2 pt-6 text-sm text-ink-soft">
              <input type="checkbox" checked={form.no_backlogs_required} onChange={(e) => set("no_backlogs_required", e.target.checked)} />
              No backlogs
            </label>
          </div>
        </div>

        {msg && <p className={`text-sm ${msg.ok ? "text-green-600" : "text-red-600"}`}>{msg.text}</p>}
        <button className="btn-primary" disabled={saving || !form.company_name}>
          {saving ? "Publishing…" : "Publish Opportunity"}
        </button>
      </form>
    </div>
  );
}
