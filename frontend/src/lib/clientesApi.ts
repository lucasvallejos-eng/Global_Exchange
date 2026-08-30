import { Client, UsuarioAsociable } from "../types";

const BACKEND = "http://localhost:8000";

function leerCookie(nombre: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${nombre}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detalle = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${detalle}`);
  }
  return res.json();
}

function headersConCsrf(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-CSRFToken": leerCookie("csrftoken"),
  };
}

export async function listClients(): Promise<Client[]> {
  const res = await fetch(`${BACKEND}/api/clientes/`, { credentials: "include" });
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
  if (!res.ok) throw new Error(`API error ${res.status}`);
}

export async function listUsuariosAsociables(): Promise<UsuarioAsociable[]> {
  const res = await fetch(`${BACKEND}/api/usuarios/`, { credentials: "include" });
  return unwrap(res);
}
