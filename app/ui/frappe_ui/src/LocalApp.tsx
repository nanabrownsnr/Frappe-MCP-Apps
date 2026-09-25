import { useMemo, useState } from "react";
import type {
  CRMDealList,
  FrappeGet,
  FrappeList,
  StructuredContent,
} from "./types/response-types";
import { crmDealDta } from "./data/crm-deal";
import Pipeline from "./components/pipeline";
import type { ToolCall } from "./components/tool-call-provider";
import FrappeListView from "./components/frappe-list-view";
import { crmLeadData } from "./data/crm-lead";
import { frappeGetData } from "./data/frappe-get";
import FrappeGetView from "./components/frappe-get-view";

export default function LocalApp() {
  const [toolCall, setToolCall] = useState<ToolCall | null>({
    id: "1",
    arguments: {},
    result: frappeGetData,
    status: "completed",
  });

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

    return null;
  }, [toolCall]);

  return (
    <main className="min-h-svh w-full bg-host-bg text-host-text">{render}</main>
  );
}
