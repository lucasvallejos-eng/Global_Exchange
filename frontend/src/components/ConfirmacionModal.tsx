/**
 * Pide confirmación antes de una acción que no se puede deshacer (eliminar,
 * cancelar). Reemplaza al window.confirm del navegador para que se vea como el
 * resto de la app.
 */
export default function ConfirmacionModal({
  titulo,
  mensaje,
  textoConfirmar = "Eliminar",
  textoVolver = "Cancelar",
  procesando = false,
  onConfirmar,
  onCancelar,
}: {
  titulo: string;
  mensaje: string;
  textoConfirmar?: string;
  textoVolver?: string;
  procesando?: boolean;
  onConfirmar: () => void;
  onCancelar: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4" onClick={procesando ? undefined : onCancelar}>
      <div
        role="alertdialog"
        aria-labelledby="confirmacion-titulo"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
        onClick={(evento) => evento.stopPropagation()}
      >
        <h3 id="confirmacion-titulo" className="text-xl font-bold text-[#0f172a]">{titulo}</h3>
        <p className="mt-3 text-sm text-[#475569]">{mensaje}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancelar}
            disabled={procesando}
            className="rounded-xl border border-[#dbe3ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#374151] hover:bg-[#f8fafc]"
          >
            {textoVolver}
          </button>
          <button
            onClick={onConfirmar}
            disabled={procesando}
            className="rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 disabled:bg-slate-300"
          >
            {procesando ? "Procesando..." : textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
}
