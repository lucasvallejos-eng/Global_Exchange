import { useEffect, useState } from "react";
import { Role, User } from "./types";
import DashboardLayout from "./components/DashboardLayout";

// Backend Django que maneja el login con Keycloak.
const BACKEND = "http://localhost:8000";

// Si el usuario tiene varios roles, este orden decide cuál manda para el menú
// (el de mayor privilegio primero).
const PRIORIDAD_ROLES: Role[] = [
  "administrador",
  "analista_cambiario",
  "cajero",
  "cliente",
];

function elegirRol(roles: string[]): Role {
  for (const rol of PRIORIDAD_ROLES) {
    if (roles.includes(rol)) return rol;
  }
  return "cliente"; // fallback, no debería pasar: "cliente" es el rol por defecto en Keycloak
}

export default function App() {
  const [cargando, setCargando] = useState(true);
  const [usuario, setUsuario] = useState<User | null>(null);

  useEffect(() => {
    fetch(`${BACKEND}/api/me/`, { credentials: "include" })
      .then(async (res) => {
        if (res.status === 200) {
          const data = await res.json();
          setUsuario({
            name: data.nombre || data.username,
            email: data.email || "",
            role: elegirRol(data.roles || []),
            // Django ya limita esta lista a los clientes asociados al usuario.
            // No descartamos asociaciones por la etiqueta del segmento.
            clientesAsignados: data.clientesAsignados || [],
          });
          setCargando(false);
        } else {
          // No autenticado -> al login de Keycloak (vía Django).
          window.location.href = `${BACKEND}/`;
        }
      })
      .catch(() => {
        // Si el backend no responde, también mandamos al login.
        window.location.href = `${BACKEND}/`;
      });

    // Solo para levantar el frontend sin autenticación:
    // setUsuario({
    //   name: "Juan Pérez",
    //   email: "cliente@global.com",
    //   role: "cliente",
    //   clientesAsignados: [
    //     { id: "CLI-101", razonSocial: "ABC SRL", tipoPersona: "Jurídica", tipoCliente: "Mayorista" },
    //     { id: "CLI-102", razonSocial: "TIGO SA", tipoPersona: "Jurídica", tipoCliente: "VIP" },
    //     { id: "CLI-103", razonSocial: "Horacio Cartes", tipoPersona: "Física", tipoCliente: "VIP" },
    //     { id: "CLI-104", razonSocial: "Santi Peña", tipoPersona: "Física", tipoCliente: "Minorista" },
    //   ],
    // });
    // setCargando(false);
  }, []);

  const cerrarSesion = () => {
    window.location.href = `${BACKEND}/logout/`;
  };

  if (cargando || !usuario) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
          color: "#718096",
        }}
      >
        Cargando…
      </div>
    );
  }

  return <DashboardLayout user={usuario} onLogout={cerrarSesion} />;
}
