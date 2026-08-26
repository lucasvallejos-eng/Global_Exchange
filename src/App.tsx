import { useState } from "react";
import { User, View } from "./types";
import LoginPage from "./components/LoginPage";
import RegisterPage from "./components/RegisterPage";
import DashboardLayout from "./components/DashboardLayout";

export default function App() {
  const [view, setView] = useState<View>("login");
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const handleLogin = (user: User) => {
    setCurrentUser(user);
    setView("dashboard");
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setView("login");
  };

  if (view === "login") return <LoginPage onLogin={handleLogin} onRegister={() => setView("register")} />;
  if (view === "register") return <RegisterPage onBack={() => setView("login")} />;
  if (view === "dashboard" && currentUser) return <DashboardLayout user={currentUser} onLogout={handleLogout} />;

  return null;
}
