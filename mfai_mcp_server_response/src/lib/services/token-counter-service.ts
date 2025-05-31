export class TokenCounterService {
  private static readonly CHARS_PER_TOKEN = 4; // Rough estimate for English text
  
  static countTokens(text: string): number {
    // Simple token estimation: 1 token ≈ 4 characters for English
    return Math.ceil(text.length / this.CHARS_PER_TOKEN);
  }
  
  static isUnder8k(text: string): boolean {
    return this.countTokens(text) < 8000;
  }
}