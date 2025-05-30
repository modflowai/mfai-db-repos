/**
 * Utilities for streaming updates during workflow execution
 */

import type { DataStreamWriter } from 'ai';
import type { ToolStatus } from './workflow-tool';

export class StreamingUtils {
  constructor(private dataStream: DataStreamWriter) {}

  /**
   * Stream a tool status update with formatted message
   */
  async streamToolStatus(status: ToolStatus): Promise<void> {
    const statusIcon = this.getStatusIcon(status.phase);
    const progressText = status.progress !== undefined ? ` (${status.progress}%)` : '';
    const actionText = status.currentAction ? `: ${status.currentAction}` : '';
    
    const content = `${statusIcon} **${status.tool}**${progressText}${actionText}\n\n`;
    console.log('🔧 StreamingUtils - writing tool status:', content);
    
    this.dataStream.writeData({
      type: 'text-delta',
      content,
    });
  }

  /**
   * Stream workflow start message
   */
  async streamWorkflowStart(totalSteps: number): Promise<void> {
    this.dataStream.writeData({
      type: 'text-delta',
      content: `🚀 **Modular Workflow Started** - ${totalSteps} steps\n\n`,
    });
  }

  /**
   * Stream workflow completion message
   */
  async streamWorkflowComplete(totalTime: number): Promise<void> {
    this.dataStream.writeData({
      type: 'text-delta',
      content: `✅ **Workflow Complete** - Finished in ${(totalTime / 1000).toFixed(1)}s\n\n`,
    });
  }

  /**
   * Stream tool result summary
   */
  async streamToolResult(toolName: string, result: any): Promise<void> {
    if (result.success) {
      this.dataStream.writeData({
        type: 'text-delta',
        content: `📊 **${toolName} Result**: ${result.shortSummary}\n\n`,
      });
    } else {
      this.dataStream.writeData({
        type: 'text-delta',
        content: `❌ **${toolName} Failed**: ${result.errors?.[0]?.message || 'Unknown error'}\n\n`,
      });
    }
  }

  /**
   * Stream error with retry information
   */
  async streamError(toolName: string, error: any, isRetrying: boolean, attemptNumber?: number): Promise<void> {
    const retryText = isRetrying && attemptNumber ? ` (Retry ${attemptNumber})` : '';
    
    this.dataStream.writeData({
      type: 'text-delta',
      content: `⚠️ **${toolName} Error**${retryText}: ${error.message}\n\n`,
    });
  }

  /**
   * Stream detailed progress information
   */
  async streamProgress(toolName: string, current: number, total: number, currentItem?: string): Promise<void> {
    const percentage = Math.round((current / total) * 100);
    const itemText = currentItem ? ` - ${currentItem}` : '';
    
    this.dataStream.writeData({
      type: 'text-delta',
      content: `🔄 **${toolName}**: ${current}/${total} (${percentage}%)${itemText}\n\n`,
    });
  }

  /**
   * Stream final answer or result
   */
  async streamFinalAnswer(answer: string): Promise<void> {
    const content = `\n📝 **Answer**:\n\n${answer}\n\n`;
    console.log('🔧 StreamingUtils - writing final answer:', content.length, 'characters');
    
    this.dataStream.writeData({
      type: 'text-delta',
      content,
    });
  }

  /**
   * Get emoji icon for tool status
   */
  private getStatusIcon(phase: ToolStatus['phase']): string {
    switch (phase) {
      case 'starting':
        return '🔄';
      case 'executing':
        return '⚡';
      case 'processing':
        return '🧠';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      case 'retrying':
        return '🔁';
      default:
        return '⚪';
    }
  }
}

/**
 * Create a streaming status function for a tool context
 */
export function createStreamingStatusFunction(
  dataStream: DataStreamWriter,
  toolName: string
): (status: Omit<ToolStatus, 'tool'>) => Promise<void> {
  const streamingUtils = new StreamingUtils(dataStream);
  
  return async (status) => {
    await streamingUtils.streamToolStatus({
      ...status,
      tool: toolName
    });
  };
}