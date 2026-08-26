export type Role = "cliente" | "cajero" | "analista" | "admin";

export type View = "login" | "register" | "dashboard";

export interface User {
  name: string;
  email: string;
  role: Role;
  avatar?: string;
}

export interface Client {
  id: string;
  nombre: string;
  tipo: "Jurídica" | "Física";
  direccion: string;
  cuentaAcreditar: string;
  correo: string;
  usuarioAsociado?: string;
}

export const DEMO_USERS: Record<string, User> = {
  "cliente@global.com": { name: "María González", email: "cliente@global.com", role: "cliente" },
  "cajero@global.com": { name: "Luis Ramírez", email: "cajero@global.com", role: "cajero" },
  "analista@global.com": { name: "Ana Fernández", email: "analista@global.com", role: "analista" },
  "admin@global.com": { name: "Carlos Benítez", email: "admin@global.com", role: "admin" },
};

export const ROLE_LABELS: Record<Role, string> = {
  cliente: "Usuario Cliente",
  cajero: "Cajero",
  analista: "Analista Cambiario",
  admin: "Administrador",
};
