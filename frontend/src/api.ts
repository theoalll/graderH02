// Thin fetch wrapper that injects the auth token and unwraps errors.

import {
  AllocationOrder,
  CaseSchema,
  CaseSummary,
  DeviceType,
  GradeReport,
  SolveResult,
  StudentJSON,
} from "./types";

const TOKEN_KEY = "grader_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init?.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (res.status === 401) {
    setToken(null);
    throw new ApiError(401, "Not authenticated");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string }>("/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request("/logout", { method: "POST" }),

  listCases: () => request<CaseSummary[]>("/cases"),
  getCase: (id: string) => request<CaseSchema>(`/cases/${id}`),
  createCase: (c: CaseSchema) =>
    request<CaseSchema>("/cases", { method: "POST", body: JSON.stringify(c) }),
  updateCase: (id: string, c: CaseSchema) =>
    request<CaseSchema>(`/cases/${id}`, { method: "PUT", body: JSON.stringify(c) }),
  deleteCase: (id: string) => request(`/cases/${id}`, { method: "DELETE" }),

  // Master data: device types
  listDeviceTypes: () => request<DeviceType[]>("/master/device-types"),
  createDeviceType: (d: DeviceType) =>
    request<DeviceType>("/master/device-types", { method: "POST", body: JSON.stringify(d) }),
  updateDeviceType: (code: string, d: DeviceType) =>
    request<DeviceType>(`/master/device-types/${code}`, { method: "PUT", body: JSON.stringify(d) }),
  deleteDeviceType: (code: string) =>
    request(`/master/device-types/${code}`, { method: "DELETE" }),

  solve: (c: CaseSchema, npm: string, allocationOrder: AllocationOrder = "host_desc") =>
    request<SolveResult>("/solve", {
      method: "POST",
      body: JSON.stringify({ case: c, npm, allocation_order: allocationOrder }),
    }),
  parsePkt: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<StudentJSON>("/parse-pkt", { method: "POST", body: fd });
  },
  grade: async (
    c: CaseSchema,
    npm: string,
    file: File,
    allocationOrder: AllocationOrder = "host_desc"
  ) => {
    const fd = new FormData();
    fd.append("case", JSON.stringify(c));
    fd.append("npm", npm);
    fd.append("file", file);
    fd.append("allocation_order", allocationOrder);
    return request<GradeReport>("/grade", { method: "POST", body: fd });
  },
  gradeJson: async (c: CaseSchema, npm: string, student: StudentJSON, allocationOrder: AllocationOrder = "host_desc") => {
    return request<GradeReport>("/grade-json", {
      method: "POST",
      body: JSON.stringify({ case: c, npm, student, allocation_order: allocationOrder }),
    });
  },
};
