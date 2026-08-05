export interface Service {
  id: string;
  name: string;
  description: string;
  duration_minutes: number;
  price: number;
  active: boolean;
}

export interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
}

export type AppointmentStatus = "confirmed" | "cancelled" | "completed" | "no_show";

export interface Appointment {
  id: string;
  customer: Customer;
  service: Service;
  start_time: string;
  end_time: string;
  status: AppointmentStatus;
  notes: string;
  created_via: string;
}

export interface AvailabilitySlot {
  start: string;
  end: string;
  available: boolean;
}

export interface BookingConfirmation {
  appointment_id: string;
  service_name: string;
  start_time: string;
  customer_name: string;
  customer_email?: string;
  duration_minutes?: number;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  engine: "grok" | "fallback";
}

export interface BusinessInfo {
  business_name: string;
  tagline: string;
  description: string;
  address: string;
  phone: string;
  open_hour: number;
  close_hour: number;
  open_days: number[];
}

export interface Review {
  id: string;
  customer_name: string;
  rating: number;
  comment: string;
  service_name: string | null;
}

export interface AppUser {
  id: string;
  name: string;
  email: string;
}

export interface DashboardStats {
  total_appointments: number;
  upcoming_appointments: number;
  cancelled_appointments: number;
  bookings_today: number;
  busiest_hour: string | null;
  bookings_by_day: Record<string, number>;
  bookings_by_service: Record<string, number>;
}

export interface ChatMessageUI {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}
