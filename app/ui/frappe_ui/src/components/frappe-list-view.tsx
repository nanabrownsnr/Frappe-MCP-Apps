import type { FrappeList, ResultType } from "@/types/response-types";
import Header from "./header";
import KeyValue, { recordRows } from "./key-value";
import { useMutation } from "@tanstack/react-query";
import { useToolCall } from "./tool-call-provider";
import { useState } from "react";
import Notice from "./notice";
import { Button } from "./ui/button";

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
  const { app } = useToolCall();
  const [error, setError] = useState<string | null>(null);

  const { mutate: getRecord } = useMutation({
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
    onSuccess: (data) => {
      if (data.isError) {
        const message =
          data.content
            .map((item) => (item.type === "text" ? item.text : ""))
            .filter(Boolean)
            .join(" ") || "An error occurred.";
        setError(message);
      }
    },
    onError: (error) => {
      setError(error.message);
    },
  });

  return (
    <section className="flex min-h-svh flex-col gap-y-4">
      <Header title={doctype} subtitle={`${records.length} records`} />

      {!!error && (
        <div className="px-4">
          <Notice
            tone="error"
            text={error}
            actions={
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setError(null)}
                >
                  Dismiss
                </Button>
              </>
            }
          />
        </div>
      )}

      <div className="flex flex-col gap-6 px-4 pb-4">
        {records.map((record, index) => (
          <KeyValue
            key={recordName(record) ?? index}
            label={recordName(record)}
            rows={recordRows(record)}
            onClick={() => {
              getRecord({ name: recordName(record) ?? "" });
            }}
          />
        ))}
      </div>
    </section>
  );
}
