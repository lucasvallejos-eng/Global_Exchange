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
  "cliente_general",
];

function elegirRol(roles: string[]): Role {
  for (const rol of PRIORIDAD_ROLES) {
    if (roles.includes(rol)) return rol;
  }
  return "cliente";
}

export default function App() {
  const [cargando, setCargando] = useState(true);
  const [usuario, setUsuario] = useState<User | null>(null);

  useEffect(() => {
    // Preguntamos al backend quién está logueado (manda la cookie de sesión).
    fetch(`${BACKEND}/api/me/`, { credentials: "include" })
      .then(async (res) => {
        if (res.status === 200) {
          const data = await res.json();
          setUsuario({
            name: data.nombre || data.username,
            email: data.email || "",
            role: elegirRol(data.roles || []),
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
