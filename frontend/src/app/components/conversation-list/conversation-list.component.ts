import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewChecked, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Conversation } from '../../models/conversation.model';

@Component({
  selector: 'app-conversation-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './conversation-list.component.html',
  styleUrls: ['./conversation-list.component.css']
})
export class ConversationListComponent implements OnInit, OnChanges, AfterViewChecked {
  @Input() conversations: Conversation[] = [];
  @Input() selectedConversationId: string | null = null;
  @Input() connectionStatus: boolean = false;
  @Input() loading: boolean = false;
  @Input() loadingMore: boolean = false;
  @Input() hasMore: boolean = true;
  @Output() conversationSelected = new EventEmitter<Conversation>();
  @Output() refresh = new EventEmitter<void>();
  @Output() loadMore = new EventEmitter<void>();

  @ViewChild('listContainer') listContainer?: ElementRef;

  filteredConversations: Conversation[] = [];
  searchTerm: string = '';
  statusFilter: string = '';
  private shouldScrollToSelected = false;

  ngOnInit(): void {
    this.applyFilters();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['conversations']) {
      this.applyFilters();
    }
    if (changes['selectedConversationId'] && this.selectedConversationId) {
      this.shouldScrollToSelected = true;
    }
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToSelected && this.selectedConversationId) {
      this.scrollToSelectedConversation();
      this.shouldScrollToSelected = false;
    }
  }

  selectConversation(conversation: Conversation): void {
    this.conversationSelected.emit(conversation);
  }

  private scrollToSelectedConversation(): void {
    if (!this.listContainer) return;

    const container = this.listContainer.nativeElement;
    const selectedElement = container.querySelector(`[data-conversation-id="${this.selectedConversationId}"]`);

    if (selectedElement) {
      selectedElement.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest'
      });
    }
  }

  onRefresh(): void {
    this.refresh.emit();
  }

  applyFilters(): void {
    let filtered = [...this.conversations];

    if (this.statusFilter) {
      filtered = filtered.filter(c => c.status === this.statusFilter);
    }

    if (this.searchTerm) {
      const searchLower = this.searchTerm.toLowerCase();
      filtered = filtered.filter(c =>
        c.last_message?.content.toLowerCase().includes(searchLower) ||
        c.id.toLowerCase().includes(searchLower)
      );
    }

    this.filteredConversations = filtered;
  }

  formatTime(dateString: string | null | undefined): string {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 0) {
      return 'agora';
    }

    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (minutes < 1) {
      return 'agora';
    } else if (hours < 1) {
      return `${minutes}min`;
    } else if (hours < 24) {
      return `${hours}h`;
    } else {
      return `${days}d`;
    }
  }

  getConversationPreview(conversation: Conversation): string {
    if (!conversation.last_message) return 'Sem mensagens';
    const content = conversation.last_message.content;
    return content.length > 50 ? content.substring(0, 50) + '...' : content;
  }

  onScroll(event: Event): void {
    if (!this.hasMore || this.loadingMore) return;

    const element = event.target as HTMLElement;
    const threshold = 50;
    const atBottom = element.scrollHeight - element.scrollTop - element.clientHeight < threshold;

    if (atBottom) {
      this.loadMore.emit();
    }
  }
}