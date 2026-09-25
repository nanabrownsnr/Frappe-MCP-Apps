import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import type { CRMDealList, ResultType } from "@/types/response-types";
import { generateId } from "@/lib/utils";
import { Board, type Card } from "./board";
import Header from "../header";
import Notice from "../notice";
import { Button } from "../ui/button";
import { useToolCall } from "../tool-call-provider";

const STAGE_ORDER = [
  "Qualification",
  "Discovery",
  "Demo",
  "Proposal",
  "Negotiation",
  "Ready to Close",
  "Won",
  "Lost",
];

const CLOSED = new Set(["Won", "Lost"]);
const ALL_SERVICE_LINES = "";

type Deal = CRMDealList["records"][number];

function stageRank(status: string): number {
  const index = STAGE_ORDER.indexOf(status);
  return index === -1 ? STAGE_ORDER.indexOf("Won") : index;
}

function toCard(deal: Deal): Card {
  const openAndLikely = !CLOSED.has(deal.status) && deal.probability >= 50;
  return {
    id: deal.name,
    status: deal.status,
    organization: deal.organization,
    lead_name: deal.lead_name,
    deal_value: deal.deal_value,
    currency: deal.currency,
    custom_service_line: deal.custom_service_line,
    probability: deal.probability,
    heat: openAndLikely ? 1 : 0,
  };
}

export default function Pipeline({
  structuredContent,
  canDrag = false,
}: {
  structuredContent: CRMDealList;
  canDrag?: boolean;
}) {
  const { doctype } = structuredContent;
  const { app, setToolCall } = useToolCall();
  const [error, setError] = useState<string | null>(null);
  const [records, setRecords] = useState(structuredContent.records);
  const [serviceLine, setServiceLine] = useState(ALL_SERVICE_LINES);
  const [sourceKey, setSourceKey] = useState(structuredContent);

  const { mutate: getDeal, isPending } = useMutation({
    mutationFn: async ({ name }: { name: string }) => {
      if (!app) throw new Error("No app found");
      const response = await app.callServerTool({
        name: "frappe_get",
        arguments: {
          doctype,
          name,
        },
      });
      return response as ResultType;
    },
    onSuccess: (data, { name }) => {
      if (data.isError) {
        const message =
          data.content
            .map((item) => (item.type === "text" ? item.text : ""))
            .filter(Boolean)
            .join(" ") || "An error occurred.";
        setError(message);
      } else {
        setToolCall({
          id: generateId(),
          arguments: {
            doctype,
            name,
          },
          result: data,
          status: "completed",
        });
      }
    },
    onError: (error) => {
      setError(error.message);
    },
  });

  if (sourceKey !== structuredContent) {
    setSourceKey(structuredContent);
    setRecords(structuredContent.records);
    setServiceLine(ALL_SERVICE_LINES);
  }

  const serviceLines = useMemo(
    () => [...new Set(records.map((deal) => deal.custom_service_line))].sort(),
    [records]
  );

  const columns = useMemo(() => {
    const statuses = [
      ...new Set(structuredContent.records.map((deal) => deal.status)),
    ].sort((a, b) => stageRank(a) - stageRank(b));
    return statuses.map((status) => ({
      value: status,
      label: status,
      meta: CLOSED.has(status) ? "Closed" : "Open",
    }));
  }, [structuredContent]);

  const cards = useMemo(
    () =>
      records
        .filter(
          (deal) => !serviceLine || deal.custom_service_line === serviceLine
        )
        .map(toCard),
    [records, serviceLine]
  );

  return (
    <section className="flex flex-col gap-y-4 min-h-svh">
      <Header
        title="Pipeline"
        subtitle={`${cards.length} deals`}
        isLoading={isPending}
      >
        <label className="text-[11px] font-semibold text-gray-4">
          <span className="sr-only">Service line</span>
          <select
            value={serviceLine}
            onChange={(event) => setServiceLine(event.target.value)}
            className="rounded-full bg-white border px-2.5 py-1 text-[11px] font-semibold text-dark"
          >
            <option value={ALL_SERVICE_LINES}>All service lines</option>
            {serviceLines.map((line) => (
              <option key={line} value={line}>
                {line}
              </option>
            ))}
          </select>
        </label>
      </Header>

      {!!error && (
        <div className="px-4">
          <Notice
            tone="error"
            text={error}
            actions={
              <Button
                size="sm"
                variant="outline"
                onClick={() => setError(null)}
              >
                Dismiss
              </Button>
            }
          />
        </div>
      )}

      <Board
        cards={cards}
        columns={columns}
        canDrag={canDrag}
        onCardClick={(name) => getDeal({ name })}
        onStatusChange={
          canDrag
            ? (id, status) =>
                setRecords((current) =>
                  current.map((deal) =>
                    deal.name === id ? { ...deal, status } : deal
                  )
                )
            : undefined
        }
      />
    </section>
  );
}
