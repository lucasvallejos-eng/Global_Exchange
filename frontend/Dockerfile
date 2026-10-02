# Imagen de producción de la maqueta: se construye con Node y se sirve con
# nginx. Se usa desde docker-compose.prod.yml; ver docs/despliegue-produccion.md.

# 1) Construcción
FROM node:22-alpine AS construccion
WORKDIR /app
# La misma versión de pnpm que fija .mise.toml.
RUN npm install -g pnpm@10.34.3
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# La dirección del backend queda fija en el JavaScript al construir: el
# navegador de quien abre la página tiene que poder llegar a ella.
ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
RUN pnpm build

# 2) Servidor: solo los archivos construidos, sin Node ni dependencias.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=construccion /app/dist /usr/share/nginx/html
EXPOSE 80
