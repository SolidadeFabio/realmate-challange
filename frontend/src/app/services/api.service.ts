import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Conversation } from '../models/conversation.model';
import {
  ConversationListResponse,
  ConversationMessagesResponse,
  CreateConversationRequest
} from '../models/api-responses.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  async getConversations(page: number = 1): Promise<ConversationListResponse> {
    return firstValueFrom(
      this.http.get<ConversationListResponse>(`${this.apiUrl}/conversations/?page=${page}`)
    );
  }

  async getConversationMessages(conversationId: string): Promise<ConversationMessagesResponse> {
    return firstValueFrom(
      this.http.get<ConversationMessagesResponse>(`${this.apiUrl}/conversations/${conversationId}/messages/`)
    );
  }

  async closeConversation(conversationId: string): Promise<Conversation> {
    return firstValueFrom(
      this.http.post<Conversation>(`${this.apiUrl}/conversations/${conversationId}/close/`, {})
    );
  }

  async createConversation(content: string, contactId?: string): Promise<Conversation> {
    const body: CreateConversationRequest = { content };
    if (contactId) {
      body.contact_id = contactId;
    }
    return firstValueFrom(
      this.http.post<Conversation>(`${this.apiUrl}/conversations/`, body)
    );
  }
}
