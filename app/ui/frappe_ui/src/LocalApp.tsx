import { useMemo, useState } from "react";
import type {
  CRMDealList,
  FrappeCreatePrepare,
  FrappeGet,
  FrappeList,
  StructuredContent,
} from "./types/response-types";
import { crmDealDta } from "./data/crm-deal";
import Pipeline from "./components/pipeline";
import {
  ToolCallContext,
  type ToolCall,
} from "./components/tool-call-provider";
import FrappeListView from "./components/frappe-list-view";
import { crmLeadData } from "./data/crm-lead";
import { frappeGetData } from "./data/frappe-get";
import FrappeGetView from "./components/frappe-get-view";
import PrepareForm from "./components/prepare-form";
import { frappeCreatePrepareData } from "./data/frappe-create-prepare";

export default function LocalApp() {
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([
    {
      id: "1",
      arguments: {},
      result: frappeCreatePrepareData,
      status: "completed",
    },
    {
      id: "1",
      arguments: {},
      result: crmLeadData,
      status: "completed",
    },
  ]);
  const toolCall = toolCalls.at(-1) ?? null;
  const canGoBack = useMemo(() => toolCalls.length > 1, [toolCalls]);

  const setToolCall = (next: ToolCall) => {
    setToolCalls((prev) => [...prev, next]);
  };

  const popToolCall = () => {
    setToolCalls((prev) => prev.slice(0, -1));
  };

  const render = useMemo(() => {
    if (!toolCall) return null;

    const toolName = toolCall.result?._meta?.toolname;
    const structuredContent = toolCall.result?.structuredContent!;

    if (toolName === "frappe_list") {
      switch (structuredContent.doctype) {
        case "CRM Deal": {
          return (
            <Pipeline structuredContent={structuredContent as CRMDealList} />
          );
        }
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

    if (toolName === "frappe_create_prepare") {
      return (
        <PrepareForm
          structuredContent={structuredContent as FrappeCreatePrepare}
        />
      );
    }

    return null;
  }, [toolCall]);

  return (
    <ToolCallContext.Provider
      value={{
        app: null,
        toolCall,
        canGoBack,
        setToolCall,
        popToolCall,
        isConnected: false,
        error: null,
      }}
    >
      <main className="min-h-svh w-full bg-host-bg text-host-text">
        {render}
      </main>
    </ToolCallContext.Provider>
  );
}
