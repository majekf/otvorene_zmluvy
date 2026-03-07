/**
 * ChatBar — fixed bottom bar with contextual chatbot (Phase 5)
 *
 * Features:
 * - Streaming token display over WebSocket
 * - Degraded-mode banner when no LLM API key is configured
 * - Stop/cancel generation button
 * - Scope-refusal suggestion panel
 * - Source provenance expandable panel
 * - Full keyboard navigation (Enter to send, Escape to cancel)
 * - Dynamic placeholder from active FilterState
 * - Accessible (ARIA roles, labels)
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchChatStatus, chatWebSocketUrl } from '../api';
import type {
  FilterState,
  ChatMessage,
  ChatFrame,
  ProvenanceItem,
  ScopeRefusalData,
  ChatStatusResponse,
} from '../types';

interface ChatBarProps {
  filters: FilterState;
  onFilterUpdate?: (filters: Partial<FilterState>) => void;
  contractCount?: number;
}

export default function ChatBar({ filters, onFilterUpdate, contractCount }: ChatBarProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState<ChatStatusResponse | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [provenance, setProvenance] = useState<ProvenanceItem[]>([]);
  const [showSources, setShowSources] = useState(false);
  const [scopeRefusal, setScopeRefusal] = useState<ScopeRefusalData | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [sessionId] = useState(() => crypto.randomUUID?.() || Math.random().toString(36).slice(2));

  const wsRef = useRef<WebSocket | null>(null);
  const streamBufferRef = useRef('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch chat status on mount
  useEffect(() => {
    fetchChatStatus()
      .then(setStatus)
      .catch(() => setStatus({ provider: 'mock', degraded: true, features: [] }));
  }, []);

  // Auto-scroll message list
  useEffect(() => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streaming]);

  // Dynamic placeholder
  const placeholder = (() => {
    const parts: string[] = [];
    if (filters.institutions?.length) {
      parts.push(filters.institutions.join(', '));
    }
    if (filters.categories?.length) {
      parts.push(filters.categories.join(', '));
    }
    if (filters.date_from || filters.date_to) {
      parts.push(
        [filters.date_from, filters.date_to].filter(Boolean).join(' – '),
      );
    }
    const scope = parts.length ? parts.join(' — ') : 'all contracts';
    const countHint =
      contractCount !== undefined ? ` (${contractCount} contracts)` : '';
    return `Ask about ${scope}${countHint}`;
  })();

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || streaming) return;
    // degraded = mock mode; WebSocket still works, just returns mock responses

    setInput('');
    setExpanded(true);
    setScopeRefusal(null);
    setProvenance([]);
    setShowSources(false);
    setConnectionError(null);

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: text }]);

    // Open WebSocket
    const ws = new WebSocket(chatWebSocketUrl());
    wsRef.current = ws;
    streamBufferRef.current = '';
    setStreaming(true);

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          message: text,
          filters,
          session_id: sessionId,
        }),
      );
    };

    ws.onmessage = (event) => {
      try {
        const frame: ChatFrame = JSON.parse(event.data);

        switch (frame.type) {
          case 'start':
            // Generation started
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: '' },
            ]);
            break;

          case 'token':
            streamBufferRef.current += frame.content;
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = {
                  ...last,
                  content: streamBufferRef.current,
                };
              }
              return updated;
            });
            break;

          case 'done':
            if (frame.scope_refusal) {
              setScopeRefusal(frame.scope_refusal);
            }
            if (frame.provenance?.length) {
              setProvenance(frame.provenance);
            }
            // Finalise assistant message
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = {
                  ...last,
                  content: frame.content || streamBufferRef.current,
                };
              }
              return updated;
            });
            setStreaming(false);
            ws.close();
            break;

          case 'error':
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: `Error: ${frame.message}`,
              },
            ]);
            setStreaming(false);
            ws.close();
            break;
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      setConnectionError('Unable to connect to chat service. Please try again.');
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === 'assistant' && last.content === '') {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content: 'Connection error: unable to reach chat backend.',
          };
          return updated;
        }
        return [
          ...prev,
          {
            role: 'assistant',
            content: 'Connection error: unable to reach chat backend.',
          },
        ];
      });
      setStreaming(false);
    };

    ws.onclose = () => {
      setStreaming(false);
      wsRef.current = null;
    };
  }, [input, streaming, filters, sessionId, status]);

  const handleCancel = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'cancel' }));
    }
    setStreaming(false);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
    if (e.key === 'Escape' && streaming) {
      handleCancel();
    }
  };

  const handleSuggestionClick = (suggestion: { action: string; value: string }) => {
    if (!onFilterUpdate) return;
    switch (suggestion.action) {
      case 'add_institution':
        onFilterUpdate({
          institutions: [...(filters.institutions || []), suggestion.value],
        });
        break;
      case 'add_vendor':
        onFilterUpdate({
          vendors: [...(filters.vendors || []), suggestion.value],
        });
        break;
      case 'set_date_from':
        onFilterUpdate({ date_from: suggestion.value });
        break;
      case 'set_date_to':
        onFilterUpdate({ date_to: suggestion.value });
        break;
    }
    setScopeRefusal(null);
  };

  const isDegraded = status?.degraded ?? true;
  const unreadCount = expanded ? 0 : messages.filter((m) => m.role === 'assistant').length;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[calc(100vw-2rem)] max-w-[420px]" data-testid="chat-popup-root">
      {!expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="ml-auto flex items-center gap-2 rounded-full bg-gradient-to-br from-primary-600 to-primary-700 text-white px-4 py-3 shadow-xl shadow-primary-700/25 hover:shadow-primary-700/35 transition-shadow"
          aria-expanded={expanded}
          aria-label="Open chat panel"
          data-testid="chat-launcher"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" /></svg>
          <span className="text-sm font-semibold">GovLens Chat</span>
          {unreadCount > 0 && (
            <span className="inline-flex items-center justify-center min-w-5 h-5 rounded-full bg-white/20 px-1.5 text-xs font-bold">
              {unreadCount}
            </span>
          )}
        </button>
      )}

      {expanded && (
        <div className="flex flex-col rounded-2xl border border-slate-200/70 bg-white/95 backdrop-blur-xl shadow-2xl overflow-hidden" style={{ height: 'min(75vh, 560px)' }}>
          {/* Header */}
          <div className="px-4 py-3 text-left text-sm font-medium text-slate-700 bg-slate-50/90 border-b border-slate-200/70 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4 text-primary-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" /></svg>
              GovLens Chat
            </span>
            <button
              onClick={() => setExpanded(false)}
              className="btn-ghost p-1.5"
              aria-label="Minimize chat panel"
              data-testid="chat-minimize"
            >
              <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" /></svg>
            </button>
          </div>

          {/* Degraded banner */}
          {isDegraded && (
            <div
              className="bg-amber-50/80 border-b border-amber-200/60 px-4 py-2 text-sm text-amber-800 flex items-center gap-2"
              role="alert"
              data-testid="degraded-banner"
            >
              Demo mode — no LLM API key configured. Responses are generated by MockLLMClient.
            </div>
          )}

          {connectionError && (
            <div className="bg-red-50 border-b border-red-200/70 px-4 py-2 text-sm text-red-700" role="alert" data-testid="chat-connection-error">
              {connectionError}
            </div>
          )}

          {/* Message list */}
          <div
            className="flex-1 overflow-y-auto px-4 py-3 space-y-3"
            role="list"
            aria-label="Chat messages"
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                role="listitem"
                aria-label={`${msg.role} message`}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white'
                      : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  {msg.content}
                  {msg.role === 'assistant' && streaming && i === messages.length - 1 && (
                    <span className="inline-block w-2 h-4 bg-primary-400 animate-pulse ml-1 rounded-sm" />
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Scope refusal suggestions */}
          {scopeRefusal && (
            <div
              className="px-4 py-2.5 bg-orange-50/80 border-t border-orange-200/60"
              data-testid="scope-suggestions"
            >
              <p className="text-sm text-orange-700 mb-1.5 font-medium">
                Out of scope. Try:
              </p>
              <div className="flex flex-wrap gap-2">
                {scopeRefusal.suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestionClick(s)}
                    className="text-xs bg-orange-100/80 hover:bg-orange-200/80 text-orange-800 px-2.5 py-1 rounded-lg font-medium transition-colors"
                    data-testid="scope-suggestion-btn"
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Provenance / sources panel */}
          {provenance.length > 0 && (
            <div className="px-4 py-1.5 border-t border-slate-100">
              <button
                onClick={() => setShowSources(!showSources)}
                className="text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
                data-testid="show-sources-btn"
              >
                {showSources ? 'Hide Sources' : 'Show Sources'} ({provenance.length})
              </button>
              {showSources && (
                <ul className="mt-1.5 space-y-1 text-xs text-slate-600" data-testid="sources-list">
                  {provenance.map((p, i) => (
                    <li key={i}>
                      <span className="font-medium">{p.title}</span>
                      {p.excerpt && (
                        <span className="text-slate-400 ml-1">— {p.excerpt}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Input area */}
          <div className="px-4 py-2.5 border-t border-slate-200/60 flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={streaming}
              className="form-input flex-1 text-sm disabled:bg-slate-100 disabled:cursor-not-allowed"
              aria-label="Chat input"
            />
            {streaming ? (
              <button
                onClick={handleCancel}
                className="px-3.5 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 font-medium transition-colors shadow-sm"
                aria-label="Stop generation"
                data-testid="cancel-btn"
              >
                Stop
              </button>
            ) : (
              <button
                onClick={sendMessage}
                disabled={!input.trim() || streaming}
                className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="send-btn"
              >
                Send
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
