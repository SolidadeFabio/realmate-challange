import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Contact } from '../../models/conversation.model';

@Component({
  selector: 'app-contact-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './contact-modal.component.html',
  styleUrls: ['./contact-modal.component.css']
})
export class ContactModalComponent implements OnInit {
  @Input() show: boolean = false;
  @Input() contact: Contact | null = null;
  @Output() save = new EventEmitter<Partial<Contact>>();
  @Output() cancel = new EventEmitter<void>();

  formData: Partial<Contact> = {
    name: '',
    phone: '',
    email: ''
  };

  ngOnInit() {
    this.resetForm();
  }

  ngOnChanges() {
    if (this.show) {
      this.resetForm();
    }
  }

  resetForm() {
    if (this.contact) {
      this.formData = {
        name: this.contact.name || '',
        phone: this.contact.phone || '',
        email: this.contact.email || ''
      };
    } else {
      this.formData = {
        name: '',
        phone: '',
        email: ''
      };
    }
  }

  onSubmit() {
    if (this.formData.name || this.formData.phone) {
      this.save.emit(this.formData);
    }
  }

  onCancel() {
    this.cancel.emit();
  }

  get isValid(): boolean {
    return !!(this.formData.name?.trim() || this.formData.phone?.trim());
  }
}