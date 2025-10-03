export interface Conversation {
  id: string;
  status: 'OPEN' | 'CLOSED';
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
  conversation_id: string;
  direction: 'SENT' | 'RECEIVED';
  content: string;
  timestamp: string | null;
  created_at: string | null;
  client_id?: string;
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
}