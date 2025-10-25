import { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { useStore } from './store/useStore';
import { ForceGraph2DView } from './components/ForceGraph2DView';
import { ForceGraph3DView } from './components/ForceGraph3DView';
import { UploadPanel } from './components/UploadPanel';
import { ProcessingOverlay } from './components/ProcessingOverlay';
import { Sidebar } from './components/Sidebar';
import { NodeDetails } from './components/NodeDetails';
import { Analytics } from './components/Analytics';
import { ExportMenu } from './components/ExportMenu';

function App() {
  const { graphData, filteredGraphData, viewMode, filterOptions, setFilteredGraphData } = useStore();

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
      filtered.edges = filtered.edges.filter(
        (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)
      );
    }

    // Filter by minimum degree
    if (filterOptions.minDegree > 1) {
      const degrees = new Map<string, number>();
      filtered.edges.forEach((edge) => {
        degrees.set(edge.source, (degrees.get(edge.source) || 0) + 1);
        degrees.set(edge.target, (degrees.get(edge.target) || 0) + 1);
      });

      filtered.nodes = filtered.nodes.filter(
        (node) => (degrees.get(node.id) || 0) >= filterOptions.minDegree
      );
      const nodeIds = new Set(filtered.nodes.map((n) => n.id));
      filtered.edges = filtered.edges.filter(
        (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)
      );
    }

    // Filter by search query
    if (filterOptions.searchQuery) {
      const query = filterOptions.searchQuery.toLowerCase();
      filtered.nodes = filtered.nodes.filter((node) =>
        node.id.toLowerCase().includes(query)
      );
      const nodeIds = new Set(filtered.nodes.map((n) => n.id));
      filtered.edges = filtered.edges.filter(
        (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)
      );
    }

    console.log('App: Filtered result', {
      filteredNodes: filtered.nodes.length,
      filteredEdges: filtered.edges.length
    });

    setFilteredGraphData(filtered);
  }, [graphData, filterOptions, setFilteredGraphData]);

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

      {!graphData ? (
        <div className="w-full h-full flex items-center justify-center p-4">
          <UploadPanel />
        </div>
      ) : (
        <>
          {/* Debug info */}
          <div className="fixed top-4 right-4 bg-black/80 text-white p-4 rounded-lg text-xs z-50">
            <div>Nodes: {graphData?.nodes?.length || 0}</div>
            <div>Edges: {graphData?.edges?.length || 0}</div>
            <div>Filtered Nodes: {filteredGraphData?.nodes?.length || 0}</div>
            <div>Filtered Edges: {filteredGraphData?.edges?.length || 0}</div>
          </div>
          
          <Sidebar />
          <NodeDetails />
          <Analytics />
          <ExportMenu />
          
          <div className="w-full h-full">
            {viewMode.dimension === '2d' ? (
              <ForceGraph2DView />
            ) : (
              <ForceGraph3DView />
            )}
          </div>
        </>
      )}

      <ProcessingOverlay />
    </div>
  );
}

export default App;

