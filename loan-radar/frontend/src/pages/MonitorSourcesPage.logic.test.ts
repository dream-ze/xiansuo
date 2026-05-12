import { describe, expect, it } from "vitest";

import {
  DEFAULT_CREATE_FORM,
  buildPayloadFromForm,
  getAllowedCollectorTypesBySourceType,
  getDynamicFieldKeysByCollectorType,
  type CreateFormState,
} from "./MonitorSourcesPage";

function buildForm(overrides: Partial<CreateFormState>): CreateFormState {
  return {
    ...DEFAULT_CREATE_FORM,
    ...overrides,
  };
}

describe("MonitorSourcesPage source_type 与 collector_type 联动", () => {
  it("keyword 仅允许 mock/external_api/xhs", () => {
    expect(getAllowedCollectorTypesBySourceType("keyword")).toEqual(["mock", "external_api", "xhs"]);
  });

  it("manual_post 仅允许 playwright/generic_web/xhs", () => {
    expect(getAllowedCollectorTypesBySourceType("manual_post")).toEqual(["playwright", "generic_web", "xhs"]);
  });

  it("未知 source_type 回退为 mock", () => {
    expect(getAllowedCollectorTypesBySourceType("unknown")).toEqual(["mock"]);
  });
});

describe("MonitorSourcesPage 动态字段", () => {
  it("external_api 字段集合正确", () => {
    expect(getDynamicFieldKeysByCollectorType("external_api")).toEqual([
      "entry_url",
      "endpoint",
      "api_key_env",
      "max_posts",
      "max_comments_per_post",
    ]);
  });

  it("generic_web 字段集合正确", () => {
    expect(getDynamicFieldKeysByCollectorType("generic_web")).toContain("selectors.post_container");
    expect(getDynamicFieldKeysByCollectorType("generic_web")).toContain("selectors.comment_item");
  });

  it("xhs 字段集合包含 cookies 与可选 selectors", () => {
    const fields = getDynamicFieldKeysByCollectorType("xhs");
    expect(fields).toContain("cookies");
    expect(fields).toContain("selectors.note_container");
  });
});

describe("MonitorSourcesPage 表单校验", () => {
  it("manual_post + playwright 的 value 必须是 http/https", () => {
    const form = buildForm({
      source_type: "manual_post",
      collector_type: "playwright",
      value: "not-a-url",
    });

    expect(() => buildPayloadFromForm(form)).toThrow("manual_post + playwright 时，value 必须是 http/https URL");
  });

  it("generic_web 必须有 entry_url 或 value", () => {
    const form = buildForm({
      source_type: "manual_post",
      collector_type: "generic_web",
      value: "",
      entry_url: "",
    });

    expect(() => buildPayloadFromForm(form)).toThrow("generic_web 必须填写 entry_url 或 value");
  });

  it("external_api 必须有 endpoint", () => {
    const form = buildForm({
      collector_type: "external_api",
      endpoint: "",
    });

    expect(() => buildPayloadFromForm(form)).toThrow("external_api 必须填写 endpoint");
  });

  it("xhs 必须有 cookies", () => {
    const form = buildForm({
      collector_type: "xhs",
      cookies: "",
      value: "https://www.xiaohongshu.com/explore",
    });

    expect(() => buildPayloadFromForm(form)).toThrow("xhs 必须填写 cookies");
  });

  it("max_posts/max_comments_per_post 必须是正整数", () => {
    const form = buildForm({
      max_posts: "0",
      max_comments_per_post: "-1",
    });

    expect(() => buildPayloadFromForm(form)).toThrow("max_posts 必须是正整数");
  });

  it("external_api 合法配置可生成 payload", () => {
    const form = buildForm({
      source_type: "keyword",
      collector_type: "external_api",
      value: "征信修复",
      endpoint: "https://api.example.com/collect",
      api_key_env: "EXTERNAL_COLLECTOR_API_KEY",
      max_posts: "5",
      max_comments_per_post: "10",
    });

    const payload = buildPayloadFromForm(form);
    expect((payload.config as Record<string, unknown>).collector_type).toBe("external_api");
    expect((payload.config as Record<string, unknown>).external_api).toMatchObject({
      endpoint: "https://api.example.com/collect",
    });
  });
});
