import { Conversation, Message, Contact, User } from './conversation.model';

export interface ConversationListResponse {
  results: Conversation[];
  count: number;
  next: string | null;
  previous: string | null;
}

export interface ConversationMessagesResponse {
  id?: string;
  status: 'OPEN' | 'CLOSED';
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  messages: Message[];
  contact?: Contact | null;
  assigned_user?: User | null;
}

export interface CreateConversationRequest {
  content: string;
  contact_id?: string;
}