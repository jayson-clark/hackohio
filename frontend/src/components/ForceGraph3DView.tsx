import { useRef, useEffect, useCallback } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { useStore } from '@/store/useStore';
import { ENTITY_COLORS, Node as GraphNode } from '@/types';

export function ForceGraph3DView() {
  const graphRef = useRef<any>();
  
  const {
    filteredGraphData,
    highlightedNodes,
    highlightedLinks,
    setSelectedNode,
  } = useStore();

  useEffect(() => {
    if (graphRef.current && filteredGraphData) {
      // Camera auto-rotate
      graphRef.current.cameraPosition({ z: 1000 });
    }
  }, [filteredGraphData]);

  const handleNodeClick = useCallback(
    (node: any) => {
      setSelectedNode(node as GraphNode);
      
      // Look at node
      if (graphRef.current) {
        const distance = 200;
        graphRef.current.cameraPosition(
          { x: node.x, y: node.y, z: node.z + distance },
          node,
          1000
        );
      }
    },
    [setSelectedNode]
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, [setSelectedNode]);

  if (!filteredGraphData) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🧬</div>
          <h2 className="text-2xl font-bold text-white mb-2">
            No Graph Data
          </h2>
          <p className="text-gray-400">
            Upload PDFs to generate a knowledge graph
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full graph-container">
      <ForceGraph3D
        ref={graphRef}
        graphData={{
          nodes: filteredGraphData.nodes,
          links: filteredGraphData.edges
        }}
        nodeId="id"
        nodeLabel={(node: any) => {
          const n = node as GraphNode;
          return `${n.id} (${n.group}) - ${n.value} connections`;
        }}
        nodeColor={(node: any) => {
          const n = node as GraphNode;
          if (highlightedNodes.size > 0) {
            return highlightedNodes.has(n.id)
              ? ENTITY_COLORS[n.group]
              : 'rgba(100, 100, 100, 0.3)';
          }
          return ENTITY_COLORS[n.group];
        }}
        nodeRelSize={6}
        nodeVal={(node: any) => {
          const n = node as GraphNode;
          return n.value || 1;
        }}
        linkColor={(link: any) => {
          const linkId = `${(link.source as any).id || link.source}-${(link.target as any).id || link.target}`;
          if (highlightedLinks.size > 0) {
            return highlightedLinks.has(linkId)
              ? 'rgba(255, 255, 255, 0.8)'
              : 'rgba(100, 100, 100, 0.15)';
          }
          return 'rgba(255, 255, 255, 0.3)';
        }}
        linkWidth={(link: any) => {
          const linkId = `${(link.source as any).id || link.source}-${(link.target as any).id || link.target}`;
          if (highlightedLinks.has(linkId)) {
            return 2;
          }
          return 1;
        }}
        onNodeClick={handleNodeClick}
        onBackgroundClick={handleBackgroundClick}
        enableNodeDrag={true}
        enableNavigationControls={true}
        showNavInfo={false}
        backgroundColor="rgba(10, 10, 10, 0)"
      />
    </div>
  );
}

