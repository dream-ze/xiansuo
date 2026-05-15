import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";

import * as client from "../api/client";
import MonitorSourcesPage from "./MonitorSourcesPage";

vi.mock("../api/client");

function renderWithRouter(component: React.ReactElement) {
  return render(<BrowserRouter>{component}</BrowserRouter>);
}

describe("MonitorSourcesPage 组件交互测试", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (client.getMonitorSources as any).mockResolvedValue([]);
    (client.getCollectorsCapabilities as any).mockResolvedValue({
      collectors: {
        mock: { name: "Mock", status: "ready", supports: [], description: "" },
        playwright: { name: "Playwright", status: "ready", supports: [], description: "" },
        external_api: { name: "External API", status: "ready", supports: [], description: "" },
        generic_web: { name: "Generic Web", status: "ready", supports: [], description: "" },
        media_crawler: { name: "MediaCrawler", status: "ready", supports: [], description: "" },
      },
    });
  });

  describe("source_type 与 collector_type 表单联动", () => {
    it("初始化时 keyword 应限制 collector_type 只显示 mock", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue("mock：演示 / 回归测试");
      expect(collectorSelect).toBeInTheDocument();
    });

    it("切换 source_type 到 manual_post 时，collector_type 自动切换为 playwright", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const sourceTypeSelect = screen.getByDisplayValue("关键词");
      await user.selectOptions(sourceTypeSelect, "manual_post");

      await waitFor(() => {
        expect(screen.getByDisplayValue("playwright：指定公开帖子链接")).toBeInTheDocument();
      });
    });

    it("keyword source_type 时，collector_type 只显示 mock、media_crawler、external_api", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue("mock：演示 / 回归测试") as HTMLSelectElement;
      const options = Array.from(collectorSelect.options).map((o) => o.value);

      expect(options).toContain("mock");
      expect(options).toContain("media_crawler");
      expect(options).toContain("external_api");
      expect(options).not.toContain("playwright");
    });

    it("manual_post source_type 时，collector_type 只显示 playwright、media_crawler、generic_web", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const sourceTypeSelect = screen.getByDisplayValue("关键词");
      await user.selectOptions(sourceTypeSelect, "manual_post");

      await waitFor(() => {
        const collectorSelect = screen.getByDisplayValue("playwright：指定公开帖子链接") as HTMLSelectElement;
        const options = Array.from(collectorSelect.options).map((o) => o.value);

        expect(options).toContain("playwright");
        expect(options).toContain("media_crawler");
        expect(options).toContain("generic_web");
        expect(options).not.toContain("mock");
      });
    });
  });

  describe("动态表单字段显示", () => {
    it("选择 external_api 时，显示 endpoint 和 api_key_env 字段", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue("mock：演示 / 回归测试");
      await user.selectOptions(collectorSelect, "external_api");

      await waitFor(() => {
        expect(screen.getByPlaceholderText("https://your-api.example.com/collect")).toBeInTheDocument();
        expect(screen.getByPlaceholderText("EXTERNAL_COLLECTOR_API_KEY")).toBeInTheDocument();
      });
    });

    it("选择 generic_web 时，显示 selectors 字段集合", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const sourceTypeSelect = screen.getByDisplayValue("关键词");
      await user.selectOptions(sourceTypeSelect, "manual_post");

      const collectorSelect = screen.getByDisplayValue("playwright：指定公开帖子链接");
      await user.selectOptions(collectorSelect, "generic_web");

      await waitFor(() => {
        expect(screen.getByPlaceholderText("article, .post")).toBeInTheDocument();
        expect(screen.getByPlaceholderText("h1, h2")).toBeInTheDocument();
        expect(screen.getByPlaceholderText("article, .content")).toBeInTheDocument();
      });
    });

    it("选择 media_crawler 时，显示 login_type 和 cookies 字段", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue("mock：演示 / 回归测试");
      await user.selectOptions(collectorSelect, "media_crawler");

      await waitFor(() => {
        expect(screen.getByText(/login_type/)).toBeInTheDocument();
      }, { timeout: 5000 });
    });
  });

  describe("表单校验与错误提示", () => {
    it("external_api 缺少 endpoint 时提交显示错误", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue("mock：演示 / 回归测试");
      await user.selectOptions(collectorSelect, "external_api");

      await waitFor(() => {
        expect(screen.getByPlaceholderText("https://your-api.example.com/collect")).toBeInTheDocument();
      });

      const submitButton = screen.getByText("新增");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/external_api 必须填写 endpoint/)).toBeInTheDocument();
      });
    });

    it("外部API缺少api_key_env时也应该允许提交（可选字段）", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue("mock：演示 / 回归测试");
      await user.selectOptions(collectorSelect, "external_api");

      await waitFor(() => {
        expect(screen.getByPlaceholderText("https://your-api.example.com/collect")).toBeInTheDocument();
      });

      const endpointInput = screen.getByPlaceholderText("https://your-api.example.com/collect");
      expect(endpointInput).toBeInTheDocument();
    });

    it("manual_post + playwright 的 value 不是 URL 时提交显示错误", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const sourceTypeSelect = screen.getByDisplayValue("关键词");
      await user.selectOptions(sourceTypeSelect, "manual_post");

      await waitFor(() => {
        expect(screen.getByDisplayValue("playwright：指定公开帖子链接")).toBeInTheDocument();
      });

      const valueInput = screen.getByDisplayValue("");
      await user.type(valueInput, "not-a-url");

      const submitButton = screen.getByText("新增");
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/manual_post \+ playwright 时，value 必须是 http\/https URL/)).toBeInTheDocument();
      });
    });
  });

  describe("采集器能力加载", () => {
    it("页面加载时应调用 getCollectorsCapabilities", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(client.getCollectorsCapabilities).toHaveBeenCalled();
      });
    });

    it("采集器能力表格应显示所有注册的采集器", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByText("Mock")).toBeInTheDocument();
        expect(screen.getByText("Playwright")).toBeInTheDocument();
        expect(screen.getByText("External API")).toBeInTheDocument();
      });
    });

    it("采集器能力加载失败时显示错误提示", async () => {
      (client.getCollectorsCapabilities as any).mockRejectedValue(new Error("Failed"));

      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByText("采集器能力加载失败")).toBeInTheDocument();
      });
    });
  });
});
