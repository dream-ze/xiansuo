import { Component, type ReactNode } from "react";
import { Button, ConfigProvider, Result, theme } from "antd";
import zhCN from "antd/locale/zh_CN";

import AppRoutes from "./routes";

const SASS_TOKEN = {
  colorPrimary: "#00d4ff",
  colorInfo: "#00d4ff",
  colorSuccess: "#00e396",
  colorWarning: "#ffb020",
  colorError: "#ff4560",
  colorBgLayout: "#0a0e1a",
  colorBgContainer: "#111827",
  colorBgElevated: "#1a2035",
  colorBorder: "rgba(0,212,255,0.15)",
  colorBorderSecondary: "rgba(0,212,255,0.08)",
  colorText: "rgba(255,255,255,0.88)",
  colorTextSecondary: "rgba(255,255,255,0.55)",
  colorTextTertiary: "rgba(255,255,255,0.35)",
  colorFill: "rgba(0,212,255,0.06)",
  colorFillSecondary: "rgba(0,212,255,0.04)",
  colorFillTertiary: "rgba(0,212,255,0.03)",
  borderRadius: 6,
  borderRadiusLG: 8,
  borderRadiusSM: 4,
  fontSize: 13,
  fontSizeHeading1: 22,
  fontSizeHeading2: 18,
  fontSizeHeading3: 16,
  fontSizeSM: 12,
  controlHeight: 32,
  controlHeightLG: 40,
  controlHeightSM: 26,
  padding: 16,
  paddingLG: 24,
  paddingSM: 12,
  paddingXS: 8,
  margin: 16,
  marginLG: 24,
  marginSM: 12,
  marginXS: 8,
  boxShadow: "0 0 12px rgba(0,212,255,0.08), 0 2px 8px rgba(0,0,0,0.4)",
  boxShadowSecondary: "0 0 20px rgba(0,212,255,0.1), 0 4px 16px rgba(0,0,0,0.5)",
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif",
  wireframe: false,
};

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class GlobalErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面出现错误"
          subTitle="抱歉，页面发生了意外错误。请尝试刷新页面。"
          extra={[
            <Button type="primary" key="reload" onClick={() => window.location.reload()}>
              刷新页面
            </Button>,
            <Button key="back" onClick={() => { this.handleReload(); window.location.href = "/"; }}>
              返回首页
            </Button>,
          ]}
        />
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <GlobalErrorBoundary>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: theme.darkAlgorithm,
          token: SASS_TOKEN,
          components: {
            Layout: {
              siderBg: "#060a14",
              headerBg: "rgba(10,14,26,0.85)",
              bodyBg: "#0a0e1a",
            },
            Menu: {
              darkItemBg: "transparent",
              darkSubMenuItemBg: "rgba(0,212,255,0.04)",
              darkItemSelectedBg: "rgba(0,212,255,0.15)",
              darkItemHoverBg: "rgba(0,212,255,0.08)",
              darkItemColor: "rgba(255,255,255,0.55)",
              darkItemSelectedColor: "#00d4ff",
              darkItemHoverColor: "rgba(0,212,255,0.85)",
              itemBorderRadius: 6,
              itemMarginInline: 8,
              itemHeight: 38,
              collapsedIconSize: 18,
              iconSize: 16,
            },
            Card: {
              paddingLG: 16,
              padding: 12,
              colorBgContainer: "rgba(17,24,39,0.75)",
              colorBorderSecondary: "rgba(0,212,255,0.1)",
            },
            Table: {
              headerBg: "rgba(0,212,255,0.06)",
              headerColor: "rgba(0,212,255,0.85)",
              rowHoverBg: "rgba(0,212,255,0.06)",
              headerBorderRadius: 0,
              fontSize: 13,
              colorBgContainer: "rgba(17,24,39,0.6)",
              colorBorderSecondary: "rgba(0,212,255,0.08)",
            },
            Statistic: {
              titleFontSize: 12,
              contentFontSize: 24,
            },
            Tag: {
              borderRadiusSM: 4,
            },
            Button: {
              borderRadius: 6,
              controlHeight: 32,
              colorPrimary: "#00d4ff",
              colorPrimaryHover: "#33ddff",
              algorithm: true,
            },
            Input: {
              colorBgContainer: "rgba(17,24,39,0.8)",
              colorBorder: "rgba(0,212,255,0.15)",
              colorBorderHover: "rgba(0,212,255,0.4)",
              activeBorderColor: "#00d4ff",
            },
            Select: {
              colorBgContainer: "rgba(17,24,39,0.8)",
              colorBorder: "rgba(0,212,255,0.15)",
              optionSelectedBg: "rgba(0,212,255,0.15)",
            },
            Tabs: {
              inkBarColor: "#00d4ff",
              itemActiveColor: "#00d4ff",
              itemSelectedColor: "#00d4ff",
              itemHoverColor: "rgba(0,212,255,0.7)",
            },
            Modal: {
              contentBg: "#111827",
              headerBg: "#111827",
            },
            Drawer: {
              colorBgElevated: "#111827",
            },
            Dropdown: {
              colorBgElevated: "#1a2035",
            },
            Tooltip: {
              colorBgSpotlight: "#1a2035",
            },
            Badge: {
              colorBgContainer: "#0a0e1a",
            },
          },
        }}
      >
        <AppRoutes />
      </ConfigProvider>
    </GlobalErrorBoundary>
  );
}
