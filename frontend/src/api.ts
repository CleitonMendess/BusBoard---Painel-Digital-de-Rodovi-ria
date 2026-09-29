const API_BASE = '';

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

function clearToken() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('role');
}

export function getRole(): string | null {
  return localStorage.getItem('role');
}

export function saveSession(token: string, refreshToken: string, role: string) {
  localStorage.setItem('access_token', token);
  localStorage.setItem('refresh_token', refreshToken);
  localStorage.setItem('role', role);
}

/**
 * Troca o refresh_token por um access_token novo.
 * Vale mesmo com o access_token expirado, que é o caso que importa.
 */
async function renovarAccessToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const dados = await res.json();
    if (!dados.access_token) return false;
    localStorage.setItem('access_token', dados.access_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(path: string, options: RequestInit = {}, jaTentouRenovar = false): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const token = getToken();
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // access token expirou: renova uma vez e repete a requisição
    if (!jaTentouRenovar && (await renovarAccessToken())) {
      return request<T>(path, options, true);
    }
    clearToken();
    window.location.reload();
    throw new Error('Não autorizado');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; refresh_token: string; token_type: string; role?: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    createUser: (data: { name: string; email: string; password: string; role?: string; active?: boolean }) =>
      request<{ mensagem: string; role: string }>('/auth/creat_user', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    refresh: (refreshToken: string) =>
      request<{ access_token: string; token_type: string }>('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }),
    listUsers: () => request<{ Usuarios: AppUser[] }>('/auth/users'),
    changeRole: (userId: number, role: string) =>
      request<{ mensagem: string; user_id: number; role_atual: string }>(`/auth/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }),
    changeActive: (userId: number, active: boolean) =>
      request<{ mensagem: string; user_id: number; active: boolean }>(`/auth/users/${userId}/active`, {
        method: 'PATCH',
        body: JSON.stringify({ active }),
      }),
    delete: (userId: number) =>
      request<{ mensagem: string }>(`/auth/users/${userId}`, {
        method: 'DELETE',
      }),
  },

  board: {
    departures: () => request<{ saidas: Trip[] }>('/board/departures'),
    arrivals: () => request<{ chegadas: Trip[] }>('/board/arrivals'),
    active: () => request<{ em_andamento: Trip[] }>('/board/active'),
  },

  trips: {
    list: () => request<{ Viagens: Trip[] }>('/trips/list'),
    create: (data: CreateTripData) =>
      request<{ mensagem: string; trip: Trip }>('/trips/create_trips', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: number, data: UpdateTripData) =>
      request<{ mensagem: string; trip_id: number }>(`/trips/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ mensagem: string }>(`/trips/${id}`, {
        method: 'DELETE',
      }),
    resetDay: () =>
      request<{ mensagem: string; total: number }>('/trips/reset-day', {
        method: 'POST',
      }),
    updateStatus: (id: number, status: string) =>
      request<{ mensagem: string; trip_id: number; status_atual: string }>(`/trips/status/${id}?status=${encodeURIComponent(status)}`, {
        method: 'PATCH',
      }),
    updateTime: (id: number, data: { scheduled_time: string; estimated_time?: string }) =>
      request<{ mensagem: string; trip_id: number; scheduled_time: string; estimated_time: string }>(`/trips/time/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
  },

  companies: {
    list: () => request<{ Companhias: Company[] }>('/companies/list'),
    create: (data: { name: string; active?: boolean }) =>
      request<{ mensagem: string }>('/companies/create', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: number, data: { name?: string; active?: boolean }) =>
      request<{ mensagem: string }>(`/companies/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ mensagem: string }>(`/companies/${id}`, {
        method: 'DELETE',
      }),
  },

  destinations: {
    list: () => request<{ Destinos: Destination[] }>('/destinations/list'),
    create: (data: { city: string; state: string; active?: boolean }) =>
      request<{ mensagem: string }>('/destinations/create_destinations', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: number, data: { city?: string; state?: string; active?: boolean }) =>
      request<{ mensagem: string }>(`/destinations/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ mensagem: string }>(`/destinations/${id}`, {
        method: 'DELETE',
      }),
  },

  platforms: {
    list: () => request<{ Plataformas: Platform[] }>('/platforms/list'),
    create: (data: { number: number; active?: boolean }) =>
      request<{ mensagem: string }>('/platforms/create_platforms', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: number, data: { number?: number; active?: boolean }) =>
      request<{ mensagem: string }>(`/platforms/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<{ mensagem: string }>(`/platforms/${id}`, {
        method: 'DELETE',
      }),
  },
};

export function logout() {
  clearToken();
}

export interface Trip {
  trip_id: number;
  company: string;
  destination: string;
  platform: number;
  scheduled_time: string;
  estimated_time: string | null;
  status: string;
  type?: string;
  trip_direction?: string;
  id?: number;
  company_id?: number;
  destination_id?: number;
  platform_id?: number;
}

export interface AppUser {
  id: number;
  name: string;
  email: string;
  role: string;
  active: boolean;
}

export interface Company {
  id: number;
  name: string;
  active: boolean;
  created_at: string;
}

export interface Destination {
  id: number;
  city: string;
  state: string;
  active: boolean;
}

export interface Platform {
  id: number;
  number: number;
  active: boolean;
}

export interface CreateTripData {
  type: string;
  trip_direction: string;
  scheduled_time: string;
  estimated_time?: string;
  status?: string;
  company_id: number;
  destination_id: number;
  platform_id: number;
}

export interface UpdateTripData {
  type?: string;
  trip_direction?: string;
  scheduled_time?: string;
  estimated_time?: string; // '' remove a previsão
  status?: string;
  company_id?: number;
  destination_id?: number;
  platform_id?: number;
}