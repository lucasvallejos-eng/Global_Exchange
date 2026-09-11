import { useMemo, useState } from "react";
import MediosPagoModule from "./MediosPagoModule";

const initialProfile = {
  username: "juan123",
  email: "juan.perez@email.com",
};

const initialPasswordState = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
};

const isValidUsername = (value: string) => /^[a-zA-Z0-9_]{4,}$/.test(value);
const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
const isStrongPassword = (value: string) => /^(?=.*[A-Z])(?=.*\d).{8,}$/.test(value);

export default function ConfiguracionDatosModule() {
  const [profile, setProfile] = useState(initialProfile);
  const [passwords, setPasswords] = useState(initialPasswordState);
  const [profileErrors, setProfileErrors] = useState<{ username?: string; email?: string }>({});
  const [passwordErrors, setPasswordErrors] = useState<{ currentPassword?: string; newPassword?: string; confirmPassword?: string }>({});
  const [toast, setToast] = useState<string | null>(null);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const passwordStrength = useMemo(() => {
    const value = passwords.newPassword;

    if (!value) return { label: "Sin contraseña", color: "bg-slate-200 text-slate-500" };
    if (value.length < 8) return { label: "Débil", color: "bg-red-100 text-red-600" };
    if (isStrongPassword(value)) return { label: "Fuerte", color: "bg-green-100 text-green-700" };
    return { label: "Media", color: "bg-yellow-100 text-yellow-700" };
  }, [passwords.newPassword]);

  const validateProfile = () => {
    const nextErrors: { username?: string; email?: string } = {};

    if (!isValidUsername(profile.username)) {
      nextErrors.username = "El nombre de usuario debe tener al menos 4 caracteres, sin espacios ni caracteres especiales.";
    }

    if (!isValidEmail(profile.email)) {
      nextErrors.email = "El formato de correo no es válido.";
    }

    setProfileErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const validatePassword = () => {
    const nextErrors: { currentPassword?: string; newPassword?: string; confirmPassword?: string } = {};

    if (!passwords.currentPassword.trim()) {
      nextErrors.currentPassword = "Debe ingresar su contraseña actual.";
    }

    if (!isStrongPassword(passwords.newPassword)) {
      nextErrors.newPassword = "La nueva contraseña debe tener al menos 8 caracteres, una mayúscula y un número.";
    }

    if (passwords.confirmPassword !== passwords.newPassword) {
      nextErrors.confirmPassword = "Las contraseñas no coinciden.";
    }

    setPasswordErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleProfileSave = () => {
    if (!validateProfile()) {
      return;
    }

    setToast("Datos de usuario actualizados correctamente.");
    setTimeout(() => setToast(null), 2600);
  };

  const handlePasswordSave = () => {
    if (!validatePassword()) {
      return;
    }

    setPasswords({ currentPassword: "", newPassword: "", confirmPassword: "" });
    setPasswordErrors({});
    setToast("Contraseña modificada con éxito.");
    setTimeout(() => setToast(null), 2600);
  };

  const renderPasswordInput = (
    label: string,
    value: string,
    onChange: (value: string) => void,
    show: boolean,
    toggleShow: () => void,
    error?: string,
    placeholder?: string,
  ) => (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-[#374151]">{label}</span>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-xl border border-[#dbe3ee] bg-[#f8fafc] px-3 py-2.5 pr-10 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
        />
        <button
          type="button"
          onClick={toggleShow}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-[#64748b]"
        >
          {show ? "Ocultar" : "Mostrar"}
        </button>
      </div>
      {error && <span className="mt-1 block text-xs font-medium text-red-600">{error}</span>}
    </label>
  );

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-[#dbe3ee] bg-white p-6 shadow-sm">
        <div className="mb-5">
          <p className="text-sm font-medium text-[#64748b]">Configuración</p>
          <h2 className="text-2xl font-bold tracking-tight text-[#0f172a]">Datos de usuario</h2>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <div className="rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-5">
            <h3 className="text-lg font-semibold text-[#0f172a]">Datos del perfil</h3>

            <div className="mt-5 space-y-4">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Nombre de Usuario</span>
                <input
                  value={profile.username}
                  onChange={(e) => setProfile((prev) => ({ ...prev, username: e.target.value }))}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
                {profileErrors.username && <span className="mt-1 block text-xs font-medium text-red-600">{profileErrors.username}</span>}
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[#374151]">Correo Electrónico</span>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile((prev) => ({ ...prev, email: e.target.value }))}
                  className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937] outline-none focus:border-[#1a7eff]"
                />
                {profileErrors.email && <span className="mt-1 block text-xs font-medium text-red-600">{profileErrors.email}</span>}
              </label>

              <button
                onClick={handleProfileSave}
                className="w-full rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#176ae6]"
              >
                Guardar Cambios de Perfil
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-5">
            <h3 className="text-lg font-semibold text-[#0f172a]">Seguridad</h3>

            <div className="mt-5 space-y-4">
              {renderPasswordInput(
                "Contraseña Actual",
                passwords.currentPassword,
                (value) => setPasswords((prev) => ({ ...prev, currentPassword: value })),
                showCurrentPassword,
                () => setShowCurrentPassword((prev) => !prev),
                passwordErrors.currentPassword,
                "Ingrese su contraseña actual",
              )}

              {renderPasswordInput(
                "Nueva Contraseña",
                passwords.newPassword,
                (value) => setPasswords((prev) => ({ ...prev, newPassword: value })),
                showNewPassword,
                () => setShowNewPassword((prev) => !prev),
                passwordErrors.newPassword,
                "Mínimo 8 caracteres",
              )}

              <div className="rounded-xl border border-[#e2e8f0] bg-white p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748b]">Fortaleza</span>
                  <span className={`rounded-full px-2 py-1 text-[10px] font-bold ${passwordStrength.color}`}>
                    {passwordStrength.label}
                  </span>
                </div>
              </div>

              {renderPasswordInput(
                "Confirmar Nueva Contraseña",
                passwords.confirmPassword,
                (value) => setPasswords((prev) => ({ ...prev, confirmPassword: value })),
                showConfirmPassword,
                () => setShowConfirmPassword((prev) => !prev),
                passwordErrors.confirmPassword,
                "Repita la nueva contraseña",
              )}

              <button
                onClick={handlePasswordSave}
                className="w-full rounded-xl bg-[#0f172a] px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#1e293b]"
              >
                Actualizar Contraseña
              </button>
            </div>
          </div>
        </div>
      </div>

      <div id="medios-pago-config">
        <MediosPagoModule />
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-[60] rounded-xl bg-[#0f172a] px-4 py-3 text-sm font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
