import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { ApiService } from './api.service';
import { User } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private api: ApiService) {
    this.loadUserFromStorage();
  }

  private loadUserFromStorage(): void {
    const userJson = localStorage.getItem('nekohentai_user') || localStorage.getItem('nekohentai_user');
    if (userJson) {
      try {
        this.currentUserSubject.next(JSON.parse(userJson));
      } catch (e) {
        localStorage.removeItem('nekohentai_user');
        localStorage.removeItem('nekohentai_user');
      }
    }
  }

  public get currentUserValue(): User | null {
    return this.currentUserSubject.value;
  }

  public get isLoggedIn(): boolean {
    return !!this.currentUserValue;
  }

  public get isAdmin(): boolean {
    return this.currentUserValue?.role?.toLowerCase() === 'admin';
  }

  private saveUserToStorage(user: User): void {
    if (user && user.token) {
      localStorage.setItem('nekohentai_token', user.token);
      localStorage.setItem('nekohentai_user', JSON.stringify(user));
      localStorage.setItem('nekohentai_token', user.token);
      localStorage.setItem('nekohentai_user', JSON.stringify(user));
      this.currentUserSubject.next(user);
    }
  }

  login(credentials: { usernameOrEmail: string; password: string }): Observable<User> {
    return this.api.post<User>('auth/login', credentials).pipe(
      tap((user) => this.saveUserToStorage(user))
    );
  }

  googleLogin(idToken: string): Observable<User> {
    return this.api.post<User>('auth/google-login', { idToken }).pipe(
      tap((user) => this.saveUserToStorage(user))
    );
  }

  register(data: { username: string; email: string; password: string; fullName?: string }): Observable<User> {
    return this.api.post<User>('auth/register', data).pipe(
      tap((user) => this.saveUserToStorage(user))
    );
  }

  updateCurrentUser(updatedUserPartial: Partial<User>): void {
    const current = this.currentUserValue;
    if (current) {
      const updatedUser = { ...current, ...updatedUserPartial };
      localStorage.setItem('nekohentai_user', JSON.stringify(updatedUser));
      localStorage.setItem('nekohentai_user', JSON.stringify(updatedUser));
      this.currentUserSubject.next(updatedUser);
    }
  }

  refreshToken(): Observable<User> {
    return this.api.post<User>('auth/refresh-token', {}).pipe(
      tap((user) => this.saveUserToStorage(user))
    );
  }

  logout(): void {
    this.api.post('auth/logout', {}).subscribe({
      next: () => {},
      error: () => {}
    });
    localStorage.removeItem('nekohentai_token');
    localStorage.removeItem('nekohentai_user');
    localStorage.removeItem('nekohentai_token');
    localStorage.removeItem('nekohentai_user');
    this.currentUserSubject.next(null);
  }
}
