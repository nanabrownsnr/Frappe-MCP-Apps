import type { FrappeFormField } from "@/types/response-types";

export type FormValues = Record<string, unknown>;

export function buildDefaultValues(
  fields: FrappeFormField[],
  values: Record<string, unknown>,
): FormValues {
  const result: FormValues = {};
  for (const field of fields) {
    result[field.fieldname] = defaultForField(field, values[field.fieldname]);
  }
  return result;
}

export function emptyRow(fields: FrappeFormField[]): FormValues {
  return buildDefaultValues(fields, {});
}

export function selectOptions(options: string | null): string[] {
  if (!options) return [];
  return options
    .split("\n")
    .map((option) => option.trim())
    .filter(Boolean);
}

export function fieldDescription(field: FrappeFormField): string | null {
  if (field.description) return field.description;
  if (field.fieldtype === "Link" && field.options) return field.options;
  if (field.fieldtype === "Percent") return "%";
  return null;
}

/** `true`/`false` when the expression matches; `null` when there is no rule or it is unrecognized. */
export function matchDependsOn(
  expression: string | null,
  doc: Record<string, unknown>,
): boolean | null {
  if (!expression?.trim()) return null;

  const body = expression.trim().replace(/^eval:\s*/, "");
  const comparison = body.match(
    /^doc\.([A-Za-z0-9_]+)\s*(==|!=)\s*"([^"]*)"\s*$/,
  );
  if (comparison) {
    const actual = String(doc[comparison[1]] ?? "");
    const equal = actual === comparison[3];
    return comparison[2] === "==" ? equal : !equal;
  }

  const reference = body.match(/^doc\.([A-Za-z0-9_]+)\s*$/);
  if (reference) {
    const value = doc[reference[1]];
    return (
      value !== null &&
      value !== undefined &&
      value !== "" &&
      value !== false &&
      value !== 0 &&
      value !== "0"
    );
  }

  return null;
}

export function isFieldVisible(
  expression: string | null,
  doc: Record<string, unknown>,
): boolean {
  const matched = matchDependsOn(expression, doc);
  return matched === null ? true : matched;
}

export function isFieldRequired(
  field: FrappeFormField,
  doc: Record<string, unknown>,
): boolean {
  if (field.reqd) return true;
  return matchDependsOn(field.mandatory_depends_on, doc) === true;
}

export function docAtPrefix(
  values: FormValues,
  namePrefix?: string,
): Record<string, unknown> {
  if (!namePrefix) return values;
  const value = namePrefix.split(".").reduce<unknown>((current, key) => {
    if (!current || typeof current !== "object") return undefined;
    return (current as Record<string, unknown>)[key];
  }, values);
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function defaultForField(field: FrappeFormField, raw: unknown): unknown {
  if (field.fieldtype === "Table") {
    const rows = Array.isArray(raw) ? raw : [];
    return rows.map((row) => {
      const source =
        row && typeof row === "object" ? (row as Record<string, unknown>) : {};
      return buildDefaultValues(field.child_fields ?? [], source);
    });
  }

  if (field.fieldtype === "Check") {
    const value = raw === undefined ? field.default : raw;
    return value === true || value === 1 || value === "1";
  }

  const value =
    raw === null || raw === undefined || raw === ""
      ? (field.default ?? "")
      : String(raw);

  if (field.fieldtype === "Datetime") return toDatetimeLocal(value);
  if (field.fieldtype === "Date") return value.slice(0, 10);
  return value;
}

function toDatetimeLocal(value: string): string {
  if (!value) return "";
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  return normalized.slice(0, 16);
}
