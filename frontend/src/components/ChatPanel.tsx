import { useState } from 'react';
import { apiService } from '@/services/api';
import { useStore } from '@/store/useStore';

type Message = { role: 'user' | 'assistant'; content: string; isAgentic?: boolean; researchId?: string };

export const ChatPanel = () => {
  const { filteredGraphData, setHighlightedNodes, setHighlightedLinks, currentProject } = useStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(true);
  
  // Agentic AI state
  const [agentMode, setAgentMode] = useState(false);
  const [currentResearch, setCurrentResearch] = useState<any>(null);
  const [isResearching, setIsResearching] = useState(false);

  // Check if the query should trigger agentic research
  const checkIfShouldResearch = async (query: string) => {
    const researchKeywords = [
      'research', 'find papers', 'discover', 'explore', 'investigate', 'analyze',
      'what is known about', 'tell me about', 'study', 'literature', 'papers on',
      'recent developments', 'current research', 'latest findings'
    ];
    
    const queryLower = query.toLowerCase();
    const hasKeywords = researchKeywords.some(keyword => queryLower.includes(keyword));
    
    // Auto-trigger for specific patterns
    const autoTriggerPatterns = [
      /what is known about/i,
      /find papers on/i,
      /research on/i,
      /tell me about.*research/i,
      /what are the latest.*findings/i
    ];
    
    const autoTrigger = autoTriggerPatterns.some(pattern => pattern.test(query));
    
    return {
      shouldResearch: hasKeywords || autoTrigger,
      autoTrigger,
      confidence: hasKeywords ? 0.8 : 0.6
    };
  };

  // Start agentic research
  const startAgenticResearch = async (query: string, _researchInfo: any) => {
    setIsResearching(true);
    
    // Add research message
    const researchMessage = {
      role: 'assistant' as const,
      content: `🔬 I'll research "${query}" for you. This may take a few minutes...`,
      isAgentic: true
    };
    
    setMessages(prev => [...prev, researchMessage]);
    
    try {
      // Start research using the API service with proper auth
      const response = await apiService.startAgenticResearch({
        research_topic: query,
        max_papers: 10,
        search_strategy: 'comprehensive'
      });
      
      const data = response;
      setCurrentResearch(data);
      
      // Poll for results
      pollResearchStatus(data.research_id);
      
    } catch (error) {
      console.error('Failed to start research:', error);
      setMessages(prev => [...prev, {
        role: 'assistant' as const,
        content: '❌ Sorry, I couldn\'t start the research. Please try again.',
        isAgentic: true
      }]);
      setIsResearching(false);
    }
  };

  // Poll research status
  const pollResearchStatus = async (researchId: string) => {
    const poll = async () => {
      try {
        const status = await apiService.getAgenticResearchStatus(researchId);
        
        if (status.status === 'completed') {
          // Get results
          const results = await apiService.getAgenticResearchResults(researchId);
          
          // Format results for display
          const resultMessage = formatResearchResults(results);
          setMessages(prev => [...prev, {
            role: 'assistant' as const,
            content: resultMessage,
            isAgentic: true,
            researchId
          }]);
          
          setIsResearching(false);
          setCurrentResearch(null);
        } else if (status.status === 'failed') {
          setMessages(prev => [...prev, {
            role: 'assistant' as const,
            content: `❌ Research failed: ${status.error}`,
            isAgentic: true
          }]);
          setIsResearching(false);
          setCurrentResearch(null);
        } else {
          // Still processing, poll again
          setTimeout(poll, 2000);
        }
      } catch (error) {
        console.error('Failed to check research status:', error);
        setIsResearching(false);
      }
    };
    
    poll();
  };

  // Format research results for display
  const formatResearchResults = (results: any) => {
    const papers = results.papers_analyzed || 0;
    const insights = results.insights || [];
    const recommendations = results.recommendations || {};
    
    let message = `🔬 **Research Complete!**\n\n`;
    message += `📚 **Analyzed ${papers} papers**\n\n`;
    
    if (insights.length > 0) {
      message += `💡 **Key Insights:**\n`;
      insights.slice(0, 3).forEach((insight: any, i: number) => {
        message += `${i + 1}. **${insight.title}**\n`;
        message += `   ${insight.description?.substring(0, 100)}...\n\n`;
      });
    }
    
    if (recommendations.research_gaps?.length > 0) {
      message += `🎯 **Research Gaps Identified:**\n`;
      recommendations.research_gaps.slice(0, 2).forEach((gap: string, i: number) => {
        message += `${i + 1}. ${gap}\n`;
      });
      message += `\n`;
    }
    
    message += `📊 **Knowledge Graph:** ${results.knowledge_graph?.nodes?.length || 0} entities, ${results.knowledge_graph?.edges?.length || 0} relationships`;
    
    return message;
  };

  const send = async () => {
    if (!input.trim()) return;
    
    // Clear highlights from previous query
    setHighlightedNodes(new Set());
    setHighlightedLinks(new Set());
    
    const nextHistory = [...messages, { role: 'user' as const, content: input }];
    setMessages(nextHistory);
    setLoading(true);
    setInput(''); // Clear input immediately
    
    try {
      // Check if we should trigger agentic research
      const shouldResearch = await checkIfShouldResearch(input);
      
      if (shouldResearch && (agentMode || shouldResearch.autoTrigger)) {
        await startAgenticResearch(input, shouldResearch);
        return;
      }
      
      // Regular chat if we have graph data
      if (filteredGraphData) {
        const res = await apiService.chat(input, filteredGraphData, nextHistory, currentProject?.project_id);
        setMessages([...nextHistory, { role: 'assistant' as const, content: res.answer }]);

        // Highlight relevant nodes and edges
        const nodeSet = new Set<string>(res.relevant_nodes || []);
        const linkSet = new Set<string>((res.relevant_edges || []).map(([a, b]) => `${a}-${b}`));
        setHighlightedNodes(nodeSet);
        setHighlightedLinks(linkSet);
      } else {
        // No graph data available
        setMessages([...nextHistory, { 
          role: 'assistant' as const, 
          content: 'No graph data available. Please upload and process some PDFs first, or try asking me to research a topic!' 
        }]);
      }
    } catch (e) {
      setMessages([...nextHistory, { role: 'assistant' as const, content: 'Error answering. Check backend.' }]);
    } finally {
      setLoading(false);
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
        <span>Smart Chat</span>
        <div className="flex gap-2">
          {/* Agent Mode Toggle */}
          <button
            onClick={() => setAgentMode(!agentMode)}
            className={`text-xs px-2 py-1 rounded text-white ${
              agentMode 
                ? 'bg-green-600 hover:bg-green-500' 
                : 'bg-gray-600 hover:bg-gray-500'
            }`}
          >
            {agentMode ? '🤖 Agent ON' : '🤖 Agent OFF'}
          </button>
          
          {messages.length > 0 && (
            <button 
              onClick={() => {
                setMessages([]);
                setHighlightedNodes(new Set());
                setHighlightedLinks(new Set());
              }} 
              className="text-xs px-2 py-1 bg-red-600 hover:bg-red-500 rounded text-white"
            >
              Clear
            </button>
          )}
          <button onClick={() => setOpen(false)} className="text-xs px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded border border-gray-700 text-gray-300">Minimize</button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <div className={`inline-block px-3 py-2 rounded-lg ${
              m.role === 'user' 
                ? 'bg-blue-600 text-white' 
                : m.isAgentic 
                  ? 'bg-purple-800 text-purple-100 border border-purple-600' 
                  : 'bg-gray-800 text-gray-100'
            }`}>
              {m.isAgentic && (
                <div className="text-xs text-purple-300 mb-1">
                  🤖 Agentic Research
                </div>
              )}
              {m.content}
            </div>
          </div>
        ))}
        {messages.length === 0 && (
          <div className="text-gray-400 text-sm space-y-2">
            <div className="font-medium text-gray-300">Try these examples:</div>
            <div className="space-y-1">
              <div>• "shortest path between TP53 and cancer"</div>
              <div>• "neighbors of VEGF"</div>
              <div>• "common connections TP53, BRCA1"</div>
              {agentMode && (
                <>
                  <div className="text-purple-300 font-medium mt-2">Agentic Research:</div>
                  <div>• "research gut microbiome and immunotherapy"</div>
                  <div>• "find papers on cancer biomarkers"</div>
                  <div>• "what is known about CRISPR therapy"</div>
                </>
              )}
            </div>
          </div>
        )}
        
        {/* Research Status Indicator */}
        {isResearching && (
          <div className="bg-purple-900/50 border border-purple-600 rounded-lg p-3 mb-3">
            <div className="flex items-center space-x-2 text-purple-200">
              <div className="animate-spin">🔬</div>
              <span className="text-sm">Researching your topic...</span>
            </div>
            {currentResearch && (
              <div className="text-xs text-purple-300 mt-1">
                Status: {currentResearch.status}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="p-3 border-t border-gray-800 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder={
            agentMode 
              ? "Ask me to research anything..." 
              : "Ask about the graph or research topics..."
          }
          className="flex-1 bg-gray-800 text-gray-100 px-3 py-2 rounded outline-none border border-gray-700"
        />
        <button
          onClick={send}
          disabled={loading || isResearching}
          className={`px-3 py-2 rounded text-white ${
            isResearching 
              ? 'bg-purple-600 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-500'
          } disabled:opacity-50`}
        >
          {isResearching ? '🔬' : loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
      )}
    </>
  );
};


