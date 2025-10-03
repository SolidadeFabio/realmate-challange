import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-new-conversation-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './new-conversation-modal.component.html',
  styleUrls: ['./new-conversation-modal.component.css']
})
export class NewConversationModalComponent {
  @Input() show = false;
  @Output() created = new EventEmitter<string>();
  @Output() cancelled = new EventEmitter<void>();

  content = '';

  onCreate(): void {
    if (this.content.trim()) {
      this.created.emit(this.content.trim());
      this.content = '';
    }
  }

  onCancel(): void {
    this.content = '';
    this.cancelled.emit();
  }
}
