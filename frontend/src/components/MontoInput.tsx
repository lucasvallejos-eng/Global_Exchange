import { useLayoutEffect, useRef } from "react";

/**
 * Campo para montos con el formato de Paraguay: punto para los miles y coma
 * para los decimales (987.367 o 1.250,50). Los puntos se ponen solos al
 * escribir; si el usuario los escribe, se toman como separador de miles.
 *
 * El valor que entra y sale (``valor`` / ``onCambio``) es el número "crudo"
 * en texto, con punto decimal ("987367" o "1250.5"), listo para Number().
 */
export default function MontoInput({
  valor,
  onCambio,
  decimales = 0,
  className,
  placeholder,
}: {
  valor: string;
  onCambio: (valor: string) => void;
  decimales?: number;
  className?: string;
  placeholder?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  // Cuántos dígitos (y coma) había a la izquierda del cursor: al reformatear,
  // el cursor vuelve a quedar después de esos mismos caracteres.
  const significativosAntesDelCursor = useRef<number | null>(null);

  useLayoutEffect(() => {
    const input = ref.current;
    const objetivo = significativosAntesDelCursor.current;
    if (!input || objetivo === null) return;
    let vistos = 0;
    let posicion = 0;
    while (posicion < input.value.length && vistos < objetivo) {
      if (/[\d,]/.test(input.value[posicion])) vistos += 1;
      posicion += 1;
    }
    input.setSelectionRange(posicion, posicion);
    significativosAntesDelCursor.current = null;
  });

  return (
    <input
      ref={ref}
      type="text"
      inputMode={decimales > 0 ? "decimal" : "numeric"}
      value={formatear(valor)}
      placeholder={placeholder}
      className={className}
      onChange={(evento) => {
        const texto = evento.target.value;
        const cursor = evento.target.selectionStart ?? texto.length;
        significativosAntesDelCursor.current = texto.slice(0, cursor).replace(/[^\d,]/g, "").length;
        onCambio(normalizar(texto, decimales));
      }}
    />
  );
}

/** "1250.5" -> "1.250,5" */
function formatear(valor: string): string {
  if (!valor) return "";
  const [entero, decimal] = valor.split(".");
  const conMiles = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return decimal !== undefined ? `${conMiles},${decimal}` : conMiles;
}

/** Lo que escribió el usuario ("1.250,5") -> número crudo ("1250.5"). */
function normalizar(texto: string, decimales: number): string {
  const limpio = texto.replace(/[^\d,]/g, "");
  const [entero, ...resto] = limpio.split(",");
  const sinCeros = entero.replace(/^0+(?=\d)/, "");
  if (resto.length === 0 || decimales === 0) return sinCeros;
  return `${sinCeros || "0"}.${resto.join("").slice(0, decimales)}`;
}
