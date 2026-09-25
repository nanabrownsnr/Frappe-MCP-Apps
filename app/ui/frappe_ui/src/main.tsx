// React browser entry point. Change the root component import when you rename
// the example UI, and keep the target ID aligned with index.html.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import "./style.css";
import LocalApp from "./LocalApp.tsx";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient();

const root = document.querySelector("#root");
if (!root) {
  throw new Error("Missing #root element");
}

if (import.meta.env.MODE === "development") {
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <LocalApp />
      </QueryClientProvider>
    </StrictMode>
  );
} else {
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </StrictMode>
  );
}
