import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";

import * as client from "../api/index";
import MonitorSourcesPage from "./MonitorSourcesPage";

vi.mock("../api/index");

function renderWithRouter(component: React.ReactElement) {
  return render(<BrowserRouter>{component}</BrowserRouter>);
}

describe("MonitorSourcesPage 组件交互测试", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (client.getMonitorSources as any).mockResolvedValue([]);
    (client.getCollectorsCapabilities as any).mockResolvedValue({
      collectors: {
        media_crawler: { name: "MediaCrawler 多平台采集器", status: "ready", supports: ["keyword", "competitor_account", "manual_post", "hot_post_rule"], description: "" },
        mock: { name: "演示采集器（Mock）", status: "ready", supports: ["keyword", "competitor_account", "manual_post", "hot_post_rule"], description: "" },
      },
    });
  });

  describe("source_type 与 collector_type 表单联动", () => {
    it("初始化时 keyword 应显示 media_crawler 为默认 collector_type", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue(/media_crawler/);
      expect(collectorSelect).toBeInTheDocument();
    });

    it("keyword source_type 时，collector_type 显示 media_crawler 和 mock", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue(/media_crawler/) as HTMLSelectElement;
      const options = Array.from(collectorSelect.options).map((o) => o.value);

      expect(options).toContain("media_crawler");
      expect(options).toContain("mock");
    });

    it("切换 source_type 到 manual_post 时，collector_type 仍包含 media_crawler 和 mock", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const sourceTypeSelect = screen.getByDisplayValue("关键词");
      await user.selectOptions(sourceTypeSelect, "manual_post");

      await waitFor(() => {
        const collectorSelect = screen.getByDisplayValue(/media_crawler/) as HTMLSelectElement;
        const options = Array.from(collectorSelect.options).map((o) => o.value);

        expect(options).toContain("media_crawler");
        expect(options).toContain("mock");
      });
    });
  });

  describe("动态表单字段显示", () => {
    it("选择 media_crawler 时，显示 login_type 和 cookies 字段", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue(/media_crawler/);
      expect(collectorSelect).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText(/login_type/)).toBeInTheDocument();
      }, { timeout: 5000 });
    });

    it("选择 mock 时，不显示 login_type 和 cookies 字段", async () => {
      const user = userEvent.setup();
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByDisplayValue("关键词")).toBeInTheDocument();
      });

      const collectorSelect = screen.getByDisplayValue(/media_crawler/);
      await user.selectOptions(collectorSelect, "mock");

      await waitFor(() => {
        expect(screen.queryByText(/login_type/)).not.toBeInTheDocument();
      });
    });
  });

  describe("演示模式", () => {
    it("mock 可用时显示一键生成演示数据按钮", async () => {
      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByText(/MediaCrawler 多平台采集器/)).toBeInTheDocument();
      });

      const demoButton = await screen.findByRole("button", { name: /一键生成演示数据/ });
      expect(demoButton).toBeInTheDocument();
    });

    it("mock 不可用时不显示一键生成演示数据按钮", async () => {
      (client.getCollectorsCapabilities as any).mockResolvedValue({
        collectors: {
          media_crawler: { name: "MediaCrawler 多平台采集器", status: "ready", supports: [], description: "" },
        },
      });

      renderWithRouter(<MonitorSourcesPage />);

      await waitFor(() => {
        expect(screen.getByText(/MediaCrawler 多平台采集器/)).toBeInTheDocument();
      });

      expect(screen.queryByRole("button", { name: /一键生成演示数据/ })).not.toBeInTheDocument();
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
        expect(screen.getByText("MediaCrawler 多平台采集器")).toBeInTheDocument();
        expect(screen.getByText("演示采集器（Mock）")).toBeInTheDocument();
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
