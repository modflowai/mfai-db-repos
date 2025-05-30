'use client';

interface SearchResult {
  filename: string;
  filepath: string;
  repo_name: string;
  snippet: string;
  similarity?: number;
  relevanceScore?: number;
}

interface RepositorySearchData {
  query: string;
  strategy: string;
  repositories: string[];
  results: SearchResult[];
  totalFound: number;
  repositoriesSearched: string[];
  searchStrategy: string;
  success: boolean;
  timestamp: string;
}

export function RepositorySearcher({
  searchData,
}: {
  searchData?: RepositorySearchData;
}) {
  if (!searchData) {
    return (
      <div className="flex items-center gap-2 p-3 bg-orange-50 rounded-lg border border-orange-200">
        <div className="animate-spin size-4 border-2 border-orange-500 border-t-transparent rounded-full"></div>
        <span className="text-orange-700 font-medium">Searching repositories...</span>
      </div>
    );
  }

  const { results, totalFound, repositoriesSearched, searchStrategy } = searchData;

  return (
    <div className="p-4 rounded-xl border-2 bg-orange-50 border-orange-200">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">🔍</span>
        <span className="font-semibold text-orange-800">Repository Search</span>
        <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
          {totalFound} results
        </span>
      </div>
      
      <div className="mb-3 text-sm">
        <span className="font-medium text-gray-700">Searched: </span>
        {repositoriesSearched.map(repo => (
          <span key={repo} className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs mr-1">
            {repo}
          </span>
        ))}
        <span className="ml-2 text-gray-500">using {searchStrategy} strategy</span>
      </div>

      {results.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700">Top Results:</div>
          {results.slice(0, 3).map((result, index) => (
            <div key={index} className="bg-white p-3 rounded border border-orange-200">
              <div className="flex justify-between items-start mb-1">
                <span className="font-medium text-gray-800 text-sm">{result.filename}</span>
                {result.relevanceScore && (
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                    {Math.round(result.relevanceScore * 100)}%
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-600 mb-1">{result.repo_name} • {result.filepath}</div>
              <div className="text-xs text-gray-700">{result.snippet.substring(0, 100)}...</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}