import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  isLoginMode = signal(true);
  isLoading = signal(false);

  username = '';
  email = '';
  password = '';
  confirmPassword = '';
  firstName = '';
  lastName = '';

  private returnUrl: string = '/';

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private toastService: ToastService
  ) {
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
  }

  toggleMode(): void {
    this.isLoginMode.update(v => !v);
    this.clearForm();
  }

  clearForm(): void {
    this.username = '';
    this.email = '';
    this.password = '';
    this.confirmPassword = '';
    this.firstName = '';
    this.lastName = '';
  }

  onSubmit(): void {
    if (this.isLoginMode()) {
      this.login();
    } else {
      this.register();
    }
  }

  private login(): void {
    if (!this.username || !this.password) {
      this.toastService.showError('Preencha usuário e senha');
      return;
    }

    this.isLoading.set(true);
    this.authService.login({ username: this.username, password: this.password }).subscribe({
      next: () => {
        this.toastService.showSuccess('Login realizado com sucesso');
        this.router.navigate([this.returnUrl]);
      },
      error: (error) => {
        const message = error.error?.detail || 'Erro ao fazer login';
        this.toastService.showError(message);
        this.isLoading.set(false);
      }
    });
  }

  private register(): void {
    if (!this.username || !this.firstName || !this.password) {
      this.toastService.showError('Preencha todos os campos obrigatórios');
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.toastService.showError('As senhas não coincidem');
      return;
    }

    if (this.password.length < 6) {
      this.toastService.showError('A senha deve ter no mínimo 6 caracteres');
      return;
    }

    this.isLoading.set(true);
    this.authService.register({
      username: this.username,
      email: `${this.username}@example.com`,
      password: this.password,
      first_name: this.firstName,
      last_name: ''
    }).subscribe({
      next: () => {
        this.toastService.showSuccess('Registro realizado com sucesso. Faça login.');
        this.isLoginMode.set(true);
        this.clearForm();
        this.isLoading.set(false);
      },
      error: (error) => {
        let message = 'Erro ao registrar usuário';
        if (error.error?.username) {
          message = 'Nome de usuário já existe';
        } else if (error.error?.details) {
          message = error.error.details.join(', ');
        }
        this.toastService.showError(message);
        this.isLoading.set(false);
      }
    });
  }
}
