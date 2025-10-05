import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Contact } from '../models/conversation.model';

@Injectable({
  providedIn: 'root'
})
export class ContactService {
  private readonly apiUrl = environment.apiUrl;
  private contactsSubject = new BehaviorSubject<Contact[]>([]);
  public contacts$ = this.contactsSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadContacts();
  }

  async loadContacts(): Promise<void> {
    try {
      const contacts = await firstValueFrom(
        this.http.get<Contact[]>(`${this.apiUrl}/contacts/`)
      );
      this.contactsSubject.next(contacts);
    } catch (error) {
      console.error('Failed to load contacts', error);
    }
  }

  async createContact(contact: Partial<Contact>): Promise<Contact> {
    const newContact = await firstValueFrom(
      this.http.post<Contact>(`${this.apiUrl}/contacts/`, contact)
    );
    await this.loadContacts();
    return newContact;
  }

  async updateContact(id: string, contact: Partial<Contact>): Promise<Contact> {
    const updated = await firstValueFrom(
      this.http.patch<Contact>(`${this.apiUrl}/contacts/${id}/`, contact)
    );
    await this.loadContacts();
    return updated;
  }

  async deleteContact(id: string): Promise<void> {
    await firstValueFrom(
      this.http.delete(`${this.apiUrl}/contacts/${id}/`)
    );
    await this.loadContacts();
  }

  async assignContactToConversation(conversationId: string, contactId: string): Promise<void> {
    await firstValueFrom(
      this.http.patch(`${this.apiUrl}/conversations/${conversationId}/assign-contact/`, {
        contact_id: contactId
      })
    );
  }

  getContacts(): Contact[] {
    return this.contactsSubject.value;
  }
}