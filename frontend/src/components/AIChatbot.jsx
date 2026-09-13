import { useEffect, useRef, useState } from 'react';
import {
  Bot,
  Sparkles,
  Send,
  X,
  Trash2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Download,
  Lightbulb,
} from 'lucide-react';
import { getAIChatTopics, sendAIChat } from '../api';

export default function AIChatbot({
  mode = 'widget', // 'widget' | 'fullscreen'
  initialContext = null,
  onClose = null,
}) {
  const [isOpen, setIsOpen] = useState(mode === 'fullscreen');
  const [isMinimized, setIsMinimized] = useState(false);
  const [categories, setCategories] = useState([]);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `👋 **Hi there! I'm BugFlow AI Mentor.**\n\nI'm here to help you with anything related to **reporting, debugging, and solving software bugs** — with step-by-step guidance!\n\n💡 *Ask me any question below to get started:*`,
      category: 'Welcome',
      suggested_followups: [
        'How do I write my first bug report?',
        'What is the difference between Severity and Priority?',
        'How to troubleshoot a 500 Internal Server Error?',
        'Can you review my draft bug description?',
      ],
      helpful_tips: [
        'Ask about QA terminology, bug reproduction, or code error messages anytime.',
        'You can paste draft bug text or error logs directly into this chat for instant feedback.',
      ],
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useState(initialContext);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    loadStarterTopics();
  }, []);

  useEffect(() => {
    if (initialContext) {
      setContext(initialContext);
    }
  }, [initialContext]);

  useEffect(() => {
    if (isOpen && !isMinimized) {
      scrollToBottom();
    }
  }, [messages, isOpen, isMinimized]);

  function scrollToBottom() {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  }

  async function loadStarterTopics() {
    try {
      const data = await getAIChatTopics();
      if (data?.categories) {
        setCategories(data.categories);
      }
    } catch {
      // ignore
    }
  }

  async function handleSendMessage(customText = null, customMode = 'general_mentor', customContext = null) {
    const textToSend = (customText !== null ? customText : inputText).trim();
    if (!textToSend || loading) return;

    const userMessage = {
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString(),
    };

    const newHistory = [...messages, userMessage];
    setMessages(newHistory);
    setInputText('');
    setLoading(true);

    try {
      const payload = {
        messages: newHistory.map((m) => ({ role: m.role, content: m.content })),
        mode: customMode,
        context: customContext || context,
      };

      const res = await sendAIChat(payload);
      setMessages([
        ...newHistory,
        {
          role: 'assistant',
          content: res.reply || 'I processed your request.',
          category: res.category,
          suggested_followups: res.suggested_followups || [],
          helpful_tips: res.helpful_tips || [],
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setMessages([
        ...newHistory,
        {
          role: 'assistant',
          content: `⚠️ **Error connecting to AI Mentor**: ${err.message || 'Please try again in a moment.'}`,
          category: 'Error',
          suggested_followups: ['How to report a bug?', 'Severity vs Priority?'],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleClearChat() {
    setMessages([
      {
        role: 'assistant',
        content: `Conversation reset! ✨ How can I help you today?`,
        suggested_followups: [
          'How do I write my first bug report?',
          'What is the difference between Severity and Priority?',
          'Step-by-step troubleshooting checklist',
          'Explain 500 Internal Server Error',
        ],
      },
    ]);
  }

  function handleExportChat() {
    const chatExport = messages
      .map((m) => `[${m.role.toUpperCase()}]:\n${m.content}\n`)
      .join('\n----------------------------------------\n\n');
    const blob = new Blob([chatExport], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `BugFlow_AI_Mentor_Chat_${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function copyToClipboard(text, index) {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  }

  // Markdown Formatter Component
  function MarkdownContent({ content }) {
    if (!content) return null;

    const parts = content.split(/(```[\s\S]*?```)/g);

    return (
      <div className="chat-markdown-body">
        {parts.map((part, pIdx) => {
          if (part.startsWith('```') && part.endsWith('```')) {
            const firstLineBreak = part.indexOf('\n');
            const lang = part.slice(3, firstLineBreak).trim() || 'code';
            const codeBody = part.slice(firstLineBreak + 1, -3);
            return (
              <div key={pIdx} className="chat-code-block">
                <div className="chat-code-header">
                  <span className="chat-code-lang">{lang}</span>
                  <button
                    className="chat-code-copy-btn"
                    onClick={() => copyToClipboard(codeBody, `code-${pIdx}`)}
                    title="Copy Code"
                  >
                    {copiedIndex === `code-${pIdx}` ? (
                      <>
                        <Check size={12} color="#10b981" /> Copied!
                      </>
                    ) : (
                      <>
                        <Copy size={12} /> Copy
                      </>
                    )}
                  </button>
                </div>
                <pre className="chat-code-pre">
                  <code>{codeBody}</code>
                </pre>
              </div>
            );
          }

          const lines = part.split('\n');
          return (
            <div key={pIdx}>
              {lines.map((line, lIdx) => {
                const trimmed = line.trim();
                if (!trimmed) return <div key={lIdx} style={{ height: '0.4rem' }} />;

                // Headers
                if (trimmed.startsWith('### ')) {
                  return (
                    <h4 key={lIdx} className="chat-md-h4">
                      {parseInline(trimmed.slice(4))}
                    </h4>
                  );
                }
                if (trimmed.startsWith('#### ')) {
                  return (
                    <h5 key={lIdx} className="chat-md-h5">
                      {parseInline(trimmed.slice(5))}
                    </h5>
                  );
                }
                if (trimmed === '---') {
                  return <hr key={lIdx} className="chat-md-hr" />;
                }

                // Table rows
                if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
                  const cells = trimmed
                    .split('|')
                    .slice(1, -1)
                    .map((c) => c.trim());
                  if (cells.every((c) => c.startsWith('---') || c.startsWith(':---'))) {
                    return null;
                  }
                  return (
                    <div key={lIdx} className="chat-md-table-row">
                      {cells.map((cell, cIdx) => (
                        <div key={cIdx} className="chat-md-table-cell">
                          {parseInline(cell)}
                        </div>
                      ))}
                    </div>
                  );
                }

                // Bullet points
                if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                  return (
                    <div key={lIdx} className="chat-md-bullet">
                      <span className="chat-bullet-dot">•</span>
                      <span>{parseInline(trimmed.slice(2))}</span>
                    </div>
                  );
                }

                // Numbered lists
                const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
                if (numMatch) {
                  return (
                    <div key={lIdx} className="chat-md-number">
                      <span className="chat-number-badge">{numMatch[1]}</span>
                      <span>{parseInline(numMatch[2])}</span>
                    </div>
                  );
                }

                return (
                  <p key={lIdx} className="chat-md-p">
                    {parseInline(trimmed)}
                  </p>
                );
              })}
            </div>
          );
        })}
      </div>
    );
  }

  function parseInline(text) {
    const tokens = [];
    let remaining = text;
    let key = 0;
    const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/;

    while (remaining) {
      const match = remaining.match(regex);
      if (!match) {
        tokens.push(<span key={key++}>{remaining}</span>);
        break;
      }

      const matchIndex = match.index;
      if (matchIndex > 0) {
        tokens.push(<span key={key++}>{remaining.substring(0, matchIndex)}</span>);
      }

      const matchedStr = match[0];
      if (matchedStr.startsWith('**') && matchedStr.endsWith('**')) {
        tokens.push(
          <strong key={key++} style={{ color: 'var(--text)', fontWeight: '700' }}>
            {matchedStr.slice(2, -2)}
          </strong>
        );
      } else if (matchedStr.startsWith('`') && matchedStr.endsWith('`')) {
        tokens.push(
          <code key={key++} className="chat-inline-code">
            {matchedStr.slice(1, -1)}
          </code>
        );
      } else if (matchedStr.startsWith('*') && matchedStr.endsWith('*')) {
        tokens.push(
          <em key={key++} style={{ color: 'var(--text-muted)' }}>
            {matchedStr.slice(1, -1)}
          </em>
        );
      }

      remaining = remaining.substring(matchIndex + matchedStr.length);
    }

    return tokens;
  }


  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: Floating Trigger Pill if closed (Widget Mode)
  // ─────────────────────────────────────────────────────────────────────────────
  if (mode === 'widget' && !isOpen) {
    return (
      <div className="ai-floating-trigger-container">
        <button
          className="ai-floating-trigger-btn"
          onClick={() => {
            setIsOpen(true);
            setIsMinimized(false);
          }}
          title="Open AI Mentor & Bug Assistant"
        >
          <div className="ai-trigger-icon-pulse">
            <Bot size={22} color="#ffffff" />
          </div>
          <div className="ai-trigger-label">
            <span className="ai-trigger-title">Ask AI Mentor</span>
            <span className="ai-trigger-subtitle">Bug & QA Help</span>
          </div>
          <span className="ai-trigger-badge">AI</span>
        </button>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: Main Chatbot Container (Widget or Full-Screen View)
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div
      className={`ai-chatbot-window ${
        mode === 'fullscreen' ? 'ai-chatbot-fullscreen' : 'ai-chatbot-widget'
      } ${isMinimized ? 'minimized' : ''}`}
    >
      {/* Chatbot Header */}
      <div className="ai-chat-header">
        <div className="ai-chat-header-left">
          <div className="ai-bot-avatar-glow">
            <Bot size={20} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <h3 className="ai-chat-title">BugFlow AI Mentor</h3>
              <span className="ai-chat-online-pill">
                <span className="ai-online-dot" /> Online
              </span>
            </div>
            <p className="ai-chat-subtitle">
              Interactive guidance for reporting, debugging & solving bugs
            </p>
          </div>
        </div>

        <div className="ai-chat-header-actions">
          <button
            className="ai-header-btn"
            onClick={handleExportChat}
            title="Export Conversation Transcript"
          >
            <Download size={15} />
          </button>
          <button
            className="ai-header-btn"
            onClick={handleClearChat}
            title="Clear Chat History"
          >
            <Trash2 size={15} />
          </button>
          {mode === 'widget' && (
            <button
              className="ai-header-btn"
              onClick={() => setIsMinimized(!isMinimized)}
              title={isMinimized ? 'Expand' : 'Minimize'}
            >
              {isMinimized ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
          {mode === 'widget' && (
            <button
              className="ai-header-btn"
              onClick={() => {
                setIsOpen(false);
                if (onClose) onClose();
              }}
              title="Close Assistant"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Active Context Banner (if context was passed from modal/form) */}
          {context && (
            <div className="ai-context-banner">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', minWidth: 0 }}>
                <Sparkles size={14} color="var(--accent)" />
                <span className="ai-context-label">Active Context:</span>
                <span className="ai-context-value" title={context.issue_title || context.draft_title || context.project_name}>
                  {context.issue_title || context.draft_title || context.project_name || 'Active Ticket'}
                </span>
              </div>
              <button
                className="ai-context-clear-btn"
                onClick={() => setContext(null)}
                title="Clear Active Context"
              >
                Clear
              </button>
            </div>
          )}

          {/* Chat & Mentor Body */}
          <div className="ai-chat-body">
            {/* Messages Stream */}
            <div className="ai-messages-container">
              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={idx} className={`ai-message-row ${isUser ? 'user' : 'assistant'}`}>
                    <div className={`ai-message-bubble ${isUser ? 'user' : 'assistant'}`}>
                      {/* Role Header */}
                      <div className="ai-msg-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          {isUser ? (
                            <span className="ai-msg-author">You</span>
                          ) : (
                            <>
                              <Bot size={14} color="var(--accent)" />
                              <span className="ai-msg-author">AI Mentor</span>
                              {msg.category && (
                                <span className="ai-msg-tag">{msg.category}</span>
                              )}
                            </>
                          )}
                        </div>
                        {!isUser && (
                          <button
                            className="ai-msg-copy-btn"
                            onClick={() => copyToClipboard(msg.content, idx)}
                            title="Copy Answer"
                          >
                            {copiedIndex === idx ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
                          </button>
                        )}
                      </div>

                      {/* Content */}
                      <div className="ai-msg-text">
                        <MarkdownContent content={msg.content} />
                      </div>

                      {/* Helpful Takeaway Tips */}
                      {!isUser && msg.helpful_tips && msg.helpful_tips.length > 0 && (
                        <div className="ai-tips-box">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.3rem', fontWeight: '700', fontSize: '0.75rem', color: 'var(--accent)' }}>
                            <Lightbulb size={13} /> Key Takeaways & Best Practices:
                          </div>
                          <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            {msg.helpful_tips.map((tip, tIdx) => (
                              <li key={tIdx} style={{ marginBottom: '0.15rem' }}>
                                {tip}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Suggested Follow-up Chips */}
                      {!isUser && msg.suggested_followups && msg.suggested_followups.length > 0 && (
                        <div className="ai-followups-container">
                          <span className="ai-followups-label">Suggested Follow-ups:</span>
                          <div className="ai-followups-pills">
                            {msg.suggested_followups.map((followup, fIdx) => (
                              <button
                                key={fIdx}
                                className="ai-followup-pill"
                                onClick={() => handleSendMessage(followup)}
                              >
                                {followup}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {loading && (
                <div className="ai-message-row assistant">
                  <div className="ai-message-bubble assistant loading">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div className="ai-typing-indicator">
                        <span />
                        <span />
                        <span />
                      </div>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        AI Mentor is thinking & formulating answer...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>


            {/* Input Area */}
            <div className="ai-input-wrapper">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="ai-input-form"
              >
                <textarea
                  ref={textareaRef}
                  className="ai-chat-textarea"
                  placeholder="Ask any doubt on reporting, debugging, severity, or solving bugs..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  rows={1}
                />
                <button
                  type="submit"
                  className="ai-send-btn"
                  disabled={!inputText.trim() || loading}
                  title="Send Message"
                >
                  <Send size={15} />
                </button>
              </form>
              <div className="ai-input-hint">
                Press <strong>Enter</strong> to send • <strong>Shift+Enter</strong> for newline
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
