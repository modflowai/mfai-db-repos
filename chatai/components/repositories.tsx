'use client';

interface Repository {
  id: number;
  name: string;
  url: string;
  file_count: number;
  navigation_guide?: string;
  repository_type: string;
  created_at: string;
  updated_at: string;
  relevanceScore?: number;
  relevanceReasoning?: string;
}

interface RepositoriesData {
  repositories: Repository[];
  count: number;
  userQuery: string | null;
  sortedByRelevance: boolean;
  timestamp: string;
}

const SAMPLE: RepositoriesData = {
  repositories: [
    {
      id: 1,
      name: "pest",
      url: "https://github.com/modflowai/pest-git",
      file_count: 47,
      navigation_guide: "# PEST - MCP Navigation Guide\n\n## Primary Purpose\nThis repository is THE authority on the PEST (Parameter ESTimation) software suite, detailing its model-independent parameter estimation capabilities...",
      repository_type: "documentation",
      created_at: "2025-05-28T09:32:07.367Z",
      updated_at: "2025-05-28T18:08:53.993Z"
    },
    {
      id: 2,
      name: "mfusg",
      url: "https://github.com/modflowai/mfusg-git",
      file_count: 77,
      navigation_guide: "# MFUSG - MCP Navigation Guide\n\n## Primary Purpose\nThis repository is THE authority on simulating 3D groundwater chemical species transport using the MODFLOW-UG Transport (UGT) code...",
      repository_type: "documentation",
      created_at: "2025-05-28T09:46:26.712Z",
      updated_at: "2025-05-28T18:02:26.368Z"
    }
  ],
  count: 2,
  userQuery: null,
  sortedByRelevance: false,
  timestamp: new Date().toISOString()
};

export function Repositories({
  repositoriesData = SAMPLE,
}: {
  repositoriesData?: RepositoriesData;
}) {
  const { repositories, count, userQuery, sortedByRelevance } = repositoriesData;

  return (
    <div className="flex flex-col gap-4 rounded-2xl p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 max-w-2xl">
      <div className="flex flex-row justify-between items-center">
        <div className="flex flex-row gap-2 items-center">
          <div className="size-10 rounded-full bg-blue-500 flex items-center justify-center">
            <span className="text-white font-semibold text-lg">📚</span>
          </div>
          <div>
            <div className="text-xl font-semibold text-gray-800">
              MODFLOW Repositories
            </div>
            <div className="text-sm text-gray-600">
              {count} {count === 1 ? 'repository' : 'repositories'} available
            </div>
          </div>
        </div>
        
        {sortedByRelevance && (
          <div className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
            Sorted by relevance
          </div>
        )}
      </div>

      {userQuery && (
        <div className="text-sm text-gray-600 bg-blue-50 p-2 rounded-lg border-l-4 border-blue-400">
          <strong>Query:</strong> {userQuery}
        </div>
      )}

      <div className="flex flex-col gap-3">
        {repositories.map((repo) => (
          <div key={repo.id} className="bg-white rounded-xl p-4 border border-gray-200 hover:border-blue-300 transition-colors">
            <div className="flex flex-row justify-between items-start mb-2">
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-800">{repo.name}</h3>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                    {repo.file_count} files
                  </span>
                  {repo.relevanceScore !== undefined && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                      {Math.round(repo.relevanceScore * 100)}% relevant
                    </span>
                  )}
                </div>
                <a 
                  href={repo.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-800 hover:underline mt-1"
                >
                  {repo.url}
                </a>
              </div>
            </div>

            {repo.relevanceReasoning && (
              <div className="text-sm text-gray-600 mb-2 bg-yellow-50 p-2 rounded border-l-2 border-yellow-300">
                <strong>Why relevant:</strong> {repo.relevanceReasoning}
              </div>
            )}

            {repo.navigation_guide && (
              <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded mt-2">
                <strong>Description:</strong> {repo.navigation_guide.substring(0, 150)}
                {repo.navigation_guide.length > 150 && '...'}
              </div>
            )}

            <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
              <span className="capitalize">{repo.repository_type}</span>
              <span>•</span>
              <span>Updated {new Date(repo.updated_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-200">
        Retrieved {new Date(repositoriesData.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}