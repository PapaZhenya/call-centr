export function statusBadgeClass(status: string): string {
  if (status === "completed") return "badge success";
  if (status.endsWith("_failed")) return "badge danger";
  if (status === "uploaded") return "badge muted";
  return "badge warning";
}

export function splitPhrases(value: string): string[] | null {
  const items = value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return items.length > 0 ? items : null;
}

export function speakerLabel(
  speaker: string | null,
  labels: { agent: string; customer: string; unknown: string },
): string {
  if (speaker === "agent") return labels.agent;
  if (speaker === "customer") return labels.customer;
  return labels.unknown;
}
