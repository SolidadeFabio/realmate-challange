export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name?: string;
}

export interface Contact {
  id: string;
  name: string | null;
  phone: string | null;
  email: string | null;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  status: 'OPEN' | 'CLOSED';
  contact: Contact | null;
  assigned_user: User | null;
  created_at: string | null;
  updated_at: string | null;
  closed_at: string | null;
  message_count?: number;
  unread_count?: number;
  last_message?: Message | null;
  messages?: Message[];
}

export interface Message {
  id: string;
  conversation: string;
  direction: 'SENT' | 'RECEIVED';
  content: string;
  timestamp: string | null;
  author_user: User | null;
  is_internal?: boolean;
  created_at: string | null;
}

export interface ConversationFilters {
  status?: 'OPEN' | 'CLOSED' | '';
  search?: string;
  date_from?: string;
  date_to?: string;
}

export interface WebSocketMessage {
  type: string;
  conversations?: Conversation[];
  conversation?: Conversation;
  message?: Message;
  error?: string;
  can_view_internal?: boolean;
}