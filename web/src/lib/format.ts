import type { FieldType } from "./api";

// Pages render on the server, so pin the time zone instead of inheriting the host's.
const dateTime = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
});

export function formatDate(value: string): string {
  return `${dateTime.format(new Date(value))} UTC`;
}

/** Renders a record value according to its Avro field type. */
export function formatValue(value: unknown, type: FieldType): string {
  if (value === null || value === undefined) return "—";
  if (type === "datetime" && typeof value === "string") return formatDate(value);
  if (type === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** `first_name` -> `First name` */
export function humanize(name: string): string {
  const words = name.replace(/[_-]+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}
