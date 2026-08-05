import type {
  Appointment,
  AvailabilitySlot,
  BusinessInfo,
  ChatResponse,
  DashboardStats,
  Review,
  AppUser,
  Service,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore parse failure, use statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<{ status: string; ai_engine: string }>("/api/health"),

  listServices: () => request<Service[]>("/api/services"),

  sendChatMessage: (message: string, sessionId?: string | null) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId || undefined }),
    }),

  getAvailability: (serviceId: string, date: string) =>
    request<AvailabilitySlot[]>(
      `/api/availability?service_id=${encodeURIComponent(serviceId)}&date=${date}`
    ),

  getBusinessInfo: () => request<BusinessInfo>("/api/business"),

  listReviews: () => request<Review[]>("/api/reviews"),

  book: (payload: {
    service_id: string;
    start_time: string;
    customer_name: string;
    customer_email: string;
    customer_phone?: string;
    notes?: string;
  }) =>
    request<Appointment>("/api/book", { method: "POST", body: JSON.stringify(payload) }),

  cancelBooking: (appointmentId: string) =>
    request<Appointment>(`/api/book/${appointmentId}/cancel`, { method: "PATCH" }),

  rescheduleBooking: (
    appointmentId: string,
    payload: {
      service_id: string;
      start_time: string;
      customer_name: string;
      customer_email: string;
    }
  ) =>
    request<Appointment>(`/api/book/${appointmentId}/reschedule`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  userLogin: (name: string, email?: string) =>
    request<AppUser>("/api/users/login", { method: "POST", body: JSON.stringify({ name, email }) }),

  getUserAppointments: (email: string) =>
    request<Appointment[]>(`/api/users/appointments?email=${encodeURIComponent(email)}`),

  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  admin: {
    getBusinessSettings: (token: string) =>
      request<BusinessInfo>("/api/admin/business", {}, token),
    updateBusinessSettings: (token: string, payload: Partial<BusinessInfo>) =>
      request<BusinessInfo>(
        "/api/admin/business",
        { method: "PATCH", body: JSON.stringify(payload) },
        token
      ),
    setupChat: (token: string, message: string, sessionId?: string | null) =>
      request<{ session_id: string; reply: string; engine: string }>(
        "/api/admin/setup-chat",
        { method: "POST", body: JSON.stringify({ message, session_id: sessionId || undefined }) },
        token
      ),
    listAppointments: (token: string, statusFilter?: string) =>
      request<Appointment[]>(
        `/api/admin/appointments${statusFilter ? `?status_filter=${statusFilter}` : ""}`,
        {},
        token
      ),
    stats: (token: string) => request<DashboardStats>("/api/admin/stats", {}, token),
    cancel: (token: string, id: string) =>
      request<Appointment>(`/api/admin/appointments/${id}/cancel`, { method: "PATCH" }, token),
    complete: (token: string, id: string) =>
      request<Appointment>(`/api/admin/appointments/${id}/complete`, { method: "PATCH" }, token),
    noShow: (token: string, id: string) =>
      request<Appointment>(`/api/admin/appointments/${id}/no-show`, { method: "PATCH" }, token),
    reschedule: (token: string, id: string, newStartTime: string) =>
      request<Appointment>(
        `/api/admin/appointments/${id}/reschedule`,
        { method: "PATCH", body: JSON.stringify({ new_start_time: newStartTime }) },
        token
      ),
    listAllServices: (token: string) =>
      request<Service[]>("/api/admin/services", {}, token),
    ragStatus: (token: string) =>
      request<Record<string, unknown>>("/api/admin/rag/status", {}, token),
    ragReindex: (token: string) =>
      request<{ ok: boolean; chunks_indexed: number }>(
        "/api/admin/rag/reindex",
        { method: "POST" },
        token
      ),
    ragSearch: (token: string, query: string) =>
      request<{ results: { source: string; text: string; score: number }[] }>(
        `/api/admin/rag/search?query=${encodeURIComponent(query)}`,
        {},
        token
      ),
  },
};

export { ApiError };
