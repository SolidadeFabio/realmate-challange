import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getAccessToken();

  if (token && authService.validateToken(token)) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !req.url.includes('/auth/')) {
        const refreshToken = authService.getRefreshToken();

        if (refreshToken) {
          return authService.refreshToken().pipe(
            switchMap(tokens => {
              const clonedReq = req.clone({
                setHeaders: {
                  Authorization: `Bearer ${tokens.access}`
                }
              });
              return next(clonedReq);
            }),
            catchError(refreshError => {
              authService.logout();
              return throwError(() => refreshError);
            })
          );
        } else {
          authService.logout();
        }
      }

      return throwError(() => error);
    })
  );
};
