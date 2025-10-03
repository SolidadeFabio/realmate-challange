import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConversationListComponent } from './components/conversation-list/conversation-list.component';
import { ConversationDetailComponent } from './components/conversation-detail/conversation-detail.component';
import { ToastComponent } from './components/toast/toast.component';
import { WebSocketService } from './services/websocket.service';
import { ToastService } from './services/toast.service';
import { Conversation } from './models/conversation.model';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ConversationListComponent, ConversationDetailComponent, ToastComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit, OnDestroy {
  conversations: Conversation[] = [];
  selectedConversation: Conversation | null = null;
  connectionStatus = false;
  loading = false;
  loadingMore = false;
  hasMore = true;

  private destroy$ = new Subject<void>();

  constructor(
    private websocketService: WebSocketService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.initializeSubscriptions();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private initializeSubscriptions(): void {
    this.websocketService.conversations$
      .pipe(takeUntil(this.destroy$))
      .subscribe(conversations => {
        this.conversations = conversations;
        this.cdr.detectChanges();
      });

    this.websocketService.currentConversation$
      .pipe(takeUntil(this.destroy$))
      .subscribe(conversation => {
        this.selectedConversation = conversation;
        this.cdr.detectChanges();
      });

    this.websocketService.connectionStatus$
      .pipe(takeUntil(this.destroy$))
      .subscribe(status => {
        this.connectionStatus = status;
        this.cdr.detectChanges();
      });

    this.websocketService.loading$
      .pipe(takeUntil(this.destroy$))
      .subscribe(loading => {
        this.loading = loading;
        this.cdr.detectChanges();
      });

    this.websocketService.loadingMore$
      .pipe(takeUntil(this.destroy$))
      .subscribe(loadingMore => {
        this.loadingMore = loadingMore;
        this.hasMore = this.websocketService.hasMore();
        this.cdr.detectChanges();
      });

    this.websocketService.errors$
      .pipe(takeUntil(this.destroy$))
      .subscribe(error => {
        if (error) {
          this.toastService.showError(error);
        }
      });

    this.websocketService.success$
      .pipe(takeUntil(this.destroy$))
      .subscribe(message => {
        if (message) {
          this.toastService.showSuccess(message);
        }
      });
  }

  onConversationSelected(conversation: Conversation): void {
    this.websocketService.getConversationDetail(conversation.id);
  }

  onRefresh(): void {
    this.websocketService.getConversations();
  }

  onSendMessage(message: string): void {
    if (this.selectedConversation) {
      this.websocketService.sendMessage(this.selectedConversation.id, message);
    }
  }

  onCloseConversation(): void {
    if (this.selectedConversation) {
      this.websocketService.closeConversation(this.selectedConversation.id);
    }
  }

  onLoadMore(): void {
    this.websocketService.loadMoreConversations();
  }

  onNewConversation(content: string): void {
    this.websocketService.createConversation(content);
  }
}