'use client';

interface QueryAnalysisData {
  query: string;
  strategy: string;
  repositories: string[];
  searchType: string;
  keywords: string[];
  expectedResultTypes: string[];
  success: boolean;
  timestamp: string;
}

export function QueryAnalyzer({
  analysisData,
}: {
  analysisData?: QueryAnalysisData;
}) {
  const isLoading = !analysisData;
  const { strategy, repositories, searchType, keywords, expectedResultTypes } = analysisData || {};

  return (
    <div className="p-4 rounded-xl border-2 bg-purple-50 border-purple-200">
      {/* Static header - always visible */}
      <div className="flex items-center gap-2 mb-3">
        {isLoading ? (
          <div className="animate-spin size-4 border-2 border-purple-500 border-t-transparent rounded-full"></div>
        ) : (
          <span className="text-lg">📋</span>
        )}
        <span className="font-semibold text-purple-800">Query Analysis</span>
      </div>
      
      {/* Static grid layout with dynamic content */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="font-medium text-gray-700">Strategy:</span>
          {isLoading ? (
            <div className="ml-2 inline-block w-16 h-5 bg-gray-300 animate-pulse rounded"></div>
          ) : (
            <span className="ml-2 bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs">
              {strategy}
            </span>
          )}
        </div>
        
        <div>
          <span className="font-medium text-gray-700">Type:</span>
          {isLoading ? (
            <div className="ml-2 inline-block w-20 h-4 bg-gray-300 animate-pulse rounded"></div>
          ) : (
            <span className="ml-2 text-gray-600">{searchType}</span>
          )}
        </div>
      </div>

      {/* Target repositories section - static label, dynamic content */}
      <div className="mt-2">
        <span className="text-sm font-medium text-gray-700">Target repositories: </span>
        {isLoading ? (
          <div className="inline-flex gap-1">
            <div className="w-12 h-5 bg-gray-300 animate-pulse rounded"></div>
            <div className="w-16 h-5 bg-gray-300 animate-pulse rounded"></div>
          </div>
        ) : repositories && repositories.length > 0 ? (
          repositories.map(repo => (
            <span key={repo} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded mr-1">
              {repo}
            </span>
          ))
        ) : (
          <span className="text-xs text-gray-500">all repositories</span>
        )}
      </div>
      
      {/* Keywords section - static label, dynamic content */}
      <div className="mt-2">
        <span className="text-sm font-medium text-gray-700">Keywords: </span>
        {isLoading ? (
          <div className="inline-flex gap-1">
            <div className="w-14 h-5 bg-gray-300 animate-pulse rounded"></div>
            <div className="w-18 h-5 bg-gray-300 animate-pulse rounded"></div>
            <div className="w-10 h-5 bg-gray-300 animate-pulse rounded"></div>
          </div>
        ) : keywords && keywords.length > 0 ? (
          keywords.map(keyword => (
            <span key={keyword} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded mr-1">
              {keyword}
            </span>
          ))
        ) : null}
      </div>
    </div>
  );
}