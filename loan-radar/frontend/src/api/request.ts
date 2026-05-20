const viteEnv = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
const isDev = viteEnv?.DEV;
const defaultApiBaseUrl = isDev ? "" : "http://localhost:8001";
const rawApiBaseUrl = viteEnv?.VITE_API_BASE_URL || defaultApiBaseUrl;
export const API_BASE_URL = rawApiBaseUrl.replace(/\/$/, "");

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  message: string;
  detail?: string;
};

let _isRefreshing = false;
let _refreshPromise: Promise<boolean> | null = null;

async function tryRefreshToken(): Promise<boolean> {
  if (_isRefreshing && _refreshPromise) {
    return _refreshPromise;
  }
  _isRefreshing = true;
  _refreshPromise = (async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return false;
    try {
      const resp = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!resp.ok) return false;
      const data = await resp.json();
      if (data.access_token) {
        localStorage.setItem("access_token", data.access_token);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      _isRefreshing = false;
      _refreshPromise = null;
    }
  })();
  return _refreshPromise;
}

function forceLogout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (response.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      const newToken = localStorage.getItem("access_token");
      const retryResponse = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
          "Content-Type": "application/json",
          ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
          ...(init?.headers ?? {}),
        },
        ...init,
      });
      if (retryResponse.status === 401) {
        forceLogout();
        throw new Error("登录已过期，请重新登录");
      }
      return parseResponse<T>(retryResponse);
    }
    forceLogout();
    throw new Error("登录已过期，请重新登录");
  }

  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  let payload: ApiResponse<T> | null = null;
  try {
    payload = (await response.json()) as ApiResponse<T>;
  } catch {
    if (!response.ok) {
      throw new Error(`请求失败: ${response.status} ${response.statusText}`);
    }
    throw new Error("响应格式错误，无法解析 JSON");
  }

  if (!response.ok) {
    throw new Error(payload.message || payload.detail || `请求失败: ${response.status} ${response.statusText}`);
  }

  if (payload && typeof payload.success === "boolean") {
    if (!payload.success) {
      throw new Error(payload.message || `请求失败`);
    }
    return payload.data as T;
  }

  return payload as unknown as T;
}

export function buildSearchParams(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  return searchParams.toString();
}
