import { describe, expect, it } from "vitest";

import { getQrLoginErrorMessage } from "./qr-login-panel";

describe("getQrLoginErrorMessage", () => {
  it("uses fetch request Error messages from the API layer", () => {
    expect(getQrLoginErrorMessage(new Error("XHS PC QR code generation failed: timeout"))).toBe(
      "XHS PC QR code generation failed: timeout",
    );
  });
});
