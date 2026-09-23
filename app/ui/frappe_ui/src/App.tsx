import { useCallback, useState } from "react";
import {
  useApp,
  useDocumentTheme,
  useHostFonts,
  useHostStyleVariables,
  type App as McpApp,
} from "@modelcontextprotocol/ext-apps/react";

const SERVICE_KEYS = [
  "service_line",
  "custom_service_line",
  "business_unit",
  "vertical",
] as const;

type ViewData = Record<string, unknown> | unknown[];

const label = (key: string) =>
  key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const scalar = (value: unknown) =>
  value === null || value === undefined || value === ""
    ? "Not set"
    : String(value);

const text = (value: unknown) =>
  typeof value === "string" || typeof value === "number" ? String(value) : "";

function Field({ name, value }: { name: string; value: unknown }) {
  return (
    <div className="grid grid-cols-1 gap-[0.2rem] border-b border-host-border py-[0.65rem] wrap-anywhere last:border-b-0 min-[30rem]:grid-cols-[minmax(8rem,30%)_1fr] min-[30rem]:gap-4">
      <strong className="text-[0.8rem] font-semibold text-host-muted">
        {label(name)}
      </strong>
      <span className="text-[0.9rem]">{scalar(value)}</span>
    </div>
  );
}

function RecordView({
  value,
}: {
  value: Record<string, unknown> | null | undefined;
}) {
  const entries = Object.entries(value ?? {});
  const simple = entries.filter(
    ([, item]) => item === null || typeof item !== "object"
  );
  const nested = entries.filter(([, item]) => item && typeof item === "object");
  return (
    <>
      {simple.length ? (
        <section className="grid gap-0 rounded-card border border-host-border bg-host-surface px-4 py-[0.85rem]">
          {simple.map(([name, item]) => (
            <Field key={name} name={name} value={item} />
          ))}
        </section>
      ) : null}
      {nested.map(([name, item]) => (
        <section className="mt-4" key={name}>
          <h2 className="mb-2 text-[0.78rem] font-[650] tracking-[0.06em] text-host-muted uppercase">
            {label(name)}
          </h2>
          {Array.isArray(item) ? (
            <div className="grid gap-[0.65rem]">
              {item.map((row, index) => (
                <article
                  className="grid gap-[0.28rem] rounded-card border border-host-border bg-host-surface px-4 py-[0.85rem] text-[0.88rem] [&_strong]:font-semibold [&_strong]:text-host-muted"
                  key={
                    isRecord(row) && row.name != null ? String(row.name) : index
                  }
                >
                  {isRecord(row) ? (
                    <RecordView value={row} />
                  ) : (
                    <span>{scalar(row)}</span>
                  )}
                </article>
              ))}
            </div>
          ) : isRecord(item) ? (
            <RecordView value={item} />
          ) : null}
        </section>
      ))}
    </>
  );
}

function amount(row: Record<string, unknown>) {
  return Number(
    row.deal_value ?? row.expected_deal_value ?? row.annual_revenue ?? 0
  );
}

function DealPipeline({ records }: { records: Record<string, unknown>[] }) {
  const serviceKey = SERVICE_KEYS.find((key) => key in (records[0] ?? {}));
  const services = [
    "All",
    ...new Set(
      records
        .map((row) => (serviceKey ? row[serviceKey] : undefined))
        .filter(Boolean)
    ),
  ];
  const [service, setService] = useState("All");
  const filtered =
    service === "All" || !serviceKey
      ? records
      : records.filter((row) => row[serviceKey] === service);
  const statuses = [
    ...new Set(records.map((row) => text(row.status) || "Uncategorized")),
  ];
  const total = records.reduce((sum, row) => sum + amount(row), 0);
  const currency = text(records[0]?.currency);

  return (
    <section>
      <div className="mb-4 flex items-baseline gap-[0.6rem] border-b border-host-border pb-[0.8rem]">
        <strong className="text-[0.95rem]">{filtered.length} open deals</strong>
        <span className="text-[0.8rem] text-host-muted">
          {total ? `${currency} ${total.toLocaleString()}` : "No value"}
        </span>
        <small className="ml-auto text-[0.72rem] text-host-muted">
          Click a card to view it in Frappe
        </small>
      </div>
      <div className="mb-[0.8rem] flex items-center justify-between text-[0.8rem] text-host-muted">
        <span>Grouped by status · ranked by value</span>
        {serviceKey ? (
          <label>
            Service line{" "}
            <select
              className="ml-[0.4rem] rounded-control border border-host-border bg-host-surface px-2 py-[0.35rem] text-inherit [font:inherit]"
              value={service}
              onChange={(event) => setService(event.target.value)}
            >
              {services.map((item) => (
                <option key={String(item)}>{String(item)}</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      <div className="grid auto-cols-[minmax(12rem,1fr)] grid-flow-col gap-[0.7rem] overflow-x-auto pb-2">
        {statuses.map((status) => (
          <div
            className="min-h-56 rounded-card bg-host-surface p-[0.55rem]"
            key={status}
          >
            <h2 className="mb-[0.55rem] flex justify-between text-[0.82rem] font-bold">
              {label(status)}{" "}
              <small className="font-medium text-host-muted">
                {
                  filtered.filter(
                    (row) => (text(row.status) || "Uncategorized") === status
                  ).length
                }
              </small>
            </h2>
            {filtered
              .filter((row) => (text(row.status) || "Uncategorized") === status)
              .map((deal, index) => {
                const value =
                  deal.deal_value ??
                  deal.expected_deal_value ??
                  deal.annual_revenue;
                const owner = text(deal.deal_owner) || text(deal.owner);
                const serviceLine = serviceKey ? text(deal[serviceKey]) : "";
                return (
                  <article
                    className="mb-[0.55rem] grid gap-[0.3rem] rounded-control border border-host-border bg-host-bg p-[0.7rem] text-[0.78rem]"
                    key={deal.name != null ? String(deal.name) : index}
                  >
                    <strong>
                      {text(deal.organization) ||
                        text(deal.company) ||
                        text(deal.title) ||
                        text(deal.deal_name) ||
                        text(deal.name)}
                    </strong>
                    <span className="text-host-muted">{text(deal.name)}</span>
                    <b className="text-[0.9rem]">
                      {value
                        ? `${text(deal.currency)} ${Number(
                            value
                          ).toLocaleString()}`
                        : "No value"}
                    </b>
                    <span className="text-host-muted">
                      {text(deal.expected_closure_date)
                        ? `Close ${text(deal.expected_closure_date)}`
                        : owner
                        ? `Owner: ${owner}`
                        : ""}
                    </span>
                    {serviceLine ? (
                      <em className="w-fit rounded-[0.3rem] bg-host-chip px-[0.35rem] py-[0.15rem] text-[0.68rem] text-host-muted not-italic">
                        {serviceLine}
                      </em>
                    ) : null}
                  </article>
                );
              })}
          </div>
        ))}
      </div>
    </section>
  );
}

function rowsFrom(data: ViewData | null) {
  if (Array.isArray(data)) return data.filter(isRecord);
  if (isRecord(data) && Array.isArray(data.records))
    return data.records.filter(isRecord);
  return [];
}

function recordFrom(data: ViewData | null) {
  if (!isRecord(data)) return null;
  if (isRecord(data.record)) return data.record;
  if (data.name) return data;
  return null;
}

export default function App() {
  const [data, setData] = useState<ViewData | null>(null);

  const onAppCreated = useCallback((createdApp: McpApp) => {
    createdApp.ontoolresult = (result) => {
      const payload = result.structuredContent ?? result;
      setData(isRecord(payload) || Array.isArray(payload) ? payload : null);
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

  const rows = rowsFrom(data);
  const record = recordFrom(data);
  const doctype =
    isRecord(data) && typeof data.doctype === "string"
      ? data.doctype
      : undefined;

  return (
    <main
      className="min-h-full w-full bg-host-bg p-4 text-host-text"
      data-host-theme={theme}
      aria-live="polite"
    >
      <header>
        <p className="mb-[0.35rem] text-[0.72rem] font-[650] tracking-[0.08em] text-host-muted uppercase">
          {doctype ? label(doctype) : "Frappe"}
        </p>
        <h1 className="mb-4 text-[1.35rem] leading-[1.25] font-bold">
          {record && record.name != null
            ? String(record.name)
            : rows.length
            ? `${rows.length} records`
            : "Record details"}
        </h1>
      </header>
      {error ? (
        <p>{error.message}</p>
      ) : !isConnected ? (
        <p>Connecting to MCP…</p>
      ) : null}
      {record ? (
        <RecordView value={record} />
      ) : doctype === "CRM Deal" ? (
        <DealPipeline records={rows} />
      ) : (
        <section className="grid gap-[0.65rem]">
          {rows.map((row, index) => (
            <article
              className="grid gap-[0.28rem] rounded-card border border-host-border bg-host-surface px-4 py-[0.85rem] text-[0.88rem] [&_strong]:font-semibold [&_strong]:text-host-muted"
              key={row.name != null ? String(row.name) : index}
            >
              <RecordView value={row} />
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
