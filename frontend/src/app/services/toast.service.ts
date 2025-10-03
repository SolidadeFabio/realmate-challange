import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface Toast {
  id: number;
  message: string;
  type: 'error' | 'success' | 'info';
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toastsSubject = new BehaviorSubject<Toast[]>([]);
  public toasts$ = this.toastsSubject.asObservable();
  private nextId = 1;

  showError(message: string, duration: number = 4000): void {
    this.show(message, 'error', duration);
  }

  showSuccess(message: string, duration: number = 4000): void {
    this.show(message, 'success', duration);
  }

  showInfo(message: string, duration: number = 4000): void {
    this.show(message, 'info', duration);
  }

  private show(message: string, type: Toast['type'], duration: number): void {
    const toast: Toast = {
      id: this.nextId++,
      message,
      type
    };

    const currentToasts = this.toastsSubject.value;
    this.toastsSubject.next([...currentToasts, toast]);

    setTimeout(() => {
      this.remove(toast.id);
    }, duration);
  }

  remove(id: number): void {
    const currentToasts = this.toastsSubject.value;
    this.toastsSubject.next(currentToasts.filter(t => t.id !== id));
  }
}
