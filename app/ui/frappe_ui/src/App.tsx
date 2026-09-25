import { useMemo } from "react";
import { ToolCallProvider, useToolCall } from "./components/tool-call-provider";
import Pipeline from "./components/pipeline";
import type {
  CRMDealList,
  FrappeGet,
  FrappeList,
} from "./types/response-types";
import FrappeListView from "./components/frappe-list-view";
import FrappeGetView from "./components/frappe-get-view";

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
        // case "CRM Deal": {
        //   return (
        //     <Pipeline structuredContent={structuredContent as CRMDealList} />
        //   );
        // }
        default: {
          return (
            <FrappeListView
              structuredContent={structuredContent as FrappeList}
            />
          );
        }
      }
    }

    if (toolName === "frappe_get") {
      switch (structuredContent.doctype) {
        default: {
          return (
            <FrappeGetView structuredContent={structuredContent as FrappeGet} />
          );
        }
      }
    }

    return null;
  }, [toolCall]);

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
