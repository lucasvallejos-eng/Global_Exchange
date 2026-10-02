export type Role = "cliente" | "cajero" | "analista_cambiario" | "administrador";
export type ClientCategory = "Minorista" | "Mayorista" | "VIP";

export interface ClienteAsignado {
  id: string;
  razonSocial: string;
  tipoPersona: "Física" | "Jurídica";
  tipoCliente: ClientCategory | string | null;
  descuentoCompra: number | null;
}

export interface User {
  name: string;
  username?: string;
  email: string;
  // Consola de cuenta de Keycloak (datos personales y contraseña).
  cuentaUrl?: string;
  role: Role;
  avatar?: string;
  clientesAsignados?: ClienteAsignado[];
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
  // Id del segmento (app `comisiones`) del que salen la comisión y el
  // descuento del cliente; null si todavía no tiene uno asignado.
  segmento: number | null;
  direccion: string;
  cuentaAcreditar: string;
  correo: string;
  usuarios: number[];
  // Lo calcula el backend a partir del segmento; solo se muestra.
  porcentajeComision?: string | null;
}

export const DEMO_USERS: Record<string, User> = {
  "cliente@global.com": {
    name: "Juan Pérez",
    email: "cliente@global.com",
    role: "cliente",
    clientesAsignados: [
      { id: "CLI-101", razonSocial: "ABC SRL", tipoPersona: "Jurídica", tipoCliente: "Mayorista" },
      { id: "CLI-102", razonSocial: "TIGO SA", tipoPersona: "Jurídica", tipoCliente: "VIP" },
      { id: "CLI-103", razonSocial: "Horacio Cartes", tipoPersona: "Física", tipoCliente: "VIP" },
      { id: "CLI-104", razonSocial: "Santi Peña", tipoPersona: "Física", tipoCliente: "Minorista" },
    ],
  },
  "cajero@global.com": { name: "Cajero Demo", email: "cajero@global.com", role: "cajero" },
  "analista@global.com": { name: "Analista Demo", email: "analista@global.com", role: "analista_cambiario" },
  "admin@global.com": { name: "Admin Demo", email: "admin@global.com", role: "administrador" },
};

export const ROLE_LABELS: Record<Role, string> = {
  cliente: "Cliente",
  cajero: "Cajero",
  analista_cambiario: "Analista Cambiario",
  administrador: "Administrador",
};
