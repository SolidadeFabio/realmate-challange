import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subject, timer } from 'rxjs';
import { Conversation, Message, WebSocketMessage } from '../models/conversation.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class WebSocketService implements OnDestroy {
  private socket: WebSocket | null = null;
  private readonly wsUrl = this.getWebSocketUrl();
  private readonly reconnectDelay = 3000;

  private currentPage = 1;
  private hasMorePages = true;

  private readonly conversationsSubject = new BehaviorSubject<Conversation[]>([]);
  private readonly currentConversationSubject = new BehaviorSubject<Conversation | null>(null);
  private readonly connectionStatusSubject = new BehaviorSubject<boolean>(false);
  private readonly errorSubject = new Subject<string>();
  private readonly loadingSubject = new BehaviorSubject<boolean>(false);
  private readonly conversationLoadingSubject = new BehaviorSubject<boolean>(false);
  private readonly loadingMoreSubject = new BehaviorSubject<boolean>(false);
  private readonly successSubject = new Subject<string>();

  public readonly conversations$ = this.conversationsSubject.asObservable();
  public readonly currentConversation$ = this.currentConversationSubject.asObservable();
  public readonly connectionStatus$ = this.connectionStatusSubject.asObservable();
  public readonly errors$ = this.errorSubject.asObservable();
  public readonly loading$ = this.loadingSubject.asObservable();
  public readonly conversationLoading$ = this.conversationLoadingSubject.asObservable();
  public readonly loadingMore$ = this.loadingMoreSubject.asObservable();
  public readonly success$ = this.successSubject.asObservable();

  constructor(private apiService: ApiService) {
    this.initialize();
  }

  private async initialize(): Promise<void> {
    await this.loadInitialData();
    this.connect();
  }

  ngOnDestroy(): void {
    this.disconnect();
  }

  private getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    return `${protocol}//${host}:80/ws/conversations/`;
  }

  private async loadInitialData(): Promise<void> {
    this.loadingSubject.next(true);
    this.currentPage = 1;
    this.hasMorePages = true;

    try {
      const response = await this.apiService.getConversations(1);
      const conversations = response.results || response;
      this.hasMorePages = !!response.next;

      const conversationsWithUnread = conversations.map((conv: Conversation) => ({
        ...conv,
        unread_count: 0
      }));
      this.conversationsSubject.next(conversationsWithUnread);
    } catch (error) {
      this.errorSubject.next('Failed to load conversations');
    } finally {
      this.loadingSubject.next(false);
    }
  }

  private connect(): void {
    try {
      this.socket = new WebSocket(this.wsUrl);
      this.setupSocketHandlers();
    } catch (error) {
      this.connectionStatusSubject.next(false);
      this.scheduleReconnect();
    }
  }

  private setupSocketHandlers(): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      this.connectionStatusSubject.next(true);
    };

    this.socket.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.socket.onerror = () => {
      this.connectionStatusSubject.next(false);
      this.errorSubject.next('Connection error');
    };

    this.socket.onclose = () => {
      this.connectionStatusSubject.next(false);
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    timer(this.reconnectDelay).subscribe(() => this.connect());
  }

  private handleMessage(data: WebSocketMessage): void {
    switch (data.type) {
      case 'new_message':
        if (data.message) {
          this.handleNewMessage(data.message);
        }
        break;

      case 'new_conversation':
        if (data.conversation) {
          this.addNewConversation(data.conversation);
        }
        break;

      case 'conversation_updated':
        if (data.conversation) {
          this.updateConversation(data.conversation);
        }
        break;

      case 'error':
        if (data.error) {
          this.errorSubject.next(data.error);
        }
        break;
    }
  }

  private handleNewMessage(message: Message): void {
    const currentConv = this.currentConversationSubject.value;
    const isCurrentConversation = currentConv && currentConv.id === message.conversation_id;

    if (isCurrentConversation) {
      const updatedConversation = {
        ...currentConv,
        messages: [...(currentConv.messages || []), message]
      };
      this.currentConversationSubject.next(updatedConversation);
    }

    const conversations = this.conversationsSubject.value;
    const updatedConversations = conversations.map(conv => {
      if (conv.id === message.conversation_id) {
        const shouldIncrementUnread =
          message.direction === 'RECEIVED' && !isCurrentConversation;

        return {
          ...conv,
          last_message: message,
          message_count: (conv.message_count || 0) + 1,
          unread_count: shouldIncrementUnread
            ? (conv.unread_count || 0) + 1
            : (conv.unread_count || 0)
        };
      }
      return conv;
    });
    this.conversationsSubject.next(updatedConversations);
  }

  private addNewConversation(conversation: Conversation): void {
    const conversations = this.conversationsSubject.value;
    this.conversationsSubject.next([conversation, ...conversations]);
  }

  private updateConversation(conversation: Conversation): void {
    const conversations = this.conversationsSubject.value;
    const updatedConversations = conversations.map(conv =>
      conv.id === conversation.id ? conversation : conv
    );
    this.conversationsSubject.next(updatedConversations);

    const currentConv = this.currentConversationSubject.value;
    if (currentConv && currentConv.id === conversation.id) {
      this.getConversationDetail(conversation.id);
    }
  }

  public async getConversations(): Promise<void> {
    this.loadingSubject.next(true);
    try {
      const response = await this.apiService.getConversations(1);
      const conversations = response.results || response;
      this.conversationsSubject.next(conversations);
    } catch (error) {
      this.errorSubject.next('Failed to refresh conversations');
    } finally {
      this.loadingSubject.next(false);
    }
  }

  public async getConversationDetail(conversationId: string): Promise<void> {
    this.conversationLoadingSubject.next(true);
    this.resetUnreadCount(conversationId);

    try {
      const response = await this.apiService.getConversationMessages(conversationId);
      const conversation: Conversation = {
        id: conversationId,
        status: response.status,
        created_at: response.created_at,
        updated_at: response.updated_at,
        closed_at: response.closed_at,
        messages: response.messages,
        unread_count: 0
      };
      this.currentConversationSubject.next(conversation);
    } catch (error) {
      this.errorSubject.next('Failed to load conversation details');
    } finally {
      this.conversationLoadingSubject.next(false);
    }
  }

  private resetUnreadCount(conversationId: string): void {
    const conversations = this.conversationsSubject.value;
    const updatedConversations = conversations.map(conv => {
      if (conv.id === conversationId) {
        return { ...conv, unread_count: 0 };
      }
      return conv;
    });
    this.conversationsSubject.next(updatedConversations);
  }

  public sendMessage(conversationId: string, content: string): void {
    if (!content.trim()) return;

    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.errorSubject.next('WebSocket not connected');
      return;
    }

    const message = {
      type: 'send_message',
      conversation_id: conversationId,
      content: content.trim()
    };

    try {
      this.socket.send(JSON.stringify(message));
    } catch (error) {
      this.errorSubject.next('Failed to send message');
    }
  }

  public async closeConversation(conversationId: string): Promise<void> {
    this.loadingSubject.next(true);
    try {
      const response = await this.apiService.closeConversation(conversationId);

      const conversations = this.conversationsSubject.value;
      const updatedConversations = conversations.map(conv => {
        if (conv.id === conversationId) {
          return { ...conv, status: 'CLOSED' as 'CLOSED', closed_at: response.closed_at };
        }
        return conv;
      });
      this.conversationsSubject.next(updatedConversations);

      const currentConv = this.currentConversationSubject.value;
      if (currentConv && currentConv.id === conversationId) {
        this.currentConversationSubject.next({
          ...currentConv,
          status: 'CLOSED',
          closed_at: response.closed_at
        });
      }

      this.successSubject.next('Conversa fechada com sucesso');
    } catch (error) {
      this.errorSubject.next('Failed to close conversation');
    } finally {
      this.loadingSubject.next(false);
    }
  }

  public async loadMoreConversations(): Promise<void> {
    if (!this.hasMorePages || this.loadingMoreSubject.value) {
      return;
    }

    this.loadingMoreSubject.next(true);
    this.currentPage++;

    try {
      const response = await this.apiService.getConversations(this.currentPage);
      const newConversations = response.results || response;
      this.hasMorePages = !!response.next;

      const conversationsWithUnread = newConversations.map((conv: Conversation) => ({
        ...conv,
        unread_count: 0
      }));

      const existingConversations = this.conversationsSubject.value;
      this.conversationsSubject.next([...existingConversations, ...conversationsWithUnread]);
    } catch (error) {
      this.errorSubject.next('Failed to load more conversations');
      this.currentPage--;
    } finally {
      this.loadingMoreSubject.next(false);
    }
  }

  public hasMore(): boolean {
    return this.hasMorePages;
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}