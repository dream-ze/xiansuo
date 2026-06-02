import { RadarChartOutlined } from "@ant-design/icons";
import { useState } from "react";
import { Button, Card, Form, Input, message, Tabs } from "antd";

import { API_BASE_URL } from "../api/request";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");

  const onSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || (mode === "login" ? "登录失败" : "注册失败"));
      }

      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      window.location.href = "/";
    } catch (err) {
      message.error(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "100vh",
      background: "linear-gradient(135deg, #0a0e1a 0%, #0d1525 50%, #0a1020 100%)",
      position: "relative",
      overflow: "hidden",
    }}>
      <div style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `
          radial-gradient(ellipse at 20% 50%, rgba(0,212,255,0.06) 0%, transparent 50%),
          radial-gradient(ellipse at 80% 50%, rgba(0,102,255,0.04) 0%, transparent 50%)
        `,
        pointerEvents: "none",
      }} />
      <Card style={{
        width: 400,
        background: "rgba(17,24,39,0.85)",
        border: "1px solid rgba(0,212,255,0.15)",
        borderRadius: 12,
        boxShadow: "0 0 30px rgba(0,212,255,0.1), 0 8px 32px rgba(0,0,0,0.5)",
        backdropFilter: "blur(12px)",
        position: "relative",
        zIndex: 1,
      }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <RadarChartOutlined style={{ fontSize: 36, color: "#00d4ff", filter: "drop-shadow(0 0 8px rgba(0,212,255,0.5))", marginBottom: 8, display: "block" }} />
          <h2 style={{ margin: 0, color: "rgba(255,255,255,0.88)", fontSize: 20, fontWeight: 600, textShadow: "0 0 12px rgba(0,212,255,0.2)" }}>智获客雷达</h2>
          <div style={{ fontSize: 11, color: "rgba(0,212,255,0.5)", letterSpacing: "0.15em", marginTop: 4 }}>LEAD INTELLIGENCE RADAR</div>
        </div>
        <Tabs
          activeKey={mode}
          onChange={(key) => setMode(key as "login" | "register")}
          items={[
            { key: "login", label: "登录" },
            { key: "register", label: "注册" },
          ]}
          centered
        />
        <Form onFinish={onSubmit} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              {mode === "login" ? "登录" : "注册"}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
