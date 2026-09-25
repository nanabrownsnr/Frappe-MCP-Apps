import { useMemo } from "react";
import { FormProvider, useForm, type FieldValues } from "react-hook-form";
import type { FrappeCreatePrepare } from "@/types/response-types";
import Header from "@/components/header";
import { Button } from "@/components/ui/button";
import { FieldGroup } from "@/components/ui/field";
import FormFields from "./fields";
import { buildDefaultValues } from "./values";

export default function PrepareForm({
  structuredContent,
}: {
  structuredContent: FrappeCreatePrepare;
}) {
  return (
    <section className="flex min-h-svh flex-col">
      <Header title={structuredContent.doctype} subtitle="Create" />
      <PrepareFormBody
        key={structuredContent.doctype}
        structuredContent={structuredContent}
      />
    </section>
  );
}

function PrepareFormBody({
  structuredContent,
}: {
  structuredContent: FrappeCreatePrepare;
}) {
  const defaultValues = useMemo(
    () =>
      buildDefaultValues(structuredContent.fields, structuredContent.values),
    [structuredContent]
  );
  const form = useForm<FieldValues>({ defaultValues });

  return (
    <FormProvider {...form}>
      <form
        className="flex flex-1 flex-col"
        onSubmit={form.handleSubmit((values) => {
          console.log(values);
        })}
      >
        <FieldGroup className="flex-1 px-4 py-4">
          <FormFields fields={structuredContent.fields} />
        </FieldGroup>
        <footer className="sticky bottom-0 z-10 border-t bg-host-bg px-4 py-3">
          <Button type="submit" size="lg">
            Submit
          </Button>
        </footer>
      </form>
    </FormProvider>
  );
}
