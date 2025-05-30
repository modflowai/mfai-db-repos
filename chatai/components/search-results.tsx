'use client';

interface SearchResult {
  filename: string;
  repo_name: string;
  filepath: string;
  snippet: string;
  relevanceScore?: number;
  relevanceReasoning?: string;
}

interface SearchResultsData {
  query: string;
  success: boolean;
  finalAnswer: string;
  workflowId: string;
  totalTime: number;
  toolsExecuted: string[];
  degradedMode: boolean;
  timestamp: string;
  answer: string;
  metadata: {
    executionTime: number;
    confidence: number;
    searchStrategy: string;
  };
  searchResults?: SearchResult[];
}

const SAMPLE: SearchResultsData = {
  query: "maxcompdim in pest",
  success: true,
  finalAnswer: "MAXCOMPDIM is a PEST parameter that controls the maximum number of components in dimensional analysis...",
  workflowId: "search-123",
  totalTime: 5000,
  toolsExecuted: ["RelevanceChecker", "QueryAnalyzer", "ContextValidator", "RepositorySearcher", "ResponseGenerator"],
  degradedMode: false,
  timestamp: new Date().toISOString(),
  answer: "MAXCOMPDIM is a PEST parameter...",
  metadata: {
    executionTime: 5000,
    confidence: 0.9,
    searchStrategy: "modular_workflow"
  }
};

export function SearchResults({
  searchData = SAMPLE,
}: {
  searchData?: SearchResultsData;
}) {
  const { query, success, finalAnswer, toolsExecuted, totalTime, metadata } = searchData;

  return (
    <div className="flex flex-col gap-4 rounded-2xl p-4 bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 max-w-4xl">
      {/* Header */}
      <div className="flex flex-row justify-between items-center">
        <div className="flex flex-row gap-2 items-center">
          <div className="size-10 rounded-full bg-green-500 flex items-center justify-center">
            <span className="text-white font-semibold text-lg">🔍</span>
          </div>
          <div>
            <div className="text-xl font-semibold text-gray-800">
              MODFLOW Search Results
            </div>
            <div className="text-sm text-gray-600">
              Query: "{query}"
            </div>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-1">
          <div className={`text-xs px-2 py-1 rounded-full ${
            success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {success ? '✅ Success' : '❌ Failed'}
          </div>
          <div className="text-xs text-gray-500">
            {(totalTime / 1000).toFixed(1)}s • {Math.round(metadata.confidence * 100)}% confident
          </div>
        </div>
      </div>

      {/* Workflow Progress */}
      <div className="bg-white rounded-xl p-3 border border-gray-200">
        <div className="text-sm font-medium text-gray-700 mb-2">Modular Workflow Execution</div>
        <div className="flex flex-wrap gap-2">
          {toolsExecuted.map((tool, index) => (
            <div key={tool} className="flex items-center gap-1">
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                {index + 1}. {tool}
              </span>
              {index < toolsExecuted.length - 1 && (
                <span className="text-gray-400">→</span>
              )}
            </div>
          ))}
        </div>
        <div className="text-xs text-gray-500 mt-2">
          Strategy: {metadata.searchStrategy} • Execution time: {(metadata.executionTime / 1000).toFixed(1)}s
        </div>
      </div>

      {/* Answer */}
      {finalAnswer && (
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <div className="text-sm font-medium text-gray-700 mb-2">📝 Answer</div>
          <div className="text-gray-800 leading-relaxed">
            {finalAnswer}
          </div>
        </div>
      )}

      {/* Search Results (if available) */}
      {searchData.searchResults && searchData.searchResults.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-gray-200">
          <div className="text-sm font-medium text-gray-700 mb-3">
            📄 Found {searchData.searchResults.length} relevant documents
          </div>
          <div className="flex flex-col gap-3">
            {searchData.searchResults.map((result, index) => (
              <div key={index} className="bg-gray-50 rounded-lg p-3 border-l-4 border-green-400">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex flex-col">
                    <div className="font-medium text-gray-800">{result.filename}</div>
                    <div className="text-sm text-gray-600">{result.repo_name} • {result.filepath}</div>
                  </div>
                  {result.relevanceScore && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                      {Math.round(result.relevanceScore * 100)}% relevant
                    </span>
                  )}
                </div>
                
                <div className="text-sm text-gray-700 mb-2">
                  {result.snippet}
                </div>
                
                {result.relevanceReasoning && (
                  <div className="text-xs text-gray-600 bg-yellow-50 p-2 rounded border-l-2 border-yellow-300">
                    <strong>Why relevant:</strong> {result.relevanceReasoning}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-200">
        Search completed at {new Date(searchData.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}