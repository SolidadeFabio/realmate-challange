import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.css']
})
export class NavbarComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  user = computed(() => this.authService.currentUser());
  isAuthenticated = this.authService.isAuthenticated;

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  getUserDisplay(): string {
    const user = this.user();
    if (!user) return 'Usuário';

    if (user.first_name || user.last_name) {
      return `${user.first_name} ${user.last_name}`.trim();
    }

    return user.username;
  }
}
