import type { FrappeGet } from "@/types/response-types";
import Header from "./header";
import KeyValue, { recordRows } from "./key-value";

function recordName(record: Record<string, unknown>): string | undefined {
  const name = record.name;
  if (typeof name === "string" && name.trim()) return name;
  if (typeof name === "number") return String(name);
  return undefined;
}

export default function FrappeGetView({
  structuredContent,
}: {
  structuredContent: FrappeGet;
}) {
  const name = recordName(structuredContent.record);

  return (
    <section className="flex min-h-svh flex-col gap-y-4">
      <Header title={name ?? structuredContent.doctype} subtitle={structuredContent.doctype} />
      <div className="px-4 pb-4">
        <KeyValue rows={recordRows(structuredContent.record)} />
      </div>
    </section>
  );
}
