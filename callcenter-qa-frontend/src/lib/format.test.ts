import { describe, expect, it } from "vitest";
import { speakerLabel, splitPhrases, statusBadgeClass } from "./format";

describe("statusBadgeClass", () => {
  it("marks completed calls as success", () => {
    expect(statusBadgeClass("completed")).toBe("badge success");
  });

  it("marks any *_failed status as danger", () => {
    expect(statusBadgeClass("transcription_failed")).toBe("badge danger");
    expect(statusBadgeClass("evaluation_failed")).toBe("badge danger");
  });

  it("marks uploaded as muted", () => {
    expect(statusBadgeClass("uploaded")).toBe("badge muted");
  });

  it("marks in-progress statuses as warning", () => {
    expect(statusBadgeClass("transcribing")).toBe("badge warning");
    expect(statusBadgeClass("evaluating")).toBe("badge warning");
  });
});

describe("splitPhrases", () => {
  it("splits comma-separated phrases and trims whitespace", () => {
    expect(splitPhrases("hello,  world ,test")).toEqual(["hello", "world", "test"]);
  });

  it("drops empty entries", () => {
    expect(splitPhrases("hello,,world,")).toEqual(["hello", "world"]);
  });

  it("returns null for an empty or whitespace-only string", () => {
    expect(splitPhrases("")).toBeNull();
    expect(splitPhrases("   ")).toBeNull();
    expect(splitPhrases(",,,")).toBeNull();
  });
});

describe("speakerLabel", () => {
  const labels = { agent: "Агент", customer: "Клиент", unknown: "Неизвестно" };

  it("maps known speaker codes to labels", () => {
    expect(speakerLabel("agent", labels)).toBe("Агент");
    expect(speakerLabel("customer", labels)).toBe("Клиент");
  });

  it("falls back to unknown for null or unrecognized speakers", () => {
    expect(speakerLabel(null, labels)).toBe("Неизвестно");
    expect(speakerLabel("bot", labels)).toBe("Неизвестно");
  });
});
