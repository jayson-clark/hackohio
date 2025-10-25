import { useState } from 'react';
import {
  Search,
  Filter,
  Settings,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Box,
  BoxSelect,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { ENTITY_COLORS, ENTITY_LABELS, EntityType } from '@/types';

export function Sidebar() {
  const {
    sidebarOpen,
    toggleSidebar,
    filterOptions,
    setFilterOptions,
    viewMode,
    setViewMode,
    filteredGraphData,
    graphData,
    toggleAnalytics,
  } = useStore();

  const [searchQuery, setSearchQuery] = useState('');

  const entityTypes = Object.keys(ENTITY_COLORS) as EntityType[];

  const handleEntityTypeToggle = (type: EntityType) => {
    const current = filterOptions.entityTypes;
    const updated = current.includes(type)
      ? current.filter((t) => t !== type)
      : [...current, type];
    setFilterOptions({ entityTypes: updated });
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setFilterOptions({ searchQuery: query });
  };

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={toggleSidebar}
        className="fixed left-4 top-4 z-30 p-2 bg-gray-900/90 backdrop-blur-sm text-white rounded-lg hover:bg-gray-800 transition-all border border-gray-700"
      >
        {sidebarOpen ? (
          <ChevronLeft className="w-5 h-5" />
        ) : (
          <ChevronRight className="w-5 h-5" />
        )}
      </button>

      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 h-full bg-gradient-to-b from-gray-900 to-gray-800 border-r border-gray-700 transition-transform duration-300 z-20 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } w-80 overflow-y-auto`}
      >
        <div className="p-6 pt-20">
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-white mb-1">
              Synapse Mapper
            </h2>
            <p className="text-sm text-gray-400">
              {filteredGraphData
                ? `${filteredGraphData.nodes.length} nodes, ${filteredGraphData.edges.length} edges`
                : 'No data loaded'}
            </p>
          </div>

          {/* Search */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              <Search className="w-4 h-4 inline mr-2" />
              Search Entities
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search by name..."
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* View Mode */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              <Settings className="w-4 h-4 inline mr-2" />
              View Settings
            </label>
            
            {/* 2D/3D Toggle */}
            <div className="flex space-x-2 mb-3">
              <button
                onClick={() => setViewMode({ dimension: '2d' })}
                className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${
                  viewMode.dimension === '2d'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <Box className="w-4 h-4 inline mr-2" />
                2D
              </button>
              <button
                onClick={() => setViewMode({ dimension: '3d' })}
                className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${
                  viewMode.dimension === '3d'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                <BoxSelect className="w-4 h-4 inline mr-2" />
                3D
              </button>
            </div>

            {/* Show Labels */}
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={viewMode.showLabels}
                onChange={(e) => setViewMode({ showLabels: e.target.checked })}
                className="w-4 h-4 text-primary-600 bg-gray-800 border-gray-600 rounded focus:ring-primary-500"
              />
              <span className="text-sm text-gray-300">Show node labels</span>
            </label>
          </div>

          {/* Filters */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-3">
              <Filter className="w-4 h-4 inline mr-2" />
              Filter by Entity Type
            </label>
            <div className="space-y-2">
              {entityTypes.map((type) => (
                <label
                  key={type}
                  className="flex items-center space-x-3 cursor-pointer p-2 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={
                      filterOptions.entityTypes.length === 0 ||
                      filterOptions.entityTypes.includes(type)
                    }
                    onChange={() => handleEntityTypeToggle(type)}
                    className="w-4 h-4 rounded border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: ENTITY_COLORS[type] }}
                  />
                  <span className="text-sm text-gray-300 flex-1">
                    {ENTITY_LABELS[type]}
                  </span>
                  <span className="text-xs text-gray-500">
                    {graphData?.nodes.filter((n) => n.group === type).length || 0}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Min Degree Filter */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Minimum Connections: {filterOptions.minDegree}
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={filterOptions.minDegree}
              onChange={(e) =>
                setFilterOptions({ minDegree: parseInt(e.target.value) })
              }
              className="w-full"
            />
          </div>

          {/* Analytics Button */}
          <button
            onClick={toggleAnalytics}
            className="w-full py-3 px-4 bg-gradient-to-r from-primary-600 to-primary-500 text-white font-semibold rounded-lg hover:from-primary-700 hover:to-primary-600 transition-all flex items-center justify-center space-x-2"
          >
            <BarChart3 className="w-5 h-5" />
            <span>View Analytics</span>
          </button>
        </div>
      </div>
    </>
  );
}

