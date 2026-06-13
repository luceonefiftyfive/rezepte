import Keycloak from "keycloak-js";

const keycloak = new Keycloak({
  url: (import.meta.env.VITE_KEYCLOAK_URL as string) || "http://localhost:8080/auth",
  realm: (import.meta.env.VITE_KEYCLOAK_REALM as string) || "rezepte",
  clientId: (import.meta.env.VITE_KEYCLOAK_CLIENT_ID as string) || "frontend"
});

export default keycloak;
