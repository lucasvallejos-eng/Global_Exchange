import { Client, UsuarioAsociable } from "../types";

import { BACKEND, headersConCsrf, unwrap } from "./api";

export async function listClients(): Promise<Client[]> {
  const res = await fetch(`${BACKEND}/api/clientes/`, { credentials: "include" });
  return unwrap(res);
}

export type TasaPreferencial = {
  clienteId: number;
  categoria: string | null;
  porcentajePreferencial: string;
};

export async function getClientPreferredRate(id: number): Promise<TasaPreferencial> {
  const res = await fetch(`${BACKEND}/api/clientes/${id}/tasa-preferencial/`, { credentials: "include" });
  return unwrap(res);
}

export async function createClient(cliente: Omit<Client, "id">): Promise<Client> {
  const res = await fetch(`${BACKEND}/api/clientes/`, {
    method: "POST",
    credentials: "include",
    headers: headersConCsrf(),
    body: JSON.stringify(cliente),
  });
  return unwrap(res);
}

export async function updateClient(id: Client["id"], cliente: Omit<Client, "id">): Promise<Client> {
  const res = await fetch(`${BACKEND}/api/clientes/${id}/`, {
    method: "PATCH",
    credentials: "include",
    headers: headersConCsrf(),
    body: JSON.stringify(cliente),
  });
  return unwrap(res);
}

export async function deleteClient(id: Client["id"]): Promise<void> {
  const res = await fetch(`${BACKEND}/api/clientes/${id}/`, {
    method: "DELETE",
    credentials: "include",
    headers: headersConCsrf(),
  });
  if (!res.ok) await unwrap(res);
}

export async function listUsuariosAsociables(): Promise<UsuarioAsociable[]> {
  const res = await fetch(`${BACKEND}/api/usuarios/`, { credentials: "include" });
  return unwrap(res);
}
