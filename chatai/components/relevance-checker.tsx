'use client';

interface RelevanceData {
  query: string;
  isRelevant: boolean;
  confidence: number;
  domains: string[];
  reasoning: string;
  success: boolean;
  timestamp: string;
}

export function RelevanceChecker({
  relevanceData,
}: {
  relevanceData?: RelevanceData;
}) {
  const isLoading = !relevanceData;

  const { isRelevant, confidence, domains, reasoning } = relevanceData || {};

  return (
    <div className={`p-4 rounded-xl border-2 ${
      isLoading ? 'bg-blue-50 border-blue-200' : 
      isRelevant ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
    }`}>
      {/* Static header - always visible */}
      <div className="flex items-center gap-2 mb-2">
        {isLoading ? (
          <div className="animate-spin size-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        ) : (
          <span className="text-lg">{isRelevant ? '✅' : '❌'}</span>
        )}
        <span className={`font-semibold ${
          isLoading ? 'text-blue-800' : 
          isRelevant ? 'text-green-800' : 'text-red-800'
        }`}>
          Relevance Check
        </span>
        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
          {isLoading ? (
            <div className="w-12 h-3 bg-gray-300 animate-pulse rounded"></div>
          ) : (
            `${Math.round(confidence * 100)}% confident`
          )}
        </span>
      </div>
      
      {/* Domains section - static label, dynamic content */}
      <div className="mb-2">
        <span className="text-sm font-medium text-gray-700">Domains: </span>
        {isLoading ? (
          <div className="inline-flex gap-1">
            <div className="w-16 h-5 bg-gray-300 animate-pulse rounded"></div>
            <div className="w-20 h-5 bg-gray-300 animate-pulse rounded"></div>
            <div className="w-12 h-5 bg-gray-300 animate-pulse rounded"></div>
          </div>
        ) : domains && domains.length > 0 ? (
          domains.map(domain => (
            <span key={domain} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded mr-1">
              {domain}
            </span>
          ))
        ) : null}
      </div>
      
      {/* Reasoning section - dynamic content */}
      {isLoading ? (
        <div className="space-y-2">
          <div className="w-full h-3 bg-gray-300 animate-pulse rounded"></div>
          <div className="w-3/4 h-3 bg-gray-300 animate-pulse rounded"></div>
        </div>
      ) : reasoning ? (
        <p className="text-sm text-gray-700">{reasoning}</p>
      ) : null}
    </div>
  );
}