import { useCallback, useMemo, useState } from "react";
import {
  useApp,
  useDocumentTheme,
  useHostFonts,
  useHostStyleVariables,
  type App as McpApp,
} from "@modelcontextprotocol/ext-apps/react";
import type { StructuredContent } from "./types/response-types";
import { Button } from "@/components/ui/button";
import Pipeline from "./components/pipeline";

export default function App() {
  const [structuredContent, setStructuredContent] =
    useState<StructuredContent | null>(null);

  const onAppCreated = useCallback((createdApp: McpApp) => {
    createdApp.ontoolresult = (result) => {
      const payload = (result.structuredContent as StructuredContent) ?? null;
      setStructuredContent(payload);
    };
  }, []);

  const { app, isConnected, error } = useApp({
    appInfo: { name: "twynity-frappe-dashboard", version: "1.0.0" },
    capabilities: {},
    onAppCreated,
    autoResize: true,
  });

  useHostStyleVariables(app, app?.getHostContext());
  useHostFonts(app, app?.getHostContext());
  const theme = useDocumentTheme();

  const render = useMemo(() => {
    if (!structuredContent || !error || isConnected) return null;
    switch (structuredContent.doctype) {
      case "CRM Deal": {
        return <Pipeline structuredContent={structuredContent} />;
      }
      default: {
        return null;
      }
    }
  }, []);

  if (error) {
    return (
      <main
        className="min-h-svh w-full bg-host-text p-4 text-host-text"
        data-host-theme={theme}
        aria-live="polite"
      >
        <p>{error.message}</p>
        <Button>Refresh</Button>
      </main>
    );
  }

  if (!isConnected) {
    return (
      <main
        className="min-h-svh w-full bg-host-bg p-4 text-host-text"
        data-host-theme={theme}
        aria-live="polite"
      >
        <p>Connecting to MCP…</p>
      </main>
    );
  }

  return (
    <main className="min-h-svh w-full bg-host-bg text-host-text">{render}</main>
  );
}
