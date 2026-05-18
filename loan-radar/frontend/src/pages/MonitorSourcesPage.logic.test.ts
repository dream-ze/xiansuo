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
  it("keyword 允许 media_crawler 和 mock", () => {
    expect(getAllowedCollectorTypesBySourceType("keyword")).toEqual(["media_crawler", "mock"]);
  });

  it("manual_post 允许 media_crawler 和 mock", () => {
    expect(getAllowedCollectorTypesBySourceType("manual_post")).toEqual(["media_crawler", "mock"]);
  });

  it("未知 source_type 回退为 mock", () => {
    expect(getAllowedCollectorTypesBySourceType("unknown")).toEqual(["mock"]);
  });
});

describe("MonitorSourcesPage 动态字段", () => {
  it("media_crawler 字段集合包含 login_type 与 cookies", () => {
    const fields = getDynamicFieldKeysByCollectorType("media_crawler");
    expect(fields).toContain("login_type");
    expect(fields).toContain("cookies");
    expect(fields).toContain("enable_comments");
  });

  it("mock 字段集合仅包含 max_posts 和 max_comments_per_post", () => {
    const fields = getDynamicFieldKeysByCollectorType("mock");
    expect(fields).toEqual(["max_posts", "max_comments_per_post"]);
  });
});

describe("MonitorSourcesPage 表单校验", () => {
  it("max_posts/max_comments_per_post 必须是正整数", () => {
    const form = buildForm({
      max_posts: "0",
      max_comments_per_post: "-1",
    });

    expect(() => buildPayloadFromForm(form)).toThrow("max_posts 必须是正整数");
  });

  it("media_crawler 合法配置可生成 payload", () => {
    const form = buildForm({
      source_type: "keyword",
      collector_type: "media_crawler",
      platform: "xhs",
      value: "征信花了",
      login_type: "cookie",
      cookies: "sessionid=abc123",
      enable_comments: true,
      max_posts: "20",
      max_comments_per_post: "50",
    });

    const payload = buildPayloadFromForm(form);
    expect((payload.config as Record<string, unknown>).collector_type).toBe("media_crawler");
    expect((payload.config as Record<string, unknown>).login_type).toBe("cookie");
    expect((payload.config as Record<string, unknown>).enable_comments).toBe(true);
  });

  it("mock 合法配置可生成 payload", () => {
    const form = buildForm({
      source_type: "keyword",
      collector_type: "mock",
      platform: "xhs",
      value: "征信花了",
      max_posts: "5",
      max_comments_per_post: "10",
    });

    const payload = buildPayloadFromForm(form);
    expect((payload.config as Record<string, unknown>).collector_type).toBe("mock");
    expect((payload.config as Record<string, unknown>).max_posts).toBe(5);
    expect((payload.config as Record<string, unknown>).max_comments_per_post).toBe(10);
  });
});
