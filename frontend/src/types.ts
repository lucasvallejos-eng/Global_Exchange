export type Role = "cliente" | "cliente_general" | "cajero" | "analista_cambiario" | "administrador";

export interface User {
  name: string;
  email: string;
  role: Role;
  avatar?: string;
}

export interface UsuarioAsociable {
  id: number;
  username: string;
  nombre: string;
  email: string;
}

export interface Client {
  id: number;
  nombre: string;
  tipo: "Jurídica" | "Física";
  direccion: string;
  cuentaAcreditar: string;
  correo: string;
  usuarios: number[];
}

export const ROLE_LABELS: Record<Role, string> = {
  cliente: "Usuario Cliente",
  cliente_general: "Cliente General",
  cajero: "Cajero",
  analista_cambiario: "Analista Cambiario",
  administrador: "Administrador",
};
