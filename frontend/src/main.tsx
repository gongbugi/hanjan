import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { createDevAdapter } from "./auth/devAdapter";
import { createFirebaseAdapter } from "./auth/firebaseAdapter";
import { config } from "./config";
import "./styles.css";

const adapter = config.authMode === "firebase" ? createFirebaseAdapter() : createDevAdapter(config.devToken);
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const root = document.getElementById("root");
if (root === null) throw new Error("#root 요소가 없다");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider adapter={adapter}>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
