import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { LoginRequest, RegisterRequest, AuthTokens, User } from '../models/auth.model';
import { environment } from '../../environments/environment';

interface JWTPayload {
  user_id: string;
  username?: string;
  exp: number;
  iat: number;
  token_type: string;
  [key: string]: unknown;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly TOKEN_KEY = 'auth_access_token';
  private readonly REFRESH_KEY = 'auth_refresh_token';
  private readonly API_URL = `${environment.apiUrl}/auth`;

  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  isAuthenticated = signal<boolean>(false);
  currentUser = computed(() => this.currentUserSubject.value);

  constructor(private http: HttpClient) {
    this.checkInitialAuth();
  }

  private checkInitialAuth(): void {
    const token = this.getAccessToken();
    if (token) {
      this.loadCurrentUser().subscribe({
        next: () => this.isAuthenticated.set(true),
        error: () => {
          this.clearTokens();
          this.isAuthenticated.set(false);
        }
      });
    }
  }

  register(data: RegisterRequest): Observable<User> {
    return this.http.post<User>(`${this.API_URL}/register/`, data);
  }

  login(credentials: LoginRequest): Observable<AuthTokens> {
    return this.http.post<AuthTokens>(`${this.API_URL}/login/`, credentials).pipe(
      tap(tokens => {
        this.setTokens(tokens);
        this.isAuthenticated.set(true);
        this.loadCurrentUser().subscribe();
      }),
      catchError(error => {
        this.isAuthenticated.set(false);
        return throwError(() => error);
      })
    );
  }

  logout(): void {
    this.clearTokens();
    this.currentUserSubject.next(null);
    this.isAuthenticated.set(false);
  }

  refreshToken(): Observable<AuthTokens> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => new Error('No refresh token available'));
    }

    return this.http.post<AuthTokens>(`${this.API_URL}/refresh/`, {
      refresh: refreshToken
    }).pipe(
      tap(tokens => this.setTokens(tokens)),
      catchError(error => {
        this.logout();
        return throwError(() => error);
      })
    );
  }

  loadCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.API_URL}/me/`).pipe(
      tap(user => this.currentUserSubject.next(user)),
      catchError(error => {
        this.currentUserSubject.next(null);
        return throwError(() => error);
      })
    );
  }

  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    return sessionStorage.getItem(this.TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    return sessionStorage.getItem(this.REFRESH_KEY);
  }

  private setTokens(tokens: AuthTokens): void {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem(this.TOKEN_KEY, tokens.access);
    sessionStorage.setItem(this.REFRESH_KEY, tokens.refresh);
  }

  private clearTokens(): void {
    if (typeof window === 'undefined') return;
    sessionStorage.removeItem(this.TOKEN_KEY);
    sessionStorage.removeItem(this.REFRESH_KEY);
  }

  isTokenExpired(token: string): boolean {
    try {
      const payload = this.decodeToken(token);
      if (!payload || !payload.exp) return true;

      const expirationDate = new Date(payload.exp * 1000);
      return expirationDate <= new Date();
    } catch {
      return true;
    }
  }

  private decodeToken(token: string): JWTPayload | null {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload) as JWTPayload;
    } catch {
      throw new Error('Invalid token');
    }
  }

  validateToken(token: string): boolean {
    try {
      const payload = this.decodeToken(token);
      return !!(payload && payload.user_id && !this.isTokenExpired(token));
    } catch {
      return false;
    }
  }
}
