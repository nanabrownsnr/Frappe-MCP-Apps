// React browser entry point. Change the root component import when you rename
// the example UI, and keep the target ID aligned with index.html.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import "./style.css";

const root = document.querySelector("#root");
if (!root) {
    throw new Error("Missing #root element");
}

createRoot(root).render(
    <StrictMode>
        <App />
    </StrictMode>,
);
