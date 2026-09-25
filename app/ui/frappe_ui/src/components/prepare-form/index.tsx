import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { FormProvider, useForm, type FieldValues } from "react-hook-form";
import type { FrappeCreatePrepare, ResultType } from "@/types/response-types";
import Header from "@/components/header";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import { useToolCall } from "@/components/tool-call-provider";
import FormFields from "./fields";
import { buildDefaultValues } from "./values";
import Notice from "../notice";

export default function PrepareForm({
  structuredContent,
}: {
  structuredContent: FrappeCreatePrepare;
}) {
  const { doctype } = structuredContent;
  const { app } = useToolCall();
  const [notice, setNotice] = useState<{
    tone: "error" | "success";
    text: string;
  } | null>(null);
  const defaultValues = useMemo(
    () =>
      buildDefaultValues(structuredContent.fields, structuredContent.values),
    [structuredContent]
  );
  const form = useForm<FieldValues>({ defaultValues });

  const { mutate: createRecord, isPending } = useMutation({
    mutationFn: async (values: FieldValues) => {
      if (!app) throw new Error("No app found");
      const response = await app.callServerTool({
        name: "frappe_create_record",
        arguments: {
          doctype,
          values,
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
        setNotice({ tone: "error", text: message });
      } else {
        form.reset();
        setNotice({
          tone: "success",
          text: "Created successfully",
        });
      }
    },
    onError: (error) => {
      setNotice({ tone: "error", text: error.message });
    },
  });

  return (
    <FormProvider {...form}>
      <section className="flex min-h-svh flex-col">
        <Header
          title={structuredContent.doctype}
          subtitle={`Create ${structuredContent.doctype}`}
          isLoading={isPending}
        />
        <form
          className="flex flex-1 flex-col"
          onSubmit={form.handleSubmit((values) => createRecord(values))}
        >
          <FieldGroup className="flex-1 px-4 py-4">
            <FormFields fields={structuredContent.fields} />
          </FieldGroup>
          <footer className="sticky bottom-0 z-10 border-t bg-host-bg px-4 py-3 flex gap-2 items-center justify-end">
            {!!notice && (
              <Notice
                tone={notice.tone}
                text={notice.text}
                actions={
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setNotice(null)}
                  >
                    Dismiss
                  </Button>
                }
              />
            )}

            <Button type="submit" size="lg" disabled={isPending}>
              Submit
            </Button>
          </footer>
        </form>
      </section>
    </FormProvider>
  );
}
