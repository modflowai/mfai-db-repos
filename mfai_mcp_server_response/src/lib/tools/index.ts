// Tool definitions and registry following MCP best practices
import { DocumentRetrievalHandler } from '../handlers/document-retrieval-handler.js';
import { RepositoryListHandler } from '../handlers/repository-list-handler.js';
import { DocumentSearchService } from '../services/document-search-service.js';
import { GeminiCompressionService } from '../services/gemini-response-service.js';
import type { DocumentRetrievalInput, RepositoryListInput } from '../types/response-types.js';

export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: any;
  handler: (args: any) => Promise<any>;
}

export class ToolRegistry {
  private tools: Map<string, ToolDefinition> = new Map();
  private documentHandler: DocumentRetrievalHandler;
  private repositoryHandler: RepositoryListHandler;

  constructor(
    searchService: DocumentSearchService,
    compressionService: GeminiCompressionService,
    sqlConnection: any
  ) {
    this.documentHandler = new DocumentRetrievalHandler(searchService, compressionService, sqlConnection);
    this.repositoryHandler = new RepositoryListHandler(sqlConnection);
    
    this.registerTools();
  }

  private registerTools() {
    // Repository List Tool
    const repoListDef = RepositoryListHandler.getToolDefinition();
    this.tools.set(repoListDef.name, {
      ...repoListDef,
      handler: async (args: RepositoryListInput) => this.repositoryHandler.handle(args)
    });

    // Document Retrieval Tool
    const docRetrievalDef = DocumentRetrievalHandler.getToolDefinition();
    this.tools.set(docRetrievalDef.name, {
      ...docRetrievalDef,
      handler: async (args: DocumentRetrievalInput) => this.documentHandler.handle(args)
    });
  }

  getToolDefinitions() {
    return Array.from(this.tools.values()).map(tool => ({
      name: tool.name,
      description: tool.description,
      inputSchema: tool.inputSchema
    }));
  }

  async executeTool(name: string, args: any) {
    const tool = this.tools.get(name);
    if (!tool) {
      throw new Error(`Unknown tool: ${name}`);
    }
    return await tool.handler(args);
  }

  hasTool(name: string): boolean {
    return this.tools.has(name);
  }
}