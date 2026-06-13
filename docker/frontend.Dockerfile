FROM node:22-alpine AS build

WORKDIR /app

ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM
ARG VITE_KEYCLOAK_CLIENT_ID

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .

# Create a .env file so Vite picks up the VITE_* variables at build time
RUN echo "VITE_KEYCLOAK_URL=${VITE_KEYCLOAK_URL}" > .env \
	&& echo "VITE_KEYCLOAK_REALM=${VITE_KEYCLOAK_REALM}" >> .env \
	&& echo "VITE_KEYCLOAK_CLIENT_ID=${VITE_KEYCLOAK_CLIENT_ID}" >> .env

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
