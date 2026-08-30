import { useState } from "react";
import { User, Role, ROLE_LABELS } from "../types";
import ClientesModule from "./ClientesModule";

interface Props {
  user: User;
  onLogout: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const Icon = ({ path }: { path: string }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={path}/>
  </svg>
);

const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  cliente: [
    { id: "compra-divisas", label: "Compra de Divisas", icon: <Icon path="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/> },
    { id: "venta-divisas", label: "Venta de Divisas", icon: <Icon path="M7 12l5-5 5 5M7 17l5-5 5 5"/> },
    { id: "facturas", label: "Facturas", icon: <Icon path="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/> },
    { id: "historial", label: "Historial de Transacciones", icon: <Icon path="M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/> },
    { id: "configuracion", label: "Configuración de Datos", icon: <Icon path="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/> },
  ],
  cajero: [
    { id: "compra-divisas", label: "Compra de Divisas", icon: <Icon path="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/> },
    { id: "venta-divisas", label: "Venta de Divisas", icon: <Icon path="M7 12l5-5 5 5M7 17l5-5 5 5"/> },
  ],
  analista_cambiario: [
    { id: "monedas", label: "Monedas", icon: <Icon path="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/> },
  ],
  administrador: [
    { id: "monedas", label: "Monedas", icon: <Icon path="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/> },
    { id: "clientes", label: "Clientes", icon: <Icon path="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/> },
  ],
  cliente_general: [],
};

const PLACEHOLDER_TEXT: Record<string, string> = {
  "compra-divisas": "APARTADO DE COMPRA DE DIVISAS",
  "venta-divisas": "APARTADO DE VENTA DE DIVISAS",
  "facturas": "APARTADO DE FACTURAS",
  "historial": "APARTADO DE HISTORIAL DE TRANSACCIONES",
  "configuracion": "APARTADO DE CONFIGURACIÓN DE DATOS",
  "monedas": "APARTADO DE MONEDAS, DAR DE ALTA, BAJA Y CAMBIAR COTIZACIÓN",
};

const CLIENT_NAMES = ["María González", "Juan Pérez", "Roberto Silva", "Laura Martínez", "Andrea López"];

export default function DashboardLayout({ user, onLogout }: Props) {
  const navItems = NAV_BY_ROLE[user.role];
  const [activeSection, setActiveSection] = useState(navItems[0]?.id ?? "");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedClient, setSelectedClient] = useState(CLIENT_NAMES[0]);
  const [clientDropdown, setClientDropdown] = useState(false);

  const renderContent = () => {
    if (activeSection === "clientes" && user.role === "administrador") {
      return <ClientesModule />;
    }
    const text = PLACEHOLDER_TEXT[activeSection];
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="bg-white border-2 border-dashed border-[#e2e8f0] rounded-2xl p-16 text-center max-w-lg w-full">
          <div className="w-14 h-14 bg-[#f0f7ff] rounded-2xl flex items-center justify-center mx-auto mb-4">
            {navItems.find(n => n.id === activeSection)?.icon}
          </div>
          <p className="text-base font-bold text-[#374151] leading-relaxed">{text}</p>
          <p className="text-sm text-[#9ca3af] mt-2">Este módulo estará disponible próximamente.</p>
        </div>
      </div>
    );
  };

  const activeLabel = navItems.find(n => n.id === activeSection)?.label ?? "";

  return (
    <div className="flex h-screen bg-[#f0f4f8] overflow-hidden">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? "w-64" : "w-16"} transition-all duration-300 bg-white border-r border-[#e2e8f0] flex flex-col shadow-sm flex-shrink-0`}>
        {/* Logo */}
        <div className={`flex items-center gap-3 px-4 py-5 border-b border-[#f1f5f9] ${!sidebarOpen ? "justify-center" : ""}`}>
          <div className="w-8 h-8 rounded-full bg-[#1a7eff] flex items-center justify-center flex-shrink-0 shadow">
            <span className="text-white font-bold text-sm">$</span>
          </div>
          {sidebarOpen && <span className="text-base font-bold text-[#1a7eff] tracking-tight whitespace-nowrap">Global Exchange</span>}
        </div>

        {/* Role badge */}
        {sidebarOpen && (
          <div className="mx-3 mt-3 mb-1 px-3 py-2 bg-[#f0f7ff] rounded-xl">
            <p className="text-[10px] font-semibold text-[#1a7eff] uppercase tracking-widest">{ROLE_LABELS[user.role]}</p>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                activeSection === item.id
                  ? "bg-[#1a7eff] text-white shadow-sm"
                  : "text-[#4b5563] hover:bg-[#f0f4f8]"
              } ${!sidebarOpen ? "justify-center" : ""}`}
              title={!sidebarOpen ? item.label : undefined}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              {sidebarOpen && <span className="truncate">{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Logout */}
        <div className="px-2 pb-4 pt-2 border-t border-[#f1f5f9]">
          <button
            onClick={onLogout}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 transition-colors ${!sidebarOpen ? "justify-center" : ""}`}
            title={!sidebarOpen ? "Cerrar Sesión" : undefined}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            {sidebarOpen && "Cerrar Sesión"}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-[#e2e8f0] px-5 py-3 flex items-center justify-between shadow-sm flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg hover:bg-[#f0f4f8] transition-colors text-[#6b7280]"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
            </button>
            <div>
              <p className="text-xs text-[#9ca3af] font-medium">Panel de Control</p>
              <h1 className="text-sm font-semibold text-[#1a202c]">{activeLabel}</h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Notification bell */}
            <button className="relative p-2 rounded-lg hover:bg-[#f0f4f8] transition-colors text-[#6b7280]">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#1a7eff] rounded-full"/>
            </button>

            {/* Client dropdown (only for cliente role) */}
            {user.role === "cliente" && (
              <div className="relative">
                <button
                  onClick={() => setClientDropdown(!clientDropdown)}
                  className="flex items-center gap-2 border border-[#e2e8f0] rounded-xl px-3 py-2 text-sm font-medium text-[#374151] hover:bg-[#f8fafc] transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  {selectedClient}
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                {clientDropdown && (
                  <div className="absolute right-0 mt-1 w-52 bg-white border border-[#e2e8f0] rounded-xl shadow-lg z-20 overflow-hidden">
                    {CLIENT_NAMES.map(name => (
                      <button
                        key={name}
                        onClick={() => { setSelectedClient(name); setClientDropdown(false); }}
                        className={`w-full text-left px-4 py-2.5 text-sm hover:bg-[#f0f7ff] transition-colors ${name === selectedClient ? "text-[#1a7eff] font-semibold bg-[#f0f7ff]" : "text-[#374151]"}`}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* User avatar */}
            <div className="flex items-center gap-2.5">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-semibold text-[#1a202c] leading-tight">{user.name}</p>
                <p className="text-[10px] text-[#9ca3af]">{ROLE_LABELS[user.role]}</p>
              </div>
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#1a7eff] to-[#0052cc] flex items-center justify-center text-white font-bold text-sm shadow">
                {user.name.charAt(0)}
              </div>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          {renderContent()}
        </main>
      </div>

      {/* Overlay for client dropdown */}
      {clientDropdown && (
        <div className="fixed inset-0 z-10" onClick={() => setClientDropdown(false)}/>
      )}
    </div>
  );
}
