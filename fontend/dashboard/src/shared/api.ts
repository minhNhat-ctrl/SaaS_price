/**
 * Shared API client
 * Quy ước: API URL cố định, không sinh động
 * 
 * Sử dụng relative URL để Nginx proxy tự động forward tới backend
 * ProfilePage và AuthContext đã hoạt động với pattern này
 */

// Empty base URL = relative paths, proxied by Nginx
const API_BASE_URL = process.env.REACT_APP_API_URL || "";

interface Headers {
  [key: string]: string;
}

const defaultHeaders: Headers = {
  "Content-Type": "application/json",
};

/**
 * Simple fetch wrapper
 */
class ApiClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private getAuthToken(): string | null {
    return localStorage.getItem("auth_token");
  }

  private getHeaders(): Headers {
    const token = this.getAuthToken();
    const headers: Headers = { ...defaultHeaders };
    
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    return headers;
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "GET",
      headers: this.getHeaders(),
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "POST",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "PUT",
      headers: this.getHeaders(),
      credentials: "include",
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: "DELETE",
      headers: this.getHeaders(),
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }
}

export const api = new ApiClient(API_BASE_URL);
