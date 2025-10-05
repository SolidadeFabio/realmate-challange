import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Conversation, Message } from '../../models/conversation.model';
import { ConfirmModalComponent } from '../confirm-modal/confirm-modal.component';

@Component({
  selector: 'app-conversation-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, ConfirmModalComponent],
  templateUrl: './conversation-detail.component.html',
  styleUrls: ['./conversation-detail.component.css']
})
export class ConversationDetailComponent {
  @Input() conversation: Conversation | null = null;
  @Input() loading: boolean = false;
  @Input() canSendInternalMessages: boolean = false;
  @Output() sendMessage = new EventEmitter<{content: string, isInternal: boolean}>();
  @Output() closeConversation = new EventEmitter<void>();
  @Output() assignContact = new EventEmitter<void>();

  newMessage: string = '';
  showCloseModal = false;
  isInternalMessage = false;

  onSendMessage(event: Event): void {
    event.preventDefault();

    if (!this.newMessage.trim() || !this.conversation || this.conversation.status === 'CLOSED') {
      return;
    }

    this.sendMessage.emit({
      content: this.newMessage,
      isInternal: this.isInternalMessage
    });
    this.newMessage = '';
  }

  onCloseConversation(): void {
    if (this.conversation && this.conversation.status === 'OPEN') {
      this.showCloseModal = true;
    }
  }

  confirmClose(): void {
    this.showCloseModal = false;
    this.closeConversation.emit();
  }

  cancelClose(): void {
    this.showCloseModal = false;
  }

  onAssignContact(): void {
    this.assignContact.emit();
  }

  formatTime(timestamp: string | null | undefined): string {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getMessageAlignment(message: Message): string {
    return message.direction === 'SENT' ? 'sent' : 'received';
  }

  scrollToBottom(): void {
    setTimeout(() => {
      const messagesContainer = document.querySelector('.messages-container');
      if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    }, 100);
  }

  getFilteredMessages(): Message[] {
    if (!this.conversation?.messages) return [];

    if (!this.canSendInternalMessages) {
      return this.conversation.messages.filter(msg => !msg.is_internal);
    }

    return this.conversation.messages;
  }

  ngOnChanges(): void {
    if (this.conversation?.messages) {
      this.scrollToBottom();
    }
  }
}