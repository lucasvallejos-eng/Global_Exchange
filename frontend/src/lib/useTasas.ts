import { useEffect, useState } from "react";
import { listarVigentes, type Cotizacion } from "./cotizacionesApi";
import type { Tasa } from "./clientRates";

/**
 * Cotizaciones vigentes, traídas de la base y refrescadas cada
 * `REFRESCO_MS` (y al volver a la pestaña), para que un cambio que hace el
 * analista se vea sin recargar la página.
 *
 * Reemplaza a la tabla `BASE_RATES` que estaba escrita a mano: ahora las
 * pantallas de compra, venta, cotizaciones y simulación muestran los precios
 * que un administrador cargó realmente en el sistema.
 */
export type MapaTasas = Record<string, Tasa>;

const REFRESCO_MS = 5000;

export function useTasas() {
  const [tasas, setTasas] = useState<MapaTasas>({});
  const [monedas, setMonedas] = useState<Cotizacion[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let vigente = true;

    const cargar = () => listarVigentes()
      .then((cotizaciones) => {
        if (!vigente) return;
        const mapa: MapaTasas = {};
        for (const c of cotizaciones) {
          mapa[c.codigo] = { compra: c.precioCompra, venta: c.precioVenta };
        }
        setTasas(mapa);
        setMonedas(cotizaciones);
        setError(null);
      })
      .catch((e: unknown) => {
        if (!vigente) return;
        setError(e instanceof Error ? e.message : "No se pudieron cargar las cotizaciones.");
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });

    void cargar();
    const intervalo = window.setInterval(() => void cargar(), REFRESCO_MS);
    const alVolver = () => {
      if (document.visibilityState === "visible") void cargar();
    };
    document.addEventListener("visibilitychange", alVolver);

    // Evita tocar el estado si la pantalla se cerró antes de que llegue la respuesta.
    return () => {
      vigente = false;
      window.clearInterval(intervalo);
      document.removeEventListener("visibilitychange", alVolver);
    };
  }, []);

  /** Códigos disponibles, para los selectores de moneda. */
  const codigos = monedas.map((m) => m.codigo);

  return { tasas, monedas, codigos, cargando, error };
}
