import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import OtpPage from "./pages/OtpPage";
import RegisterPage from "./pages/RegisterPage";
import PoliceDashboard from "./pages/PoliceDashboard";
import { apiGet, clearAuthSession } from "./lib/api";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("crime_token");
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;

    if (!token) {
      setReady(true);
      return;
    }

    apiGet("/auth/me")
      .then(() => {
        if (active) setReady(true);
      })
      .catch(() => {
        clearAuthSession();
        if (active) {
          setReady(true);
          navigate("/login", { replace: true });
        }
      });

    return () => {
      active = false;
    };
  }, [navigate, token]);

  if (!token) return <Navigate to="/login" replace />;
  if (!ready) return null;
  return children;
}

function RoleHome() {
  const user = JSON.parse(localStorage.getItem("crime_user") || "null");
  if (user?.role === "police") return <Navigate to="/police" replace />;
  return <DashboardPage />;
}

export default function App() {
  return (
    <ThemeProvider>
    <Routes>
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-otp" element={<OtpPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<ProtectedRoute><RoleHome /></ProtectedRoute>} />
      <Route path="/police" element={<ProtectedRoute><PoliceDashboard /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </ThemeProvider>
  );
}
