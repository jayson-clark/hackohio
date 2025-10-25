import { useState } from 'react';
import { apiService } from '@/services/api';
import { useStore } from '@/store/useStore';

type Message = { role: 'user' | 'assistant'; content: string };

export const ChatPanel = () => {
  const { filteredGraphData, setHighlightedNodes, setHighlightedLinks } = useStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(true);

  const send = async () => {
    if (!filteredGraphData || !input.trim()) return;
    const nextHistory = [...messages, { role: 'user', content: input }];
    setMessages(nextHistory);
    setLoading(true);
    try {
      const res = await apiService.chat(input, filteredGraphData, nextHistory);
      setMessages([...nextHistory, { role: 'assistant', content: res.answer }]);

      // Highlight relevant nodes and edges
      const nodeSet = new Set<string>(res.relevant_nodes || []);
      const linkSet = new Set<string>((res.relevant_edges || []).map(([a, b]) => `${a}-${b}`));
      setHighlightedNodes(nodeSet);
      setHighlightedLinks(linkSet);
    } catch (e) {
      setMessages([...nextHistory, { role: 'assistant', content: 'Error answering. Check backend.' }]);
    } finally {
      setLoading(false);
      setInput('');
    }
  };

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed right-4 bottom-4 z-30 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-lg"
      >
        {open ? 'Hide Chat' : 'Chat'}
      </button>

      {!open ? null : (
        <div className="fixed right-0 top-0 h-full w-[360px] bg-gray-900/90 border-l border-gray-800 backdrop-blur-md z-20 flex flex-col">
      <div className="p-3 border-b border-gray-800 text-gray-200 font-semibold flex items-center justify-between">
        <span>Graph Chat</span>
        <button onClick={() => setOpen(false)} className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded border border-gray-700 text-gray-300">Minimize</button>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <div className={`inline-block px-3 py-2 rounded-lg ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-100'}`}>
              {m.content}
            </div>
          </div>
        ))}
        {messages.length === 0 && (
          <div className="text-gray-400 text-sm">
            Try: "shortest path between TP53 and cancer" or "neighbors of VEGF" or "common connections TP53, BRCA1".
          </div>
        )}
      </div>
      <div className="p-3 border-t border-gray-800 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask about the graph..."
          className="flex-1 bg-gray-800 text-gray-100 px-3 py-2 rounded outline-none border border-gray-700"
        />
        <button
          onClick={send}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-2 rounded"
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
      )}
    </>
  );
};


