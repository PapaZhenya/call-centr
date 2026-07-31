import { describe, expect, it } from "vitest";
import { ApiError } from "./api-client";

describe("ApiError", () => {
  it("carries the HTTP status and message", () => {
    const error = new ApiError(404, "Call not found");
    expect(error.status).toBe(404);
    expect(error.message).toBe("Call not found");
    expect(error).toBeInstanceOf(Error);
  });
});
