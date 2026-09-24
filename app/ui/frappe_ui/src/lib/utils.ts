export { cn } from "cn";

export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const generateId = () => {
  return Math.random().toString(36).substring(2, 9) + Date.now().toString(36);
};
