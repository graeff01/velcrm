// ============================================
// 💬 COMPONENTE DE MENSAGEM DO CHAT
// ============================================

import { useEffect, useRef, useState } from 'react';
import { Bot, User, UserCircle } from 'lucide-react';

/**
 * Componente para renderizar uma mensagem individual
 */
export function ChatMessage({ message, currentUser }) {
  const senderType = message.sender_type || 'lead';
  const senderName = message.sender_name || getSenderName(senderType);
  
  function getSenderName(type) {
    if (type === 'ia') return 'Assistente IA';
    if (type === 'vendedor') return currentUser?.name || 'Você';
    return 'Cliente';
  }

  function getAvatar(type) {
    if (type === 'ia') return <Bot size={18} />;
    if (type === 'vendedor') return <UserCircle size={18} />;
    return <User size={18} />;
  }

  function formatTime(timestamp) {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('pt-BR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch {
      return '';
    }
  }

  return (
    <div className={`message from-${senderType}`}>
      <div className="message-avatar">
        {getAvatar(senderType)}
      </div>
      
      <div className="message-bubble">
        {senderType !== 'lead' && (
          <div className="message-sender">{senderName}</div>
        )}
        <div className="message-content">{message.content}</div>
        <div className="message-time">{formatTime(message.timestamp)}</div>
      </div>
    </div>
  );
}

/**
 * Componente de indicador de digitação
 */
export function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <div className="message-avatar">
        <Bot size={18} />
      </div>
      <div className="typing-dots">
        <span></span>
        <span></span>
        <span></span>
        <span className="typing-text">IA digitando...</span>
      </div>
    </div>
  );
}

/**
 * Container de mensagens com scroll automático
 */
export function ChatMessagesContainer({ 
  messages, 
  currentUser, 
  isAITyping = false 
}) {
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // Auto-scroll para última mensagem
  useEffect(() => {
    if (shouldAutoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [messages, isAITyping, shouldAutoScroll]);

  // Detectar se usuário scrollou manualmente
  const handleScroll = () => {
    if (!containerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    setShouldAutoScroll(isNearBottom);
  };

  // Normalizar estrutura de mensagens
  const normalizedMessages = Array.isArray(messages) 
    ? messages 
    : messages?.items || [];

  if (normalizedMessages.length === 0 && !isAITyping) {
    return (
      <div className="chat-messages">
        <div className="no-messages">
          <Bot size={48} color="#8696a0" />
          <p style={{ marginTop: '12px' }}>Nenhuma mensagem ainda</p>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>
            Inicie a conversa ou aguarde o contato do lead
          </p>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="chat-messages" 
      ref={containerRef}
      onScroll={handleScroll}
    >
      {normalizedMessages.map((msg, index) => (
        <ChatMessage 
          key={index} 
          message={msg} 
          currentUser={currentUser} 
        />
      ))}
      
      {isAITyping && <TypingIndicator />}
      
      <div ref={messagesEndRef} />
    </div>
  );
}

export default ChatMessagesContainer;