import { useMemo } from "react";
import { ToolCallProvider, useToolCall } from "./components/tool-call-provider";
import Pipeline from "./components/pipeline";

export default function App() {
  return (
    <ToolCallProvider>
      <MCPView />
    </ToolCallProvider>
  );
}

function MCPView() {
  const { error, isConnected, toolCall } = useToolCall();

  const render = useMemo(() => {
    if (!toolCall) return null;
    if (toolCall.status === "idle") return;
    if (toolCall.status === "running") {
      return <div>Running...</div>;
    }
    if (toolCall.status === "error") {
      return <div>Error...</div>;
    }

    const toolName = toolCall.result?._meta?.toolname;
    const structuredContent = toolCall.result?.structuredContent!;

    if (toolName === "frappe_list") {
      switch (structuredContent.doctype) {
        case "CRM Deal": {
          return <Pipeline structuredContent={structuredContent} />;
        }
        default: {
          return null;
        }
      }
    }

    return null;
  }, []);

  if (error || !isConnected) {
    return (
      <main className="min-h-svh w-full bg-host-bg p-4 text-host-text">
        <p>{error ? error.message : "Connecting to MCP…"}</p>
      </main>
    );
  }

  return (
    <main className="min-h-svh w-full bg-host-bg text-host-text relative">
      {render}
    </main>
  );
}
