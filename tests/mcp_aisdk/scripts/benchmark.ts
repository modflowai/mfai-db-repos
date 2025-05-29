import { createSSEClient } from '../src/clients/client-factory';
import { performance } from 'perf_hooks';
import { config } from 'dotenv';

config();

interface BenchmarkResult {
  operation: string;
  duration: number;
  success: boolean;
  error?: string;
}

async function runBenchmarks() {
  console.log('🚀 MCP Server Performance Benchmarks\n');
  console.log(`Server: ${process.env.MCP_SERVER_URL}`);
  console.log(`Time: ${new Date().toISOString()}\n`);
  
  const results: BenchmarkResult[] = [];
  
  try {
    // Connection benchmark
    console.log('⏱️  Testing SSE Connection...');
    const connectionStart = performance.now();
    const client = await createSSEClient({
      apiKey: process.env.MCP_API_KEY!,
      serverUrl: process.env.MCP_SERVER_URL!,
    });
    results.push({
      operation: 'SSE Connection',
      duration: performance.now() - connectionStart,
      success: true,
    });

    // Tool discovery benchmark
    console.log('⏱️  Testing Tool Discovery...');
    const discoveryStart = performance.now();
    await client.listTools();
    results.push({
      operation: 'Tool Discovery',
      duration: performance.now() - discoveryStart,
      success: true,
    });

    // Repository listing benchmark (without navigation)
    console.log('⏱️  Testing Repository Listing (no navigation)...');
    const repoStart = performance.now();
    await client.callTool('list_repositories_with_navigation', {
      include_navigation: false,
    });
    results.push({
      operation: 'List Repositories (no nav)',
      duration: performance.now() - repoStart,
      success: true,
    });

    // Repository listing benchmark (with navigation)
    console.log('⏱️  Testing Repository Listing (with navigation)...');
    const repoNavStart = performance.now();
    await client.callTool('list_repositories_with_navigation', {
      include_navigation: true,
    });
    results.push({
      operation: 'List Repositories (with nav)',
      duration: performance.now() - repoNavStart,
      success: true,
    });

    // Text search benchmark
    console.log('⏱️  Testing Text Search...');
    const textSearchStart = performance.now();
    await client.callTool('mfai_search', {
      query: 'modflow',
      search_type: 'text',
    });
    results.push({
      operation: 'Text Search',
      duration: performance.now() - textSearchStart,
      success: true,
    });

    // Semantic search benchmark
    console.log('⏱️  Testing Semantic Search...');
    const semanticSearchStart = performance.now();
    await client.callTool('mfai_search', {
      query: 'groundwater flow simulation',
      search_type: 'semantic',
    });
    results.push({
      operation: 'Semantic Search',
      duration: performance.now() - semanticSearchStart,
      success: true,
    });

    // Repository-filtered search benchmark
    console.log('⏱️  Testing Repository-Filtered Search...');
    const filteredSearchStart = performance.now();
    await client.callTool('mfai_search', {
      query: 'model',
      search_type: 'text',
      repositories: ['modflowapi'],
    });
    results.push({
      operation: 'Filtered Search',
      duration: performance.now() - filteredSearchStart,
      success: true,
    });

    // Multiple sequential operations benchmark
    console.log('⏱️  Testing Sequential Operations...');
    const sequentialStart = performance.now();
    for (let i = 0; i < 5; i++) {
      await client.callTool('mfai_search', {
        query: `test ${i}`,
        search_type: 'text',
      });
    }
    results.push({
      operation: '5 Sequential Searches',
      duration: performance.now() - sequentialStart,
      success: true,
    });

    await client.close();

  } catch (error) {
    console.error('❌ Benchmark error:', error);
    results.push({
      operation: 'Error',
      duration: 0,
      success: false,
      error: error.message,
    });
  }

  // Print results
  console.log('\n=== Performance Benchmark Results ===\n');
  console.table(results.map(r => ({
    Operation: r.operation,
    'Duration (ms)': r.success ? r.duration.toFixed(2) : 'N/A',
    'Status': r.success ? '✅' : '❌',
    'Error': r.error || '',
  })));

  // Compare with expected thresholds
  const thresholds = {
    'SSE Connection': 1000,
    'Tool Discovery': 500,
    'List Repositories (no nav)': 1000,
    'List Repositories (with nav)': 3000,
    'Text Search': 3000,
    'Semantic Search': 5000,
    'Filtered Search': 2000,
    '5 Sequential Searches': 10000,
  };

  console.log('\n=== Performance vs Thresholds ===\n');
  let passCount = 0;
  let totalCount = 0;
  
  results.forEach(r => {
    if (r.success && thresholds[r.operation]) {
      totalCount++;
      const threshold = thresholds[r.operation];
      const status = r.duration <= threshold ? '✅ PASS' : '❌ FAIL';
      if (r.duration <= threshold) passCount++;
      console.log(`${r.operation}: ${r.duration.toFixed(2)}ms / ${threshold}ms ${status}`);
    }
  });

  // Summary statistics
  console.log('\n=== Summary Statistics ===\n');
  const successfulResults = results.filter(r => r.success);
  if (successfulResults.length > 0) {
    const durations = successfulResults.map(r => r.duration);
    const avg = durations.reduce((a, b) => a + b, 0) / durations.length;
    const min = Math.min(...durations);
    const max = Math.max(...durations);
    
    console.log(`Total Operations: ${results.length}`);
    console.log(`Successful: ${successfulResults.length}`);
    console.log(`Failed: ${results.length - successfulResults.length}`);
    console.log(`\nPerformance:`);
    console.log(`  Average: ${avg.toFixed(2)}ms`);
    console.log(`  Min: ${min.toFixed(2)}ms`);
    console.log(`  Max: ${max.toFixed(2)}ms`);
    console.log(`\nThreshold Tests:`);
    console.log(`  Passed: ${passCount}/${totalCount} (${((passCount/totalCount)*100).toFixed(1)}%)`);
  }

  // Overall assessment
  const allPassed = passCount === totalCount && results.every(r => r.success);
  console.log(`\n${allPassed ? '✅' : '❌'} Overall: ${allPassed ? 'All benchmarks passed!' : 'Some benchmarks failed or exceeded thresholds.'}`);
}

// Run benchmarks
if (require.main === module) {
  runBenchmarks().catch(console.error);
}