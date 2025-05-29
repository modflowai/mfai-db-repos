import { createSSEClient } from '@/clients/client-factory';
import { google } from '@ai-sdk/google';
import { generateText } from 'ai';
import { config } from 'dotenv';

config();

async function analyzeRepositoryWithAI() {
  console.log('🚀 Starting AI-powered repository analysis...\n');
  
  const client = await createSSEClient({
    apiKey: process.env.MCP_API_KEY!,
    serverUrl: process.env.MCP_SERVER_URL!,
  });

  try {
    // 1. Get repositories with navigation guides
    console.log('📚 Fetching repositories with navigation guides...');
    const repoResult = await client.callTool('list_repositories_with_navigation', {
      include_navigation: true,
    });
    
    const repositories = JSON.parse(repoResult.content[0].text);
    console.log(`Found ${repositories.length} repositories\n`);
    
    // 2. Use AI to analyze navigation guides
    for (const repo of repositories) {
      if (repo.navigation_guide) {
        console.log(`\n📊 Analyzing repository: ${repo.name}`);
        console.log(`URL: ${repo.url}`);
        console.log(`Files: ${repo.file_count}`);
        
        const analysis = await generateText({
          model: google('gemini-2.0-flash-001'),
          apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY!,
          prompt: `Based on this repository navigation guide, what are the key MODFLOW features implemented?
          
          Navigation Guide:
          ${repo.navigation_guide}
          
          List the top 3 MODFLOW-specific features:`,
        });

        console.log(`\n🤖 AI Analysis:\n${analysis.text}`);
        
        // 3. Search for specific features identified by AI
        console.log('\n🔍 Searching for identified features...');
        const features = analysis.text.split('\n')
          .filter(line => line.trim())
          .slice(0, 3);
        
        for (const feature of features) {
          const searchResult = await client.callTool('mfai_search', {
            query: feature,
            search_type: 'semantic',
            repositories: [repo.name],
          });
          
          const results = JSON.parse(searchResult.content[0].text);
          console.log(`  📌 "${feature.trim()}" - Found in ${results.length} files`);
          
          // Show top 3 matches
          if (results.length > 0) {
            console.log('     Top matches:');
            results.slice(0, 3).forEach((result, idx) => {
              console.log(`     ${idx + 1}. ${result.filepath} (similarity: ${result.similarity?.toFixed(3) || 'N/A'})`);
            });
          }
        }
        
        console.log('\n' + '='.repeat(80));
      }
    }
    
    // 4. Cross-repository analysis
    console.log('\n\n🔗 Cross-Repository Analysis');
    console.log('Searching for common MODFLOW patterns across all repositories...\n');
    
    const commonPatterns = [
      'groundwater flow equation',
      'finite difference method',
      'boundary conditions',
      'stress periods',
      'model packages',
    ];
    
    for (const pattern of commonPatterns) {
      console.log(`\n🔎 Pattern: "${pattern}"`);
      
      const searchResult = await client.callTool('mfai_search', {
        query: pattern,
        search_type: 'semantic',
      });
      
      const results = JSON.parse(searchResult.content[0].text);
      
      // Group by repository
      const byRepo = results.reduce((acc, result) => {
        if (!acc[result.repo_name]) acc[result.repo_name] = 0;
        acc[result.repo_name]++;
        return acc;
      }, {} as Record<string, number>);
      
      Object.entries(byRepo).forEach(([repo, count]) => {
        console.log(`   ${repo}: ${count} occurrences`);
      });
    }
    
  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await client.close();
    console.log('\n✅ Analysis complete!');
  }
}

// Run the analysis
if (require.main === module) {
  analyzeRepositoryWithAI().catch(console.error);
}