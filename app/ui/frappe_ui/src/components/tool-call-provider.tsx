import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  App,
  useApp,
  useDocumentTheme,
  useHostFonts,
  useHostStyleVariables,
} from "@modelcontextprotocol/ext-apps/react";
import type { ResultType } from "@/types/response-types";
import { generateId } from "@/lib/utils";

type ToolCall = {
  arguments?: Record<string, unknown>;
  result: ResultType | null;
  status: "idle" | "running" | "completed" | "error";
};

// Define the shape of your context
interface ToolCallContextType {
  app: ReturnType<typeof useApp>["app"];
  toolCall: ToolCall | null;
  isConnected: boolean;
  error: Error | null;
}

const ToolCallContext = createContext<ToolCallContextType>({
  app: null,
  toolCall: null,
  isConnected: false,
  error: null,
});

export function ToolCallProvider({ children }: { children: React.ReactNode }) {
  const [toolCall, setToolCall] = useState<ToolCall | null>(null);

  const onAppCreated = useCallback((createdApp: App) => {
    // createdApp.ontoolinput = (input) => {
    //   setToolCall({
    //     arguments: input.arguments,
    //     result: null,
    //     status: "running",
    //   });
    // };

    createdApp.ontoolresult = (result) => {
      console.log("result", result);
      setToolCall({
        result: result as ResultType,
        status: "completed",
      });
    };

    // createdApp.ontoolcancelled = () => {
    //   setToolCall((prev) => (prev ? { ...prev, status: "error" } : null));
    // };
  }, []);

  const { app, isConnected, error } = useApp({
    appInfo: { name: "twynity-frappe-dashboard", version: "1.0.0" },
    capabilities: {},
    onAppCreated,
    autoResize: true,
  });

  useHostStyleVariables(app, app?.getHostContext());
  useHostFonts(app, app?.getHostContext());
  useDocumentTheme();

  return (
    <ToolCallContext.Provider value={{ app, toolCall, isConnected, error }}>
      {children}
    </ToolCallContext.Provider>
  );
}

// Custom hook to consume the tool context globally
export function useToolCall() {
  const context = useContext(ToolCallContext);
  if (!context) {
    throw new Error("useToolCall must be used within a ToolCallProvider");
  }
  return context;
}
