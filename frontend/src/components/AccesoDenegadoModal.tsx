import { useEffect, useState } from "react";
import { EVENTO_ACCESO_DENEGADO } from "../lib/api";

/**
 * Aviso para cuando el backend rechaza un pedido porque el usuario no tiene
 * el rol necesario. Normalmente el menú ya oculta lo que no le corresponde,
 * así que esto aparece si le quitaron un rol en Keycloak a mitad de sesión.
 * Se monta una sola vez (en App) y escucha el evento que dispara lib/api.ts.
 */
export default function AccesoDenegadoModal() {
  const [detalle, setDetalle] = useState<string | null>(null);

  useEffect(() => {
    const abrir = (evento: Event) => setDetalle((evento as CustomEvent<string>).detail ?? "");
    window.addEventListener(EVENTO_ACCESO_DENEGADO, abrir);
    return () => window.removeEventListener(EVENTO_ACCESO_DENEGADO, abrir);
  }, []);

  if (detalle === null) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4">
      <div role="alertdialog" aria-labelledby="acceso-denegado-titulo" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 inline-flex rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
          Acceso denegado
        </div>
        <h3 id="acceso-denegado-titulo" className="text-2xl font-bold text-[#0f172a]">
          No tenés permiso para esta acción
        </h3>
        <p className="mt-3 text-sm text-[#475569]">
          Tu usuario no tiene el rol necesario. Si creés que es un error, pedile a un administrador que te lo asigne.
        </p>

        {detalle && (
          <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{detalle}</div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={() => setDetalle(null)}
            className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
          >
            Cerrar
          </button>
          <button
            onClick={() => window.location.reload()}
            className="rounded-xl bg-[#1a7eff] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#146be7]"
          >
            Volver al inicio
          </button>
        </div>
      </div>
    </div>
  );
}
