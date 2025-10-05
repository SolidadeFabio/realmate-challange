import { Routes } from '@angular/router';
import { ConversationsComponent } from './pages/conversations/conversations.component';
import { LoginComponent } from './components/login/login.component';
import { authGuard, publicOnlyGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    component: ConversationsComponent,
    canActivate: [authGuard]
  },
  {
    path: 'login',
    component: LoginComponent,
    canActivate: [publicOnlyGuard]
  },
  {
    path: '**',
    redirectTo: ''
  }
];
