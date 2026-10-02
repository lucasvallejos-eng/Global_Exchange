import { User } from "../types";
import MediosPagoModule from "./MediosPagoModule";

// Los datos del usuario y su contraseña viven en Keycloak (RN05: los
// formularios de credenciales los dibuja Keycloak). Acá solo se muestran los
// datos de la sesión actual y se ofrece ir a la consola de cuenta para
// modificarlos.

type Props = {
  user: User;
};

const ROLE_LABELS: Record<User["role"], string> = {
  administrador: "Administrador",
  analista_cambiario: "Analista cambiario",
  cajero: "Cajero",
  cliente: "Cliente",
};

function Dato({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="mb-2 block text-sm font-medium text-[#374151]">{label}</span>
      <div className="w-full rounded-xl border border-[#dbe3ee] bg-white px-3 py-2.5 text-sm text-[#1f2937]">
        {value || "—"}
      </div>
    </div>
  );
}

export default function ConfiguracionDatosModule({ user }: Props) {
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
              <Dato label="Nombre" value={user.name} />
              <Dato label="Nombre de Usuario" value={user.username ?? ""} />
              <Dato label="Correo Electrónico" value={user.email} />
              <Dato label="Rol" value={ROLE_LABELS[user.role]} />
            </div>
          </div>

          <div className="flex flex-col rounded-2xl border border-[#e2e8f0] bg-[#f8fafc] p-5">
            <h3 className="text-lg font-semibold text-[#0f172a]">Seguridad</h3>

            <p className="mt-5 text-sm text-[#475569]">
              Tu cuenta la administra el servidor de identidad (Keycloak). Desde ahí podés
              cambiar tu contraseña y actualizar tu nombre o correo; los cambios se reflejan
              acá la próxima vez que inicies sesión.
            </p>

            {user.cuentaUrl && (
              <a
                href={user.cuentaUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 block w-full rounded-xl bg-[#0f172a] px-4 py-2.5 text-center text-sm font-semibold text-white shadow-sm transition hover:bg-[#1e293b]"
              >
                Cambiar contraseña o datos de la cuenta
              </a>
            )}
          </div>
        </div>
      </div>

      <div id="medios-pago-config">
        <MediosPagoModule />
      </div>
    </div>
  );
}
