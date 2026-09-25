import { cn, isRecord } from "@/lib/utils";

export type KeyValueRow = { k: string; v: unknown };

export function recordRows(record: Record<string, unknown>): KeyValueRow[] {
  return Object.entries(record).map(([k, v]) => ({ k, v }));
}

function headingFromRows(rows: KeyValueRow[]): string | undefined {
  const name = rows.find((row) => row.k === "name")?.v;
  if (typeof name === "string" && name.trim()) return name;
  if (typeof name === "number") return String(name);
  return undefined;
}

function Value({ value }: { value: unknown }) {
  if (value == null || value === "") {
    return <span className="text-gray-5">—</span>;
  }

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return (
      <span className={cn(typeof value === "number" && "tabular-nums")}>
        {String(value)}
      </span>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-5">—</span>;
    if (value.every(isRecord)) {
      return (
        <div className="flex flex-col gap-3 py-1">
          {value.map((row, index) => {
            const rows = recordRows(row);
            return (
              <KeyValue key={index} label={headingFromRows(rows)} rows={rows} />
            );
          })}
        </div>
      );
    }
    return (
      <span className="wrap-break-word">
        {value.map((item) => String(item ?? "—")).join(", ")}
      </span>
    );
  }

  if (isRecord(value)) {
    const rows = recordRows(value);
    return <KeyValue label={headingFromRows(rows)} rows={rows} />;
  }

  return <span className="wrap-break-word">{String(value)}</span>;
}

export default function KeyValue({
  label,
  rows,
  onClick,
}: {
  label?: string;
  rows: KeyValueRow[];
  onClick?: () => void;
}) {
  return (
    <div
      className="flex flex-col gap-2 overflow-hidden rounded-xl p-4 ring-1 ring-foreground/10"
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
    >
      {label && (
        <div className="text-base font-semibold uppercase">{label}</div>
      )}
      <div className="overflow-hidden rounded-md  bg-violet-light grid grid-cols-[auto_1fr] text-sm items-start">
        {rows.map((row, index) => (
          <>
            <span
              className={cn(
                "text-host-text/80 flex items-center py-2.5 px-4",
                index > 1 && "border-t border-violet-mid"
              )}
            >
              {row.k}
            </span>
            <span
              className={cn(
                "min-w-0 wrap-break-word flex items-center py-2.5 px-4",
                index > 1 && "border-t border-violet-mid"
              )}
            >
              <Value value={row.v} />
            </span>
          </>
        ))}
      </div>
    </div>
  );
}
