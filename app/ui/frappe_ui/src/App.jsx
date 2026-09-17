import React, { useCallback, useState } from "react";
import { useApp, useDocumentTheme, useHostFonts, useHostStyleVariables } from "@modelcontextprotocol/ext-apps/react";

export default function FrappeDashboard() {
    const [data, setData] = useState(null);
    const onAppCreated = useCallback((createdApp) => {
        createdApp.ontoolresult = (result) => setData(result.structuredContent ?? result);
    }, []);
    const { app, isConnected, error } = useApp({ appInfo: { name: "twynity-frappe-dashboard", version: "1.0.0" }, capabilities: {}, onAppCreated, autoResize: true });
    useHostStyleVariables(app, app?.getHostContext());
    useHostFonts(app, app?.getHostContext());
    const theme = useDocumentTheme();
    const rows = Array.isArray(data?.records) ? data.records : Array.isArray(data) ? data : [];
    const record = data?.record ?? (!Array.isArray(data) && data?.name ? data : null);
    return <main className="card" data-host-theme={theme} aria-live="polite">
        <p className="eyebrow">Frappe / ERPNext</p><h1>{data?.doctype ?? "Records"}</h1>
        {error ? <p>{error.message}</p> : !isConnected ? <p>Connecting to MCP…</p> : null}
        {record ? <section className="details">{Object.entries(record).map(([key, value]) => <div className="field" key={key}><strong>{key}</strong><span>{String(value ?? "")}</span></div>)}</section> : <section className="records">{rows.map((row, index) => <article key={row.name ?? index}>{Object.entries(row).map(([key, value]) => <div key={key}><strong>{key}</strong>: {String(value ?? "")}</div>)}</article>)}</section>}
    </main>;
}
