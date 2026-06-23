import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchMe } from "./features/auth/authSlice";

import Layout from "./components/Layout";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Opportunities from "./pages/Opportunities";
import OpportunityDetail from "./pages/OpportunityDetail";
import ApplicationTracker from "./pages/ApplicationTracker";
import Profile from "./pages/Profile";
import Analytics from "./pages/Analytics";
import AdminDashboard from "./pages/Admin/AdminDashboard";
import UploadOpportunity from "./pages/Admin/UploadOpportunity";

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
  );
}
