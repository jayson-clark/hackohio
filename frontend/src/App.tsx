import { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { useStore } from './store/useStore';
import { useAuth, AuthProvider } from './contexts/AuthContext';
import { ForceGraph2DView } from './components/ForceGraph2DView';
import { ForceGraph3DView } from './components/ForceGraph3DView';
import { UploadPanel } from './components/UploadPanel';
import { ProcessingOverlay } from './components/ProcessingOverlay';
import { Sidebar } from './components/Sidebar';
import { ChatPanel } from './components/ChatPanel';
import { NodeDetails } from './components/NodeDetails';
import { LoginComponent } from './components/LoginComponent';
import { UserProfile } from './components/UserProfile';

function AppContent() {
  const { graphData, viewMode, filterOptions, setFilteredGraphData } = useStore();
  const { isAuthenticated, isLoading } = useAuth();

  // Apply filters when filter options or graph data change
  useEffect(() => {
    if (!graphData) {
      console.log('App: No graphData to filter');
      return;
    }

    console.log('App: Filtering graph data', {
      originalNodes: graphData.nodes?.length,
      originalEdges: graphData.edges?.length,
      filterOptions
    });

    let filtered = { ...graphData, nodes: [...graphData.nodes], edges: [...graphData.edges] };

    // Filter by entity types
    if (filterOptions.entityTypes.length > 0) {
      filtered.nodes = filtered.nodes.filter((node) =>
        filterOptions.entityTypes.includes(node.group)
      );
      const nodeIds = new Set(filtered.nodes.map((n) => n.id));
      filtered.edges = filtered.edges.filter((edge) => {
        const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as any)?.id;
        const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as any)?.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    // Filter by minimum degree
    if (filterOptions.minDegree > 1) {
      const degrees = new Map<string, number>();
      filtered.edges.forEach((edge) => {
        const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as any)?.id;
        const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as any)?.id;
        degrees.set(sourceId, (degrees.get(sourceId) || 0) + 1);
        degrees.set(targetId, (degrees.get(targetId) || 0) + 1);
      });

      filtered.nodes = filtered.nodes.filter(
        (node) => (degrees.get(node.id) || 0) >= filterOptions.minDegree
      );
      const nodeIds = new Set(filtered.nodes.map((n) => n.id));
      filtered.edges = filtered.edges.filter((edge) => {
        const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as any)?.id;
        const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as any)?.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    // Filter by search query
    if (filterOptions.searchQuery) {
      const query = filterOptions.searchQuery.toLowerCase();
      filtered.nodes = filtered.nodes.filter((node) =>
        node.id.toLowerCase().includes(query)
      );
      const nodeIds = new Set(filtered.nodes.map((n) => n.id));
      filtered.edges = filtered.edges.filter((edge) => {
        const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as any)?.id;
        const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as any)?.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }

    console.log('App: Filtered result', {
      filteredNodes: filtered.nodes.length,
      filteredEdges: filtered.edges.length,
      sampleFilteredEdge: filtered.edges[0]
    });

    setFilteredGraphData(filtered);
  }, [graphData, filterOptions, setFilteredGraphData]);

  if (isLoading) {
    return (
      <div className="w-full h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-white text-lg">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginComponent />;
  }

  return (
    <div className="w-full h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 overflow-hidden">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1f2937',
            color: '#fff',
            border: '1px solid #374151',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />

      {/* Header with user profile */}
      <div className="absolute top-4 right-4 z-50">
        <UserProfile />
      </div>

      {!graphData ? (
        <div className="w-full h-full flex items-center justify-center p-4">
          <UploadPanel />
        </div>
      ) : (
        <>
          <Sidebar />
          <NodeDetails />
          
          <div className="w-full h-full">
            {viewMode.dimension === '2d' ? (
              <ForceGraph2DView />
            ) : (
              <ForceGraph3DView />
            )}
          </div>
          <ChatPanel />
        </>
      )}

      <ProcessingOverlay />
    </div>
  );
}

function App() {
  // Get Google OAuth client ID from environment variables
  const clientId = (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID || '';

  if (!clientId) {
    return (
      <div className="w-full h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center text-white">
          <h2 className="text-2xl font-bold mb-4">Configuration Error</h2>
          <p className="text-gray-300">
            Google OAuth client ID is not configured. Please set VITE_GOOGLE_CLIENT_ID in your environment variables.
          </p>
        </div>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;

