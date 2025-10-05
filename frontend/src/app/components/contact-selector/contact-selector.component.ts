import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Contact } from '../../models/conversation.model';
import { ContactService } from '../../services/contact.service';

@Component({
  selector: 'app-contact-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './contact-selector.component.html',
  styleUrls: ['./contact-selector.component.css']
})
export class ContactSelectorComponent implements OnInit {
  @Input() show: boolean = false;
  @Output() contactSelected = new EventEmitter<Contact>();
  @Output() newContact = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  contacts: Contact[] = [];
  searchTerm: string = '';
  selectedContactId: string | null = null;

  constructor(private contactService: ContactService) {}

  ngOnInit() {
    this.contactService.contacts$.subscribe(contacts => {
      this.contacts = contacts;
    });
  }

  get filteredContacts(): Contact[] {
    if (!this.searchTerm) {
      return this.contacts;
    }
    const term = this.searchTerm.toLowerCase();
    return this.contacts.filter(contact =>
      contact.name?.toLowerCase().includes(term) ||
      contact.phone?.toLowerCase().includes(term) ||
      contact.email?.toLowerCase().includes(term)
    );
  }

  selectContact(contact: Contact) {
    this.selectedContactId = contact.id;
  }

  onConfirm() {
    const contact = this.contacts.find(c => c.id === this.selectedContactId);
    if (contact) {
      this.contactSelected.emit(contact);
    }
  }

  onNewContact() {
    this.newContact.emit();
  }

  onCancel() {
    this.cancel.emit();
    this.searchTerm = '';
    this.selectedContactId = null;
  }
}