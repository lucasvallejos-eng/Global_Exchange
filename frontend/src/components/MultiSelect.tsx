import { useEffect, useRef, useState } from "react";

interface Option {
  value: string;
  label: string;
}

interface Props {
  options: Option[];
  selected: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}

export default function MultiSelect({ options, selected, onChange, placeholder = "Seleccionar..." }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const toggle = (value: string) => {
    onChange(selected.includes(value) ? selected.filter(v => v !== value) : [...selected, value]);
  };

  const labels = options.filter(o => selected.includes(o.value)).map(o => o.label);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full px-3 py-2.5 rounded-lg border border-[#e2e8f0] text-sm text-left focus:outline-none focus:ring-2 focus:ring-[#1a7eff] transition bg-white flex items-center justify-between gap-2"
      >
        <span className={`truncate ${labels.length ? "text-[#1a202c]" : "text-[#9ca3af]"}`}>
          {labels.length ? labels.join(", ") : placeholder}
        </span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" className="shrink-0">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-[#e2e8f0] rounded-lg shadow-lg max-h-56 overflow-y-auto">
          {options.length === 0 && (
            <p className="text-xs text-[#9ca3af] px-3 py-2.5">No hay usuarios disponibles.</p>
          )}
          {options.map(o => (
            <label key={o.value} className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-[#f8fafc] cursor-pointer">
              <input
                type="checkbox"
                checked={selected.includes(o.value)}
                onChange={() => toggle(o.value)}
                className="rounded border-[#e2e8f0] text-[#1a7eff] focus:ring-[#1a7eff]"
              />
              {o.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
