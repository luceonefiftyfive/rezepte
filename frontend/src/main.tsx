import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ReactKeycloakProvider } from "@react-keycloak/web";
import App from "./App";
import "./styles.css";
import keycloak from "./keycloak";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element with id 'root' was not found.");
}

// Detect Web Crypto availability (required for PKCE S256). PKCE S256
// requires the SubtleCrypto API which is available on secure contexts
// (https) or on localhost in most browsers.
const supportsWebCrypto =
  typeof window !== "undefined" && !!(window.crypto && (window.crypto as any).subtle);

const initOptions: any = { onLoad: "check-sso" };
if (supportsWebCrypto) {
  initOptions.pkceMethod = "S256";
} else {
  // Fallback: do not set pkceMethod so Keycloak will not attempt S256.
  // This avoids the "Web Crypto API is not available" exception on
  // non-secure contexts or older browsers. Prefer serving over HTTPS.
  // eslint-disable-next-line no-console
  console.warn(
    "Web Crypto API not available; falling back from PKCE S256. Serve the app over HTTPS or use localhost to enable S256."
  );
}

createRoot(rootElement).render(
  <StrictMode>
    <ReactKeycloakProvider authClient={keycloak} initOptions={initOptions}>
      <App />
    </ReactKeycloakProvider>
  </StrictMode>
);