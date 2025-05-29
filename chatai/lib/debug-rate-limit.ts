import { Redis } from '@upstash/redis';
import { getUserById } from './db/queries';

const redis = Redis.fromEnv();

export async function debugRateLimit(userId: string) {
  console.log('\n🔍 Debug Rate Limiting for user:', userId);
  
  try {
    // Get user info
    const user = await getUserById(userId);
    console.log('👤 User role:', user?.role);
    
    // Check Redis keys
    const minuteKey = `rate-limit:user:${userId}:minute`;
    const dailyKey = `rate-limit:user:${userId}:daily`;
    
    const minuteCount = await redis.get(minuteKey);
    const dailyCount = await redis.get(dailyKey);
    const minuteTTL = await redis.ttl(minuteKey);
    const dailyTTL = await redis.ttl(dailyKey);
    
    console.log('⏱️  Minute limit:', minuteCount, '(TTL:', minuteTTL, 'seconds)');
    console.log('📅 Daily limit:', dailyCount, '(TTL:', dailyTTL, 'seconds)');
    
    return {
      userId,
      userRole: user?.role,
      minute: { count: minuteCount, ttl: minuteTTL },
      daily: { count: dailyCount, ttl: dailyTTL }
    };
  } catch (error) {
    console.error('❌ Debug error:', error);
    return null;
  }
}