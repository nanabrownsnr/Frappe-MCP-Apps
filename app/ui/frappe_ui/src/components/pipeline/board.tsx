import { useState } from "react";
import { ArrowUp, GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";

export type Card = {
  id: string;
  status: string;
  organization: string;
  lead_name: string;
  deal_value: number;
  currency: string;
  custom_service_line: string;
  probability: number;
  heat: number;
};

type Column = { value: string; label: string; meta: string };

export function money(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(amount);
  } catch {
    return `${currency} ${amount}`;
  }
}

function columnTotal(cards: Card[]): string {
  const totals = new Map<string, number>();
  for (const card of cards) {
    if (!card.deal_value) continue;
    totals.set(
      card.currency,
      (totals.get(card.currency) ?? 0) + card.deal_value
    );
  }
  if (totals.size === 0) return "—";
  return [...totals.entries()]
    .map(([currency, amount]) => money(amount, currency))
    .join(" · ");
}

function BoardCard({
  card,
  canDrag,
  dragging,
  onDragStart,
  onDragEnd,
  onClick,
}: {
  card: Card;
  canDrag: boolean;
  dragging: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onClick?: () => void;
}) {
  const value = card.deal_value ? money(card.deal_value, card.currency) : null;
  const flagged = card.heat > 0;
  return (
    <div
      draggable={canDrag}
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", card.id);
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      role="group"
      aria-label={card.organization}
      className={cn(
        "group relative flex flex-col gap-1.5 rounded-[12px] border p-3 text-left transition-all",
        flagged ? "border-amber-text/40 bg-butter" : "border-border bg-white",
        canDrag && "cursor-grab",
        onClick &&
          "cursor-pointer hover:border-primary/50 hover:shadow-[0_2px_8px_rgba(15,15,30,.06)]",
        dragging && "opacity-40"
      )}
    >
      {canDrag && (
        <GripVertical
          size={13}
          aria-hidden
          className="absolute right-2 top-2.5 text-gray-6 opacity-0 transition-opacity group-hover:opacity-100"
        />
      )}
      <span className="pr-4 text-[12.5px] font-semibold leading-snug text-dark">
        {card.organization}
      </span>
      <span className="text-[11px] text-gray-4">{card.lead_name}</span>
      <span
        className={cn(
          "font-sans tabular-nums",
          value
            ? "text-[15px] font-bold tracking-[-0.01em] text-dark"
            : "text-[12px] text-gray-5"
        )}
      >
        {value ?? "No value"}
      </span>
      <span className="flex flex-wrap items-center gap-1.5">
        <span className="rounded-full bg-violet-mid px-1.5 py-0.5 text-[10px] font-semibold text-violet-h">
          {card.custom_service_line}
        </span>
        <span className="rounded-full bg-bg-page px-1.5 py-0.5 text-[10px] font-semibold text-gray-3">
          {card.probability}%
        </span>
        {flagged && (
          <span className="rounded-full bg-amber px-1.5 py-0.5 text-[10px] font-semibold text-amber-text">
            Hot
          </span>
        )}
      </span>
    </div>
  );
}

export function Board({
  cards,
  columns,
  canDrag = true,
  onStatusChange,
  onCardClick,
}: {
  cards: Card[];
  columns: Column[];
  canDrag?: boolean;
  onStatusChange?: (id: string, status: string) => void;
  onCardClick?: (id: string) => void;
}) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [overCol, setOverCol] = useState<string | null>(null);

  const drop = (status: string, id: string) => {
    setOverCol(null);
    setDragId(null);
    if (!canDrag || !id) return;
    const card = cards.find((item) => item.id === id);
    if (!card || card.status === status) return;
    onStatusChange?.(id, status);
  };

  return (
    <div className="flex flex-col gap-y-4 flex-1 px-1">
      <div className=" flex items-center gap-2 text-[11px] text-gray-4">
        <ArrowUp size={12} aria-hidden />
        Grouped by status · ranked by deal value
        {canDrag && " · drag a card between columns"}
      </div>
      <div className="overflow-x-auto flex-1 pb-2">
        <div className="flex min-w-max gap-2">
          {columns.map((col) => {
            const inCol = cards
              .filter((card) => card.status === col.value)
              .sort((a, b) => b.deal_value - a.deal_value);
            const hot = inCol.some((card) => card.heat > 0);
            const isOver = overCol === col.value;
            return (
              <div
                key={col.value}
                onDragOver={(event) => {
                  if (!canDrag) return;
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                  if (overCol !== col.value) setOverCol(col.value);
                }}
                onDragLeave={(event) => {
                  if (event.currentTarget.contains(event.relatedTarget as Node))
                    return;
                  setOverCol((current) =>
                    current === col.value ? null : current
                  );
                }}
                onDrop={(event) => {
                  if (!canDrag) return;
                  event.preventDefault();
                  drop(col.value, event.dataTransfer.getData("text/plain"));
                }}
                aria-label={col.label}
                className={cn(
                  "flex w-[172px] flex-col gap-2 rounded-[12px] p-1 transition-colors",
                  isOver && "bg-violet-light ring-1 ring-violet-mid"
                )}
              >
                <div
                  className={cn(
                    "border-b-2 px-1 pb-2",
                    hot ? "border-amber-text" : "border-border"
                  )}
                >
                  <div className="text-[12px] font-bold leading-snug text-dark">
                    {col.label}
                  </div>
                  <div className="mt-0.5 font-sans text-[10.5px] tabular-nums text-gray-4">
                    {inCol.length} · {columnTotal(inCol)} · {col.meta}
                  </div>
                </div>
                <div className="flex min-h-[88px] flex-col gap-2">
                  {inCol.length === 0 ? (
                    <div
                      className={cn(
                        "rounded-[12px] border border-dashed px-3 py-4 text-center text-[11px]",
                        isOver
                          ? "border-violet text-violet"
                          : "border-border text-gray-5"
                      )}
                    >
                      {isOver ? "Drop here" : "No deals"}
                    </div>
                  ) : (
                    inCol.map((card) => (
                      <BoardCard
                        key={card.id}
                        card={card}
                        canDrag={canDrag}
                        dragging={dragId === card.id}
                        onDragStart={() => setDragId(card.id)}
                        onDragEnd={() => {
                          setDragId(null);
                          setOverCol(null);
                        }}
                        onClick={
                          onCardClick ? () => onCardClick(card.id) : undefined
                        }
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
