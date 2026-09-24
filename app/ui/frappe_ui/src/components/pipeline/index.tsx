import { useMemo, useState } from "react";
import type { CRMDeal } from "@/types/response-types";
import { Board, type Card } from "./board";

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

type Deal = CRMDeal["records"][number];

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
  structuredContent: CRMDeal;
  canDrag?: boolean;
}) {
  const [records, setRecords] = useState(structuredContent.records);
  const [serviceLine, setServiceLine] = useState(ALL_SERVICE_LINES);
  const [sourceKey, setSourceKey] = useState(structuredContent);

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
    const statuses = [...new Set(records.map((deal) => deal.status))].sort(
      (a, b) => stageRank(a) - stageRank(b)
    );
    return statuses.map((status) => ({
      value: status,
      label: status,
      meta: CLOSED.has(status) ? "Closed" : "Open",
    }));
  }, [records]);

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
    <section className="bg-bg-page p-4 text-dark">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-[15px] font-bold tracking-[-0.01em]">Pipeline</h1>
          <p className="text-[11px] text-gray-4">{cards.length} deals</p>
        </div>
        <label className="text-[11px] font-semibold text-gray-4">
          <span className="sr-only">Service line</span>
          <select
            value={serviceLine}
            onChange={(event) => setServiceLine(event.target.value)}
            className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-dark"
          >
            <option value={ALL_SERVICE_LINES}>All service lines</option>
            {serviceLines.map((line) => (
              <option key={line} value={line}>
                {line}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Board
        cards={cards}
        columns={columns}
        canDrag={canDrag}
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
