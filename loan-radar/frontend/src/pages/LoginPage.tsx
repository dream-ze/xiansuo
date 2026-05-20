import { useState } from "react";
import { Button, Card, Form, Input, message, Tabs } from "antd";

const API_BASE = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.DEV ? "" : "http://localhost:8001";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");

  const onSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const response = await fetch(`${API_BASE}${endpoint}`, {
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
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#f5f5f5" }}>
      <Card style={{ width: 400 }}>
        <h2 style={{ textAlign: "center", marginBottom: 24 }}>线索雷达</h2>
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
