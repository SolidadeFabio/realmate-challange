import { Component, OnInit, OnDestroy, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConversationListComponent } from '../../components/conversation-list/conversation-list.component';
import { ConversationDetailComponent } from '../../components/conversation-detail/conversation-detail.component';
import { ContactSelectorComponent } from '../../components/contact-selector/contact-selector.component';
import { ContactModalComponent } from '../../components/contact-modal/contact-modal.component';
import { NewConversationModalComponent } from '../../components/new-conversation-modal/new-conversation-modal.component';
import { WebSocketService } from '../../services/websocket.service';
import { ToastService } from '../../services/toast.service';
import { AuthService } from '../../services/auth.service';
import { ContactService } from '../../services/contact.service';
import { Conversation, Contact } from '../../models/conversation.model';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-conversations',
  standalone: true,
  imports: [
    CommonModule,
    ConversationListComponent,
    ConversationDetailComponent,
    ContactSelectorComponent,
    ContactModalComponent,
    NewConversationModalComponent
  ],
  templateUrl: './conversations.component.html',
  styleUrls: ['./conversations.component.css']
})
export class ConversationsComponent implements OnInit, OnDestroy {
  @ViewChild('newConversationModal') newConversationModal?: NewConversationModalComponent;

  conversations: Conversation[] = [];
  selectedConversation: Conversation | null = null;
  connectionStatus = false;
  loading = false;
  loadingMore = false;
  hasMore = true;
  canSendInternalMessages = false;

  showNewConversationModal = false;
  showContactSelector = false;
  showContactModal = false;
  editingContact: Contact | null = null;
  selectingContactFor: 'conversation' | 'newConversation' = 'conversation';

  private destroy$ = new Subject<void>();

  constructor(
    private websocketService: WebSocketService,
    private toastService: ToastService,
    private authService: AuthService,
    private contactService: ContactService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.canSendInternalMessages = this.authService.isAuthenticated();
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

  onSendMessage(messageData: {content: string, isInternal: boolean}): void {
    if (this.selectedConversation) {
      this.websocketService.sendMessage(this.selectedConversation.id, messageData.content, messageData.isInternal);
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

  onNewConversation(): void {
    this.showNewConversationModal = true;
  }

  onNewConversationCreated(data: {content: string, contact: Contact | null}): void {
    const contactId = data.contact?.id;
    this.websocketService.createConversation(data.content, contactId);
    this.showNewConversationModal = false;
  }

  onNewConversationCancelled(): void {
    this.showNewConversationModal = false;
  }

  onSelectContactForNewConversation(): void {
    this.selectingContactFor = 'newConversation';
    this.showContactSelector = true;
  }

  onAssignContact(): void {
    this.selectingContactFor = 'conversation';
    this.showContactSelector = true;
  }

  async onContactSelected(contact: Contact): Promise<void> {
    this.showContactSelector = false;

    if (this.selectingContactFor === 'newConversation') {
      if (this.newConversationModal) {
        this.newConversationModal.setContact(contact);
      }
    } else if (this.selectedConversation) {
      try {
        await this.contactService.assignContactToConversation(
          this.selectedConversation.id,
          contact.id
        );

        await this.websocketService.getConversationDetail(this.selectedConversation.id);

        const conversations = this.conversations.map(conv => {
          if (conv.id === this.selectedConversation!.id) {
            return { ...conv, contact };
          }
          return conv;
        });
        this.conversations = conversations;

        this.toastService.showSuccess('Contato vinculado com sucesso');
      } catch (error) {
        this.toastService.showError('Erro ao vincular contato');
      }
    }
  }

  onNewContactFromSelector(): void {
    this.showContactSelector = false;
    this.editingContact = null;
    this.showContactModal = true;
  }

  onCancelContactSelector(): void {
    this.showContactSelector = false;
  }

  async onSaveContact(contactData: Partial<Contact>): Promise<void> {
    try {
      if (this.editingContact) {
        await this.contactService.updateContact(this.editingContact.id, contactData);
        this.toastService.showSuccess('Contato atualizado');
      } else {
        const newContact = await this.contactService.createContact(contactData);
        this.toastService.showSuccess('Contato criado');

        if (this.selectedConversation && !this.selectedConversation.contact) {
          await this.onContactSelected(newContact);
        }
      }
      this.showContactModal = false;
      this.editingContact = null;
    } catch (error) {
      this.toastService.showError('Erro ao salvar contato');
    }
  }

  onCancelContactModal(): void {
    this.showContactModal = false;
    this.editingContact = null;
    if (!this.selectedConversation?.contact) {
      this.showContactSelector = true;
    }
  }
}
