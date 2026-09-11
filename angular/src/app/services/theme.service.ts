import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private themeSubject = new BehaviorSubject<'dark'>('dark');
  public theme$ = this.themeSubject.asObservable();

  constructor() {
    this.initTheme();
  }

  get currentTheme(): 'dark' {
    return 'dark';
  }

  get isDarkMode(): boolean {
    return true;
  }

  initTheme(): void {
    this.applyTheme('dark');
  }

  toggleTheme(): void {
    this.applyTheme('dark');
  }

  setTheme(theme: 'light' | 'dark'): void {
    this.applyTheme('dark');
  }

  private applyTheme(theme: 'dark'): void {
    this.themeSubject.next('dark');
    localStorage.setItem('nekohentai_theme', 'dark');
    localStorage.setItem('nekohentai_theme', 'dark');

    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', 'dark');
      document.body.classList.remove('light');
      document.body.classList.add('dark');
    }
  }
}
