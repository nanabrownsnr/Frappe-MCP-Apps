import { useCallback, useState } from "react";
import {
  useApp,
  useDocumentTheme,
  useHostFonts,
  useHostStyleVariables,
  type App as McpApp,
} from "@modelcontextprotocol/ext-apps/react";
import { Button } from "@/components/ui/button";
import Pipeline from "./components/pipeline";
import type { StructuredContent } from "./types/response-types";

type ViewData = Record<string, unknown> | unknown[];
type CreateField = {
  fieldname: string;
  label: string;
  fieldtype: string;
  options?: string | null;
  reqd?: boolean;
  mandatory_depends_on?: string | null;
  description?: string | null;
};
type CreateFormData = {
  doctype: string;
  fields: CreateField[];
  values: Record<string, unknown>;
};

const label = (key: string) =>
  key.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const scalar = (value: unknown) =>
  value === null || value === undefined || value === "" ? "Not set" : String(value);

const text = (value: unknown) =>
  typeof value === "string" || typeof value === "number" ? String(value) : "";

function RecordView({ value }: { value: Record<string, unknown> }) {
  const simple = Object.entries(value).filter(([, item]) => item === null || typeof item !== "object");
  const nested = Object.entries(value).filter(([, item]) => item !== null && typeof item === "object");
  return (
    <>
      {simple.length ? (
        <section className="grid gap-0 rounded-card border border-host-border bg-host-surface px-4 py-[0.85rem]">
          {simple.map(([name, item]) => (
            <div className="grid grid-cols-1 gap-[0.2rem] border-b border-host-border py-[0.65rem] last:border-b-0 min-[30rem]:grid-cols-[minmax(8rem,30%)_1fr] min-[30rem]:gap-4" key={name}>
              <strong className="text-[0.8rem] font-semibold text-host-muted">{label(name)}</strong>
              <span className="wrap-anywhere text-[0.9rem]">{scalar(item)}</span>
            </div>
          ))}
        </section>
      ) : null}
      {nested.map(([name, item]) => (
        <section className="mt-4" key={name}>
          <h2 className="mb-2 text-[0.78rem] font-[650] tracking-[0.06em] text-host-muted uppercase">{label(name)}</h2>
          {Array.isArray(item) ? (
            <div className="grid gap-[0.65rem]">
              {item.map((row, index) => (
                <article className="rounded-card border border-host-border bg-host-surface p-3" key={isRecord(row) && row.name ? String(row.name) : index}>
                  {isRecord(row) ? <RecordView value={row} /> : scalar(row)}
                </article>
              ))}
            </div>
          ) : isRecord(item) ? <RecordView value={item} /> : null}
        </section>
      ))}
    </>
  );
}

function CreateForm({
  form,
  app,
  onCreated,
}: {
  form: CreateFormData;
  app: McpApp | null;
  onCreated: (record: Record<string, unknown>) => void;
}) {
  const [values, setValues] = useState(form.values);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [outcomeUnknown, setOutcomeUnknown] = useState(false);
  const required = form.fields.filter((field) => field.reqd);
  const optional = form.fields.filter((field) => !field.reqd);
  const conditionalRequired = optional.some((field) => field.mandatory_depends_on);
  const update = (field: CreateField, value: unknown) =>
    setValues((current) => ({ ...current, [field.fieldname]: value }));

  const renderControl = (field: CreateField) => {
    const value = values[field.fieldname];
    const className = "w-full rounded-control border border-host-border bg-host-bg px-3 py-2 text-host-text [font:inherit]";
    if (field.fieldtype === "Check") {
      return <input type="checkbox" checked={Boolean(value)} onChange={(event) => update(field, event.target.checked ? 1 : 0)} />;
    }
    if (["Text", "Small Text", "Long Text", "Code"].includes(field.fieldtype)) {
      return <textarea className={className} rows={3} value={text(value)} onChange={(event) => update(field, event.target.value)} />;
    }
    if (field.fieldtype === "Select" && field.options) {
      return (
        <select className={className} value={text(value)} onChange={(event) => update(field, event.target.value)}>
          <option value="">Choose…</option>
          {field.options.split("\n").filter(Boolean).map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      );
    }
    const inputType = field.fieldtype === "Date" ? "date"
      : field.fieldtype === "Datetime" ? "datetime-local"
      : ["Int", "Float", "Currency", "Percent", "Duration"].includes(field.fieldtype) ? "number"
      : field.fieldtype === "Email" ? "email" : "text";
    return (
      <input className={className} type={inputType} step={inputType === "number" ? "any" : undefined}
        value={value == null ? "" : String(value)}
        onChange={(event) => update(field, inputType === "number" ? (event.target.value === "" ? "" : Number(event.target.value)) : event.target.value)} />
    );
  };

  const submit = async () => {
    if (!app || submitting || outcomeUnknown) return;
    const missing = required.filter((field) => values[field.fieldname] == null || values[field.fieldname] === "");
    if (missing.length) {
      setError(`Fill in required fields: ${missing.map((field) => field.label).join(", ")}.`);
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await app.callServerTool({ name: "frappe_create_record", arguments: { doctype: form.doctype, values } });
      if (result.isError) {
        const message = result.content.map((item) => item.type === "text" ? item.text : "").filter(Boolean).join(" ") || "Frappe could not create this record.";
        setError(message);
        if (/outcome is unknown|check whether the record was created/i.test(message)) setOutcomeUnknown(true);
        return;
      }
      const payload = result.structuredContent;
      if (!isRecord(payload) || !isRecord(payload.record)) {
        setError("Frappe may have created the record, but the response did not include its details. Check Frappe before retrying.");
        setOutcomeUnknown(true);
        return;
      }
      onCreated(payload.record);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Could not complete the create request. Check Frappe before retrying.";
      setError(message);
      if (/outcome is unknown|check whether the record was created|may have created/i.test(message)) setOutcomeUnknown(true);
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field: CreateField) => (
    <label className="grid gap-1 text-[0.82rem]" key={field.fieldname}>
      <span className="font-semibold text-host-muted">{field.label}{field.reqd ? " *" : field.mandatory_depends_on ? " · Required when applicable" : ""}</span>
      {renderControl(field)}
      {field.description ? <small className="text-host-muted">{field.description}</small> : null}
    </label>
  );

  return (
    <section className="grid gap-4">
      <p className="text-[0.85rem] text-host-muted">Review the values below. Nothing is saved until you create it.</p>
      {required.length ? <div className="grid gap-3 rounded-card border border-host-border bg-host-surface p-4"><h2 className="text-[0.8rem] font-bold uppercase tracking-wide text-host-muted">Required fields</h2>{required.map(renderField)}</div> : null}
      {optional.length ? <details open={required.length === 0} className="rounded-card border border-host-border bg-host-surface p-4"><summary className="cursor-pointer text-[0.8rem] font-bold uppercase tracking-wide text-host-muted">Additional fields ({optional.length})</summary><div className="mt-3 grid gap-3">{required.length === 0 ? <p className="text-[0.78rem] text-host-muted">Frappe reports no unconditional required fields for this DocType. Some fields may still be required conditionally or by server-side validation.</p> : null}{conditionalRequired ? <p className="text-[0.78rem] text-host-muted">Fields marked “Required when applicable” depend on the values entered.</p> : null}{optional.map(renderField)}</div></details> : null}
      {error ? <p className="rounded-control border border-red-500/40 bg-red-500/10 p-3 text-[0.85rem]" role="alert">{error}</p> : null}
      <div className="flex justify-end"><Button disabled={!app || submitting || outcomeUnknown} onClick={() => void submit()}>{submitting ? "Creating…" : outcomeUnknown ? "Check Frappe before retrying" : "Create"}</Button></div>
    </section>
  );
}

export default function App() {
  const [structuredContent, setStructuredContent] = useState<Record<string, unknown> | null>(null);
  const [createForm, setCreateForm] = useState<CreateFormData | null>(null);
  const [createdRecord, setCreatedRecord] = useState<Record<string, unknown> | null>(null);

  const onAppCreated = useCallback((createdApp: McpApp) => {
    createdApp.ontoolresult = (result) => {
      const payload = result.structuredContent;
      if (isRecord(payload) && payload.mode === "create_form" && typeof payload.doctype === "string" && Array.isArray(payload.fields) && isRecord(payload.values)) {
        setCreateForm({ doctype: payload.doctype, fields: payload.fields.filter(isRecord) as unknown as CreateField[], values: payload.values });
        setCreatedRecord(null);
        setStructuredContent(null);
        return;
      }
      setCreateForm(null);
      setCreatedRecord(null);
      setStructuredContent(isRecord(payload) ? payload : null);
    };
  }, []);

  const { app, isConnected, error } = useApp({
    appInfo: { name: "twynity-frappe-dashboard", version: "1.0.0" },
    capabilities: {},
    onAppCreated,
    autoResize: true,
  });
  useHostStyleVariables(app, app?.getHostContext());
  useHostFonts(app, app?.getHostContext());
  const theme = useDocumentTheme();

  if (error || !isConnected) {
    return (
      <main className="min-h-svh w-full bg-host-bg p-4 text-host-text" data-host-theme={theme} aria-live="polite">
        <p>{error ? error.message : "Connecting to MCP…"}</p>
      </main>
    );
  }

  const doctype = typeof structuredContent?.doctype === "string" ? structuredContent.doctype : "Frappe";
  const record = createdRecord ?? (isRecord(structuredContent?.record) ? structuredContent.record : null);
  const records = Array.isArray(structuredContent?.records) ? structuredContent.records.filter(isRecord) : [];
  const content = structuredContent as unknown as StructuredContent | null;

  return (
    <main className="min-h-svh w-full bg-host-bg p-4 text-host-text" data-host-theme={theme} aria-live="polite">
      {createForm ? (
        <><p className="mb-3 text-xs font-semibold uppercase tracking-wide text-host-muted">New {label(createForm.doctype)}</p><CreateForm form={createForm} app={app} onCreated={(created) => { setCreateForm(null); setCreatedRecord(created); }} /></>
      ) : record ? (
        <><p className="mb-3 text-xs font-semibold uppercase tracking-wide text-host-muted">{label(doctype)}</p><h1 className="mb-4 text-xl font-bold">{text(record.name) || "Record details"}</h1><RecordView value={record} /></>
      ) : content?.doctype === "CRM Deal" ? (
        <Pipeline structuredContent={content} />
      ) : (
        <>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-host-muted">{label(doctype)}</p>
          {records.length ? <><h1 className="mb-4 text-xl font-bold">{records.length} records</h1><section className="grid gap-3">{records.map((row, index) => <article className="rounded-card border border-host-border bg-host-surface p-3" key={text(row.name) || index}><RecordView value={row} /></article>)}</section></> : null}
        </>
      )}
    </main>
  );
}
