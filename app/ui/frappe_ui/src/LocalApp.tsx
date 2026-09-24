import { useMemo, useState } from "react";
import type { StructuredContent } from "./types/response-types";
import { crmDealDta } from "./data/crm-deal";
import Pipeline from "./components/pipeline";

export default function LocalApp() {
  const [structuredContent, setStructuredContent] =
    useState<StructuredContent | null>(crmDealDta.structuredContent);

  const render = useMemo(() => {
    if (!structuredContent) return null;
    switch (structuredContent.doctype) {
      case "CRM Deal": {
        return <Pipeline structuredContent={structuredContent} />;
      }
      default: {
        return null;
      }
    }
  }, []);

  return (
    <main className="min-h-svh w-full bg-host-bg text-host-text">{render}</main>
  );
}
