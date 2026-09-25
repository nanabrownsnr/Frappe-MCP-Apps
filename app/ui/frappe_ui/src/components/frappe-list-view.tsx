import type { FrappeList } from "@/types/response-types";
import Header from "./header";
import KeyValue, { recordRows } from "./key-value";

function recordName(record: Record<string, unknown>): string | undefined {
  const name = record.name;
  if (typeof name === "string" && name.trim()) return name;
  if (typeof name === "number") return String(name);
  return undefined;
}

export default function FrappeListView({
  structuredContent,
}: {
  structuredContent: FrappeList;
}) {
  const { doctype, records } = structuredContent;

  return (
    <section className="flex min-h-svh flex-col gap-y-4">
      <Header title={doctype} subtitle={`${records.length} records`} />
      <div className="flex flex-col gap-6 px-4 pb-4">
        {records.map((record, index) => (
          <KeyValue
            key={recordName(record) ?? index}
            label={recordName(record)}
            rows={recordRows(record)}
          />
        ))}
      </div>
    </section>
  );
}
