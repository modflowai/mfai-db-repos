/**
 * Retry Logic - Intelligent retry strategies for workflow tools
 */

export class RetryLogic {
  private readonly baseDelay = 1000;
  private readonly maxDelay = 8000;
  private readonly backoffMultiplier = 2;
  
  /**
   * Wait with exponential backoff and jitter
   */
  async wait(attemptNumber: number): Promise<void> {
    const delay = Math.min(
      this.baseDelay * Math.pow(this.backoffMultiplier, attemptNumber),
      this.maxDelay
    );
    
    // Add jitter to prevent thundering herd problems
    const jitteredDelay = delay + (Math.random() * 1000);
    
    await new Promise(resolve => setTimeout(resolve, jitteredDelay));
  }
  
  /**
   * Determine if error should be retried
   */
  shouldRetry(error: Error, attemptNumber: number, maxRetries: number): boolean {
    if (attemptNumber >= maxRetries) return false;
    
    // Check if this is a retryable error type
    return this.isRetryableError(error);
  }
  
  /**
   * Check if error type is retryable
   */
  private isRetryableError(error: Error): boolean {
    const errorMessage = error.message.toLowerCase();
    
    // Network and temporary errors are retryable
    const retryablePatterns = [
      'timeout',
      'rate limit',
      'network',
      'econnreset',
      'enotfound',
      'service unavailable',
      'internal server error',
      'bad gateway',
      'gateway timeout'
    ];
    
    return retryablePatterns.some(pattern => errorMessage.includes(pattern));
  }
  
  /**
   * Get retry configuration for specific error types
   */
  getRetryConfig(error: Error): { maxRetries: number; useBackoff: boolean } {
    const errorMessage = error.message.toLowerCase();
    
    // Rate limits need more careful retry handling
    if (errorMessage.includes('rate limit')) {
      return { maxRetries: 3, useBackoff: true };
    }
    
    // Network errors can be retried more aggressively
    if (errorMessage.includes('network') || errorMessage.includes('timeout')) {
      return { maxRetries: 2, useBackoff: true };
    }
    
    // Server errors get fewer retries
    if (errorMessage.includes('server error') || errorMessage.includes('internal error')) {
      return { maxRetries: 1, useBackoff: true };
    }
    
    // Default configuration
    return { maxRetries: 2, useBackoff: true };
  }
  
  /**
   * Calculate delay for specific error types
   */
  calculateDelay(error: Error, attemptNumber: number): number {
    const errorMessage = error.message.toLowerCase();
    
    // Rate limits need longer delays
    if (errorMessage.includes('rate limit')) {
      return Math.min(this.baseDelay * Math.pow(3, attemptNumber), 30000); // Up to 30 seconds
    }
    
    // Network errors can retry faster
    if (errorMessage.includes('network') || errorMessage.includes('timeout')) {
      return Math.min(this.baseDelay * Math.pow(1.5, attemptNumber), 5000); // Up to 5 seconds
    }
    
    // Default exponential backoff
    return Math.min(
      this.baseDelay * Math.pow(this.backoffMultiplier, attemptNumber),
      this.maxDelay
    );
  }
  
  /**
   * Advanced wait with error-specific configuration
   */
  async waitForError(error: Error, attemptNumber: number): Promise<void> {
    const delay = this.calculateDelay(error, attemptNumber);
    const jitteredDelay = delay + (Math.random() * 500); // Smaller jitter for specific delays
    
    await new Promise(resolve => setTimeout(resolve, jitteredDelay));
  }
}