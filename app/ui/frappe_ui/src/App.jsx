import React, { useCallback, useState } from "react";
import { useApp, useDocumentTheme, useHostFonts, useHostStyleVariables } from "@modelcontextprotocol/ext-apps/react";

const label = (key) => key.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const scalar = (value) => value === null || value === undefined || value === "" ? "Not set" : String(value);

function Field({ name, value }) {
    return <div className="field"><strong>{label(name)}</strong><span>{scalar(value)}</span></div>;
}

function RecordView({ value }) {
    const entries = Object.entries(value ?? {});
    const simple = entries.filter(([, item]) => item === null || typeof item !== "object");
    const nested = entries.filter(([, item]) => item && typeof item === "object");
    return <>{simple.length ? <section className="details">{simple.map(([name, item]) => <Field key={name} name={name} value={item} />)}</section> : null}
        {nested.map(([name, item]) => <section className="data-section" key={name}><h2>{label(name)}</h2>
            {Array.isArray(item) ? <div className="records">{item.map((row, index) => <article key={row?.name ?? index}>{typeof row === "object" ? <RecordView value={row} /> : <span>{scalar(row)}</span>}</article>)}</div> : <RecordView value={item} />}
        </section>)}</>;
}

export default function FrappeDashboard() {
    const [data, setData] = useState(null);
    const onAppCreated = useCallback((createdApp) => { createdApp.ontoolresult = (result) => setData(result.structuredContent ?? result); }, []);
    const { app, isConnected, error } = useApp({ appInfo: { name: "twynity-frappe-dashboard", version: "1.0.0" }, capabilities: {}, onAppCreated, autoResize: true });
    useHostStyleVariables(app, app?.getHostContext());
    useHostFonts(app, app?.getHostContext());
    const theme = useDocumentTheme();
    const rows = Array.isArray(data?.records) ? data.records : Array.isArray(data) ? data : [];
    const record = data?.record ?? (!Array.isArray(data) && data?.name ? data : null);
    return <main className="card" data-host-theme={theme} aria-live="polite"><header><p className="eyebrow">{data?.doctype ? label(data.doctype) : "Frappe"}</p><h1>{record?.name ?? (rows.length ? `${rows.length} records` : "Record details")}</h1></header>
        {error ? <p>{error.message}</p> : !isConnected ? <p>Connecting to MCP…</p> : null}
        {record ? <RecordView value={record} /> : <section className="records">{rows.map((row, index) => <article key={row.name ?? index}><RecordView value={row} /></article>)}</section>}
    </main>;
}
