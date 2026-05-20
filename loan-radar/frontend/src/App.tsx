import { Component, type ReactNode } from "react";
import { Button, ConfigProvider, Result, theme } from "antd";
import zhCN from "antd/locale/zh_CN";

import AppRoutes from "./routes";

const SASS_TOKEN = {
  colorPrimary: "#2F54EB",
  colorInfo: "#2F54EB",
  colorSuccess: "#52C41A",
  colorWarning: "#FAAD14",
  colorError: "#FF4D4F",
  colorBgLayout: "#F0F2F5",
  colorBgContainer: "#FFFFFF",
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
  boxShadow: "0 1px 2px 0 rgba(0,0,0,0.03), 0 1px 6px -1px rgba(0,0,0,0.02), 0 2px 4px 0 rgba(0,0,0,0.02)",
  boxShadowSecondary: "0 6px 16px 0 rgba(0,0,0,0.08), 0 3px 6px -4px rgba(0,0,0,0.12), 0 9px 28px 8px rgba(0,0,0,0.05)",
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
          algorithm: theme.defaultAlgorithm,
          token: SASS_TOKEN,
          components: {
            Layout: {
              siderBg: "#001529",
              headerBg: "#FFFFFF",
              bodyBg: "#F0F2F5",
            },
            Menu: {
              darkItemBg: "#001529",
              darkSubMenuItemBg: "#000C17",
              darkItemSelectedBg: "#2F54EB",
              darkItemHoverBg: "rgba(47,84,235,0.15)",
              darkItemColor: "rgba(255,255,255,0.65)",
              darkItemSelectedColor: "#FFFFFF",
              darkItemHoverColor: "#FFFFFF",
              itemBorderRadius: 6,
              itemMarginInline: 8,
              itemHeight: 40,
              collapsedIconSize: 18,
              iconSize: 16,
            },
            Card: {
              paddingLG: 20,
              padding: 16,
            },
            Table: {
              headerBg: "#FAFAFA",
              headerColor: "#1F1F1F",
              rowHoverBg: "#F5F7FA",
              headerBorderRadius: 0,
              fontSize: 13,
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
            },
          },
        }}
      >
        <AppRoutes />
      </ConfigProvider>
    </GlobalErrorBoundary>
  );
}
