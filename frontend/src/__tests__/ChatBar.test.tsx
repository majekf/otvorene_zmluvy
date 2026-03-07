/**
 * Tests for ChatBar component (Phase 5)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ChatBar from '../components/ChatBar';

// Mock the API module
vi.mock('../api', () => ({
  fetchChatStatus: vi.fn(),
  chatWebSocketUrl: vi.fn(() => 'ws://localhost/api/chat'),
  saveChat: vi.fn(),
}));

import { fetchChatStatus } from '../api';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  readyState = 1; // OPEN
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    // Auto-trigger onopen on next tick
    setTimeout(() => this.onopen?.(), 0);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  }

  // Test helper: simulate receiving a frame
  _receive(frame: object) {
    this.onmessage?.({ data: JSON.stringify(frame) });
  }

  static OPEN = 1;
  static CLOSED = 3;
}

function renderChatBar(props = {}) {
  return render(
    <MemoryRouter>
      <ChatBar
        filters={{}}
        onFilterUpdate={vi.fn()}
        contractCount={10}
        {...props}
      />
    </MemoryRouter>,
  );
}

async function openChatPanel() {
  const launcher = await screen.findByTestId('chat-launcher');
  fireEvent.click(launcher);
}

describe('ChatBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    // @ts-ignore
    globalThis.WebSocket = MockWebSocket as any;
    // Mock crypto.randomUUID
    vi.spyOn(crypto, 'randomUUID').mockReturnValue('test-session-id' as `${string}-${string}-${string}-${string}-${string}`);
  });

  it('renders toggle button', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'mock',
      degraded: true,
      features: [],
    });

    renderChatBar();
    await openChatPanel();
    expect(screen.getByText(/GovLens Chat/)).toBeInTheDocument();
  });

  it('shows degraded banner when status is degraded', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'mock',
      degraded: true,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    await waitFor(() => {
      expect(screen.getByTestId('degraded-banner')).toBeInTheDocument();
    });
  });

  it('does not show degraded banner when status is ok', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: ['streaming'],
    });

    renderChatBar();
    await openChatPanel();

    await waitFor(() => {
      expect(screen.queryByTestId('degraded-banner')).not.toBeInTheDocument();
    });
  });

  it('sends message via WebSocket when form submitted', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'What are top vendors?' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    // Wait for onopen to fire
    await waitFor(() => {
      const ws = MockWebSocket.instances[0];
      expect(ws.sentMessages.length).toBe(1);
      const sent = JSON.parse(ws.sentMessages[0]);
      expect(sent.message).toBe('What are top vendors?');
    });
  });

  it('displays token frames as streaming text', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];

    // Simulate server frames
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });
    ws._receive({ type: 'token', content: 'Hello ' });
    ws._receive({ type: 'token', content: 'World' });
    ws._receive({ type: 'done', content: 'Hello World', cancelled: false, provenance: [], scope_refusal: null, usage: null });

    await waitFor(() => {
      expect(screen.getByText('Hello World')).toBeInTheDocument();
    });
  });

  it('shows cancel button during streaming', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      const ws = MockWebSocket.instances[0];
      ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });
    });

    await waitFor(() => {
      expect(screen.getByTestId('cancel-btn')).toBeInTheDocument();
    });
  });

  it('cancel button sends cancel frame', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });

    await waitFor(() => {
      expect(screen.getByTestId('cancel-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('cancel-btn'));

    const cancelSent = ws.sentMessages.find(m => {
      try { return JSON.parse(m).type === 'cancel'; } catch { return false; }
    });
    expect(cancelSent).toBeDefined();
  });

  it('placeholder reflects active filters', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar({
      filters: { institutions: ['Mesto Bratislava'], categories: ['IT'] },
      contractCount: 42,
    });
    await openChatPanel();

    await waitFor(() => {
      const input = screen.getByLabelText('Chat input');
      expect((input as HTMLInputElement).placeholder).toContain('Mesto Bratislava');
      expect((input as HTMLInputElement).placeholder).toContain('42 contracts');
    });
  });

  it('shows scope refusal suggestions', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });
    ws._receive({
      type: 'done',
      content: 'Out of scope',
      cancelled: false,
      provenance: [],
      scope_refusal: {
        reason: 'Institution not in scope',
        suggestions: [{ label: 'Add Mesto Košice', action: 'add_institution', value: 'Mesto Košice' }],
        hint_endpoint: '/api/institutions',
      },
      usage: null,
    });

    await waitFor(() => {
      expect(screen.getByTestId('scope-suggestions')).toBeInTheDocument();
      expect(screen.getByText('Add Mesto Košice')).toBeInTheDocument();
    });
  });

  it('clicking suggestion calls onFilterUpdate', async () => {
    const onFilterUpdate = vi.fn();
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar({ onFilterUpdate });
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });
    ws._receive({
      type: 'done',
      content: 'Out of scope',
      cancelled: false,
      provenance: [],
      scope_refusal: {
        reason: 'Out of scope',
        suggestions: [{ label: 'Add Košice', action: 'add_institution', value: 'Mesto Košice' }],
        hint_endpoint: '',
      },
      usage: null,
    });

    await waitFor(() => {
      expect(screen.getByTestId('scope-suggestion-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('scope-suggestion-btn'));
    expect(onFilterUpdate).toHaveBeenCalledWith({
      institutions: ['Mesto Košice'],
    });
  });

  it('sources panel hidden by default', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });
    ws._receive({
      type: 'done',
      content: 'Answer',
      cancelled: false,
      provenance: [{ id: 'c1', title: 'Contract 1', excerpt: 'url' }],
      scope_refusal: null,
      usage: null,
    });

    await waitFor(() => {
      expect(screen.getByTestId('show-sources-btn')).toBeInTheDocument();
    });

    // Sources list should NOT be visible yet
    expect(screen.queryByTestId('sources-list')).not.toBeInTheDocument();
  });

  it('sources panel expands on click', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });
    ws._receive({
      type: 'done',
      content: 'Answer',
      cancelled: false,
      provenance: [{ id: 'c1', title: 'Contract 1', excerpt: 'url' }],
      scope_refusal: null,
      usage: null,
    });

    await waitFor(() => {
      expect(screen.getByTestId('show-sources-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('show-sources-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('sources-list')).toBeInTheDocument();
      expect(screen.getByText('Contract 1')).toBeInTheDocument();
    });
  });

  it('Enter key sends message', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });
  });

  it('Escape key cancels streaming', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });

    await waitFor(() => {
      expect(screen.getByTestId('cancel-btn')).toBeInTheDocument();
    });

    fireEvent.keyDown(input, { key: 'Escape' });

    const cancelSent = ws.sentMessages.find(m => {
      try { return JSON.parse(m).type === 'cancel'; } catch { return false; }
    });
    expect(cancelSent).toBeDefined();
  });

  it('message list items have ARIA roles', async () => {
    (fetchChatStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      provider: 'openai',
      degraded: false,
      features: [],
    });

    renderChatBar();
    await openChatPanel();

    const input = screen.getByLabelText('Chat input');
    fireEvent.change(input, { target: { value: 'Hi' } });
    fireEvent.click(screen.getByTestId('send-btn'));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const ws = MockWebSocket.instances[0];
    ws._receive({ type: 'start', session_id: 'test', degraded: false, provider: 'mock' });
    ws._receive({ type: 'done', content: 'Response', cancelled: false, provenance: [], scope_refusal: null, usage: null });

    await waitFor(() => {
      const listItems = screen.getAllByRole('listitem');
      expect(listItems.length).toBeGreaterThanOrEqual(2);
    });
  });
});
