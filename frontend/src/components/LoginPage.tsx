import { useState } from "react";
import { DEMO_USERS, User } from "../types";

interface Props {
  onLogin: (user: User) => void;
  onRegister: () => void;
}

export default function LoginPage({ onLogin, onRegister }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const user = DEMO_USERS[email.toLowerCase()];
    if (user && password.length >= 4) {
      onLogin(user);
    } else {
      setError("Credenciales inválidas. Usa los accesos de demo.");
    }
  };

  return (
    <div className="min-h-screen bg-[#f0f4f8] flex flex-col">
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-10">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-full bg-[#1a7eff] flex items-center justify-center shadow-lg">
            <span className="text-white font-bold text-lg">$</span>
          </div>
          <span className="text-2xl font-bold text-[#1a7eff] tracking-tight">Global Exchange</span>
        </div>

        {/* Card */}
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-[#e2e8f0] p-8">
          <h1 className="text-2xl font-bold text-[#1a202c] text-center mb-1">Iniciar Sesión</h1>
          <p className="text-sm text-[#718096] text-center mb-7">
            Ingresa tus credenciales para acceder a tu panel financiero.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">
                Correo Electrónico
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9ca3af]">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
                </span>
                <input
                  type="email"
                  value={email}
                  onChange={e => { setEmail(e.target.value); setError(""); }}
                  placeholder="ejemplo@correo.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-[#e2e8f0] text-sm focus:outline-none focus:ring-2 focus:ring-[#1a7eff] focus:border-transparent transition"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-sm font-medium text-[#374151]">Contraseña</label>
                <button type="button" className="text-xs text-[#1a7eff] hover:underline">
                  ¿Olvidaste tu contraseña?
                </button>
              </div>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9ca3af]">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                </span>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={e => { setPassword(e.target.value); setError(""); }}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-10 py-2.5 rounded-lg border border-[#e2e8f0] text-sm focus:outline-none focus:ring-2 focus:ring-[#1a7eff] focus:border-transparent transition"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#9ca3af] hover:text-[#6b7280]"
                >
                  {showPassword
                    ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                    : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  }
                </button>
              </div>
            </div>

            {/* Remember */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={remember}
                onChange={e => setRemember(e.target.checked)}
                className="w-4 h-4 rounded border-[#d1d5db] accent-[#1a7eff]"
              />
              <span className="text-sm text-[#4b5563]">Recuérdame en este equipo</span>
            </label>

            {error && (
              <p className="text-sm text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>
            )}

            <button
              type="submit"
              className="w-full bg-[#1a7eff] hover:bg-[#1565d8] text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              Acceder al Panel
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </button>
          </form>

          <div className="my-5 flex items-center gap-3">
            <div className="flex-1 h-px bg-[#e2e8f0]"/>
            <span className="text-xs text-[#9ca3af] font-medium">O CONTINÚA CON</span>
            <div className="flex-1 h-px bg-[#e2e8f0]"/>
          </div>

          <p className="text-sm text-center text-[#6b7280]">
            ¿Aún no tienes una cuenta en Global Exchange?
          </p>
          <button
            onClick={onRegister}
            className="w-full mt-2 text-sm text-[#1a7eff] font-medium hover:underline text-center border border-[#e2e8f0] hover:bg-[#f0f7ff] py-2 rounded-lg transition-colors"
          >
            Crear cuenta gratis ahora
          </button>

          <div className="mt-6 pt-4 border-t border-[#f1f5f9] flex items-center justify-center gap-1.5 text-xs text-[#9ca3af]">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Encriptación de 256-bits activa
          </div>
        </div>

        {/* Demo hint */}
        <div className="mt-5 w-full max-w-md bg-[#fffbeb] border border-[#fcd34d] rounded-xl p-4">
          <p className="text-xs font-semibold text-[#92400e] mb-2">Accesos de demostración (contraseña: cualquiera ≥4 chars)</p>
          <div className="grid grid-cols-2 gap-1.5">
            {[
              { label: "Cliente", email: "cliente@global.com" },
              { label: "Cajero", email: "cajero@global.com" },
              { label: "Analista", email: "analista@global.com" },
              { label: "Admin", email: "admin@global.com" },
            ].map(d => (
              <button
                key={d.email}
                onClick={() => { setEmail(d.email); setPassword("demo1234"); setError(""); }}
                className="text-left bg-white border border-[#fcd34d] rounded-lg px-2.5 py-1.5 hover:bg-[#fef3c7] transition-colors"
              >
                <span className="block text-xs font-semibold text-[#92400e]">{d.label}</span>
                <span className="block text-[10px] text-[#b45309]">{d.email}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <footer className="py-4 flex justify-center gap-6 text-xs text-[#9ca3af]">
        <button className="hover:text-[#6b7280]">Asistencia Técnica</button>
        <button className="hover:text-[#6b7280]">Centro de Seguridad</button>
        <button className="hover:text-[#6b7280]">Información Legal</button>
      </footer>
    </div>
  );
}
