# Global Exchange — guía de arranque sin PyCharm

Esta guía sirve para levantar el proyecto sin usar PyCharm, directamente desde terminal.

## 1) Requisitos

- Git
- Docker Desktop instalado y corriendo
- Python 3.12+
- Node.js 20+

Verificá que ambos estén disponibles en la terminal:

```bash
python --version
node --version
npm --version
docker --version
```

---

## 2) Clonar el repositorio

```bash
git clone <url-del-repo>
cd Global_Exchange
```

---

## 3) Levantar Keycloak

Desde la raíz del proyecto:

```bash
cd keycloak
docker compose up -d
```

Verificá que responda:

```bash
curl http://localhost:8080/realms/GlobalExchange
```

Si responde con JSON, Keycloak está levantado.

---

## 4) Backend Django

Entrá a la carpeta backend:

```bash
cd ../backend
python -m venv .venv
```

### Windows (PowerShell / CMD)

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux / Mac

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Crear el archivo .env local

Copia el ejemplo:

```bash
copy .env.example .env
```

o en Linux/Mac:

```bash
cp .env.example .env
```

Completa el archivo `.env` con el secret real de Keycloak:

```env
DJANGO_SECRET_KEY=clave-local
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

KEYCLOAK_ISSUER=http://localhost:8080/realms/GlobalExchange
KEYCLOAK_WEB_CLIENT_ID=global-exchange-web
KEYCLOAK_WEB_CLIENT_SECRET=<secret_de_keycloak>
MAQUETA_URL=http://localhost:8443/
```

Entonces ejecutá:

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

La app quedará en:

- http://localhost:8000

---

## 5) Frontend Vite

Abrí otra terminal y ejecutá:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 8443
```

O si usás pnpm:

```bash
cd frontend
npx pnpm install
npx pnpm dev --host 0.0.0.0 --port 8443
```

La app quedará en:

- http://localhost:8443

---

## 6) Importantísimo antes de subir al repositorio

No se deben subir estos archivos ni carpetas:

- `.env`
- `backend/.env`
- `backend/.venv/`
- `frontend/node_modules/`
- `frontend/package-lock.json` (si el equipo usa pnpm)
- `db.sqlite3`
- `__pycache__/`
- logs
- `.idea/`

El repositorio ya tiene `.gitignore` configurado para excluirlos.

Para revisar: 

```bash
git status
```

Si querés confirmar que no hay secretos ni archivos locales,
revisá que no aparezcan archivos `.env` ni `node_modules` ni `.venv`.

---

## 7) Flujo para trabajar en equipo

```bash
git pull
# hacer cambios
git add .
git commit -m "mensaje"
git push
```

---

## 8) Problemas comunes

### Error: "invalid_client"

Es porque `KEYCLOAK_WEB_CLIENT_SECRET` no coincide con el client de Keycloak.

Solución:

1. Entrar a Keycloak
2. Ir a `Clients > global-exchange-web > Credentials`
3. Copiar el secret exacto
4. Actualizar `backend/.env`
5. Reiniciar backend

### Error: `redirect_uri` inválido

Usar siempre:

- http://localhost:8000/
- no http://127.0.0.1:8000/

### Puerto ocupado

```bash
# Windows PowerShell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000,8443,8080 }
```

Y si hace falta:

```powershell
Stop-Process -Id <PID> -Force
```

---

## 9) Estado final esperado

Cuando todo va bien:

- Keycloak: http://localhost:8080
- Backend: http://localhost:8000
- Frontend: http://localhost:8443

Todo esto sin necesidad de abrir PyCharm.
