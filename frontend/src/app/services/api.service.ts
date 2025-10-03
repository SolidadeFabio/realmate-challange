import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly apiUrl = 'http://localhost:80/api';

  constructor(private http: HttpClient) {}

  async getConversations(page: number = 1): Promise<any> {
    return firstValueFrom(
      this.http.get<any>(`${this.apiUrl}/conversations/?page=${page}`)
    );
  }

  async getConversationMessages(conversationId: string): Promise<any> {
    return firstValueFrom(
      this.http.get<any>(`${this.apiUrl}/conversations/${conversationId}/messages/`)
    );
  }

  async closeConversation(conversationId: string): Promise<any> {
    return firstValueFrom(
      this.http.post<any>(`${this.apiUrl}/conversations/${conversationId}/close/`, {})
    );
  }
}
