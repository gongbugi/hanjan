const env = import.meta.env;

export const config = {
  apiBaseUrl: (env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, ""),
  authMode: env.VITE_AUTH_MODE === "firebase" ? "firebase" : "dev",
  devToken: env.VITE_DEV_TOKEN ?? "dev-admin",
  firebase: {
    apiKey: env.VITE_FIREBASE_API_KEY ?? "",
    authDomain: env.VITE_FIREBASE_AUTH_DOMAIN ?? "",
    projectId: env.VITE_FIREBASE_PROJECT_ID ?? "",
    appId: env.VITE_FIREBASE_APP_ID ?? "",
  },
} as const;
