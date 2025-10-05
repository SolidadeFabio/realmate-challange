import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Contact } from '../../models/conversation.model';

@Component({
  selector: 'app-new-conversation-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './new-conversation-modal.component.html',
  styleUrls: ['./new-conversation-modal.component.css']
})
export class NewConversationModalComponent {
  @Input() show = false;
  @Output() created = new EventEmitter<{content: string, contact: Contact | null}>();
  @Output() cancelled = new EventEmitter<void>();
  @Output() selectContact = new EventEmitter<void>();

  content = '';
  selectedContact: Contact | null = null;

  onCreate(): void {
    if (this.content.trim() && this.selectedContact) {
      this.created.emit({
        content: this.content.trim(),
        contact: this.selectedContact
      });
      this.content = '';
      this.selectedContact = null;
    }
  }

  onCancel(): void {
    this.content = '';
    this.selectedContact = null;
    this.cancelled.emit();
  }

  onSelectContact(): void {
    this.selectContact.emit();
  }

  clearContact(): void {
    this.selectedContact = null;
  }

  setContact(contact: Contact): void {
    this.selectedContact = contact;
  }
}
