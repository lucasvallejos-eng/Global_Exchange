import { useState } from "react";

interface Props {
  onBack: () => void;
}

export default function RegisterPage({ onBack }: Props) {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const strength = form.password.length === 0 ? 0
    : form.password.length < 6 ? 1
    : form.password.length < 10 ? 2
    : 3;

  const strengthLabel = ["", "Débil", "Moderada", "Fuerte"][strength];
  const strengthColor = ["", "bg-red-400", "bg-yellow-400", "bg-green-400"][strength];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!accepted) return;
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#f0f4f8] flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-[#e2e8f0] p-10 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <h2 className="text-xl font-bold text-[#1a202c] mb-2">¡Cuenta creada!</h2>
          <p className="text-sm text-[#718096] mb-6">Tu cuenta ha sido registrada. Un administrador la activará en breve.</p>
          <button onClick={onBack} className="w-full bg-[#1a7eff] hover:bg-[#1565d8] text-white font-semibold py-2.5 rounded-lg transition-colors">
            Ir al Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f0f4f8] flex flex-col items-center justify-center px-4 py-10">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-full bg-[#1a7eff] flex items-center justify-center shadow-lg">
          <span className="text-white font-bold text-lg">$</span>
        </div>
        <span className="text-2xl font-bold text-[#1a7eff] tracking-tight">Global Exchange</span>
      </div>

      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-[#e2e8f0] p-8">
        <h1 className="text-2xl font-bold text-[#1a202c] text-center mb-1">Únete a Global Exchange</h1>
        <p className="text-sm text-[#718096] text-center mb-7">
          Empieza a cambiar divisas con las mejores tasas de Paraguay hoy mismo.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Nombre completo</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9ca3af]">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </span>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Juan Pérez"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-[#e2e8f0] text-sm focus:outline-none focus:ring-2 focus:ring-[#1a7eff] focus:border-transparent transition"
                required
              />
            </div>
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Correo electrónico</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9ca3af]">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
              </span>
              <input
                type="email"
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                placeholder="nombre@ejemplo.com"
                className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-[#e2e8f0] text-sm focus:outline-none focus:ring-2 focus:ring-[#1a7eff] focus:border-transparent transition"
                required
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1.5">Contraseña</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9ca3af]">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              </span>
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                placeholder="••••••••"
                className="w-full pl-10 pr-10 py-2.5 rounded-lg border border-[#e2e8f0] text-sm focus:outline-none focus:ring-2 focus:ring-[#1a7eff] focus:border-transparent transition"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#9ca3af] hover:text-[#6b7280]"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              </button>
            </div>
            {form.password.length > 0 && (
              <div className="mt-2">
                <div className="flex gap-1 mb-1">
                  {[1, 2, 3].map(i => (
                    <div key={i} className={`flex-1 h-1 rounded-full transition-colors ${i <= strength ? strengthColor : "bg-[#e2e8f0]"}`}/>
                  ))}
                </div>
                <p className="text-xs text-[#6b7280]">SEGURIDAD: <span className="font-semibold">{strengthLabel}</span></p>
              </div>
            )}
          </div>

          {/* Terms */}
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={accepted}
              onChange={e => setAccepted(e.target.checked)}
              className="mt-0.5 w-4 h-4 rounded border-[#d1d5db] accent-[#1a7eff]"
            />
            <span className="text-sm text-[#4b5563]">
              Acepto los{" "}
              <span className="text-[#1a7eff] hover:underline cursor-pointer">Términos y Condiciones</span>
              {" "}y la{" "}
              <span className="text-[#1a7eff] hover:underline cursor-pointer">Política de Privacidad</span>
              {" "}de Global Exchange
            </span>
          </label>

          <button
            type="submit"
            disabled={!accepted}
            className="w-full bg-[#1a7eff] hover:bg-[#1565d8] disabled:bg-[#93c5fd] disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg transition-colors"
          >
            Crear mi cuenta gratis
          </button>
        </form>

        <p className="text-sm text-center text-[#6b7280] mt-4">
          ¿Ya tienes una cuenta?{" "}
          <button onClick={onBack} className="text-[#1a7eff] font-medium hover:underline">
            Inicia sesión aquí
          </button>
        </p>

        <div className="my-5 flex items-center gap-3">
          <div className="flex-1 h-px bg-[#e2e8f0]"/>
          <span className="text-xs text-[#9ca3af] font-medium">O CONTINÚA CON</span>
          <div className="flex-1 h-px bg-[#e2e8f0]"/>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {["Google", "GitHub"].map(p => (
            <button key={p} className="flex items-center justify-center gap-2 border border-[#e2e8f0] rounded-lg py-2.5 text-sm font-medium text-[#374151] hover:bg-[#f8fafc] transition-colors">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>
              {p}
            </button>
          ))}
        </div>

        <div className="mt-6 flex justify-center gap-6 text-xs text-[#9ca3af]">
          {["SEGURO", "VERIFICADO", "RÁPIDO"].map(b => (
            <div key={b} className="flex flex-col items-center gap-1">
              <div className="w-6 h-6 rounded-full bg-[#f0f7ff] flex items-center justify-center">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#1a7eff" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              </div>
              <span>{b}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
