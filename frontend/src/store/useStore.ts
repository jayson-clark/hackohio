import { create } from 'zustand';
import { GraphData, Node, FilterOptions, ViewMode, ProcessingStatus } from '@/types';

interface AppState {
  // Graph data
  graphData: GraphData | null;
  filteredGraphData: GraphData | null;
  
  // Selected node
  selectedNode: Node | null;
  highlightedNodes: Set<string>;
  highlightedLinks: Set<string>;
  
  // Filters
  filterOptions: FilterOptions;
  
  // View settings
  viewMode: ViewMode;
  
  // Processing
  processingStatus: ProcessingStatus | null;
  isProcessing: boolean;
  
  // UI state
  sidebarOpen: boolean;
  analyticsOpen: boolean;
  
  // Actions
  setGraphData: (data: GraphData | null) => void;
  setFilteredGraphData: (data: GraphData | null) => void;
  setSelectedNode: (node: Node | null) => void;
  setHighlightedNodes: (nodes: Set<string>) => void;
  setHighlightedLinks: (links: Set<string>) => void;
  setFilterOptions: (options: Partial<FilterOptions>) => void;
  setViewMode: (mode: Partial<ViewMode>) => void;
  setProcessingStatus: (status: ProcessingStatus | null) => void;
  setIsProcessing: (processing: boolean) => void;
  toggleSidebar: () => void;
  toggleAnalytics: () => void;
  reset: () => void;
}

const initialFilterOptions: FilterOptions = {
  minDegree: 1,
  entityTypes: [],
  topN: undefined,
  searchQuery: '',
};

const initialViewMode: ViewMode = {
  dimension: '2d',
  showLabels: true,
  showEdgeLabels: false,
};

export const useStore = create<AppState>((set) => ({
  // Initial state
  graphData: null,
  filteredGraphData: null,
  selectedNode: null,
  highlightedNodes: new Set(),
  highlightedLinks: new Set(),
  filterOptions: initialFilterOptions,
  viewMode: initialViewMode,
  processingStatus: null,
  isProcessing: false,
  sidebarOpen: true,
  analyticsOpen: false,

  // Actions
  setGraphData: (data) => set({ graphData: data, filteredGraphData: data }),
  
  setFilteredGraphData: (data) => set({ filteredGraphData: data }),
  
  setSelectedNode: (node) => {
    if (!node) {
      set({
        selectedNode: null,
        highlightedNodes: new Set(),
        highlightedLinks: new Set(),
      });
      return;
    }

    // Highlight selected node and its neighbors
    set((state) => {
      const highlightedNodes = new Set<string>([node.id]);
      const highlightedLinks = new Set<string>();

      // Find connected nodes and edges
      state.filteredGraphData?.edges.forEach((edge) => {
        if (edge.source === node.id || edge.target === node.id) {
          highlightedNodes.add(edge.source);
          highlightedNodes.add(edge.target);
          highlightedLinks.add(`${edge.source}-${edge.target}`);
        }
      });

      return {
        selectedNode: node,
        highlightedNodes,
        highlightedLinks,
      };
    });
  },
  
  setHighlightedNodes: (nodes) => set({ highlightedNodes: nodes }),
  
  setHighlightedLinks: (links) => set({ highlightedLinks: links }),
  
  setFilterOptions: (options) =>
    set((state) => ({
      filterOptions: { ...state.filterOptions, ...options },
    })),
  
  setViewMode: (mode) =>
    set((state) => ({
      viewMode: { ...state.viewMode, ...mode },
    })),
  
  setProcessingStatus: (status) => set({ processingStatus: status }),
  
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  toggleAnalytics: () => set((state) => ({ analyticsOpen: !state.analyticsOpen })),
  
  reset: () =>
    set({
      graphData: null,
      filteredGraphData: null,
      selectedNode: null,
      highlightedNodes: new Set(),
      highlightedLinks: new Set(),
      filterOptions: initialFilterOptions,
      processingStatus: null,
      isProcessing: false,
    }),
}));

