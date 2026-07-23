import { api } from './api';
import type { AuthProvidersResponse, CurrentUser } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  provider: string;
  username: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/api/auth/login', { username, password });
  return data;
}

export async function fetchProviders(): Promise<AuthProvidersResponse> {
  const { data } = await api.get<AuthProvidersResponse>('/api/auth/providers');
  return data;
}

export async function fetchMe(): Promise<CurrentUser> {
  const { data } = await api.get<CurrentUser>('/api/auth/me');
  return data;
}
