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

export type ToolCall = {
  id: string;
  arguments?: Record<string, unknown>;
  result: ResultType | null;
  status: "idle" | "running" | "completed" | "error";
};

// Define the shape of your context
interface ToolCallContextType {
  app: ReturnType<typeof useApp>["app"];
  toolCall: ToolCall | null;
  canGoBack: boolean;
  setToolCall: (toolCall: ToolCall) => void;
  popToolCall: () => void;
  isConnected: boolean;
  error: Error | null;
}

export const ToolCallContext = createContext<ToolCallContextType | null>(null);

export function ToolCallProvider({ children }: { children: React.ReactNode }) {
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);

  const toolCall = useMemo(() => toolCalls.at(-1) ?? null, [toolCalls]);
  const canGoBack = useMemo(() => toolCalls.length > 1, [toolCalls]);

  const setToolCall = useCallback((toolCall: ToolCall) => {
    setToolCalls((prev) => [...prev, toolCall]);
  }, []);

  const popToolCall = useCallback(() => {
    setToolCalls((prev) => prev.slice(0, -1));
  }, []);

  const onAppCreated = useCallback((createdApp: App) => {
    createdApp.ontoolresult = (result) => {
      setToolCalls((prev) => {
        return [
          ...prev,
          {
            id: generateId(),
            result: result,
            status: "completed",
          } as ToolCall,
        ];
      });
    };

    createdApp.ontoolcancelled = () => {
      setToolCalls((prev) => {
        if (prev.length === 0)
          return [
            { id: generateId(), result: null, status: "error" } as ToolCall,
          ];
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], status: "error" };
        return next;
      });
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
  useDocumentTheme();

  const value = useMemo(
    () =>
      ({
        app,
        toolCall,
        canGoBack,
        setToolCall,
        popToolCall,
        isConnected,
        error,
      } satisfies ToolCallContextType),
    [app, toolCall, setToolCall, popToolCall, isConnected, error]
  );

  return (
    <ToolCallContext.Provider value={value}>
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
