import { Suspense, lazy, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchMe } from "./features/auth/authSlice";

import Layout from "./components/Layout";

// Route-level code splitting: each page (and its heavy deps, e.g. Recharts on
// Analytics) loads on first visit instead of in the initial bundle.
const Login = lazy(() => import("./pages/Login"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Opportunities = lazy(() => import("./pages/Opportunities"));
const OpportunityDetail = lazy(() => import("./pages/OpportunityDetail"));
const ApplicationTracker = lazy(() => import("./pages/ApplicationTracker"));
const Profile = lazy(() => import("./pages/Profile"));
const Analytics = lazy(() => import("./pages/Analytics"));
const AdminDashboard = lazy(() => import("./pages/Admin/AdminDashboard"));
const UploadOpportunity = lazy(() => import("./pages/Admin/UploadOpportunity"));

function PageFallback() {
  return <div className="p-10 text-center text-sm text-ink-muted">Loading…</div>;
}

function RequireAuth({ children }) {
  const token = useSelector((s) => s.auth.token);
  return token ? children : <Navigate to="/login" replace />;
}

// Students must finish onboarding (profile + CV) before the app unlocks.
// Admins are exempt. While /auth/me is still loading, hold rendering.
function RequireProfile({ children }) {
  const user = useSelector((s) => s.auth.user);
  if (!user) return <div className="p-10 text-center text-sm text-ink-muted">Loading…</div>;
  if (!user.is_admin && !user.profile_complete) return <Navigate to="/onboarding" replace />;
  return children;
}

function RequireAdmin({ children }) {
  const user = useSelector((s) => s.auth.user);
  return user?.is_admin ? children : <Navigate to="/" replace />;
}

export default function App() {
  const dispatch = useDispatch();
  const token = useSelector((s) => s.auth.token);

  useEffect(() => {
    if (token) dispatch(fetchMe());
  }, [token, dispatch]);

  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/login" element={<Login />} />
      <Route
        path="/onboarding"
        element={
          <RequireAuth>
            <Onboarding />
          </RequireAuth>
        }
      />
      <Route
        element={
          <RequireAuth>
            <RequireProfile>
              <Layout />
            </RequireProfile>
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="opportunities" element={<Opportunities />} />
        <Route path="opportunities/:id" element={<OpportunityDetail />} />
        <Route path="applications" element={<ApplicationTracker />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="profile" element={<Profile />} />
        <Route
          path="admin"
          element={
            <RequireAdmin>
              <AdminDashboard />
            </RequireAdmin>
          }
        />
        <Route
          path="admin/upload"
          element={
            <RequireAdmin>
              <UploadOpportunity />
            </RequireAdmin>
          }
        />
      </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
