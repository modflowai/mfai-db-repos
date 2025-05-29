import { Redis } from '@upstash/redis';
import { drizzle } from 'drizzle-orm/postgres-js';
import { eq } from 'drizzle-orm';
import postgres from 'postgres';
import { rateLimit } from './db/schema';
import type { UserRole } from '@/app/(auth)/auth';

// Initialize Redis client
const redis = Redis.fromEnv();

// Initialize database client
// biome-ignore lint: Forbidden non-null assertion.
const client = postgres(process.env.POSTGRES_URL!);
const db = drizzle(client);

interface RateLimitResult {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetTime: Date;
  timeWindow: 'minute' | 'daily';
}

interface RateLimitCheck {
  allowed: boolean;
  blockedBy?: {
    timeWindow: 'minute' | 'daily';
    limit: number;
    remaining: number;
    resetTime: Date;
  };
}

// Cache for rate limits to avoid repeated database queries
const rateLimitCache = new Map<string, { limit: number; timeWindow: 'minute' | 'daily' }[]>();

async function getRateLimitsForRole(role: UserRole): Promise<{ limit: number; timeWindow: 'minute' | 'daily' }[]> {
  // Check cache first
  if (rateLimitCache.has(role)) {
    return rateLimitCache.get(role)!;
  }

  try {
    const limits = await db
      .select({
        limit: rateLimit.limitCount,
        timeWindow: rateLimit.timeWindow,
      })
      .from(rateLimit)
      .where(eq(rateLimit.role, role));

    const formattedLimits = limits.map(l => ({
      limit: l.limit,
      timeWindow: l.timeWindow as 'minute' | 'daily'
    }));

    // Cache the result for 5 minutes
    rateLimitCache.set(role, formattedLimits);
    setTimeout(() => rateLimitCache.delete(role), 5 * 60 * 1000);

    return formattedLimits;
  } catch (error) {
    console.error('Error fetching rate limits for role:', role, error);
    
    // Fallback to conservative defaults if database fails
    return [
      { limit: 3, timeWindow: 'minute' },
      { limit: 20, timeWindow: 'daily' }
    ];
  }
}

async function checkSingleRateLimit(
  userId: string, 
  timeWindow: 'minute' | 'daily', 
  limit: number
): Promise<RateLimitResult> {
  const now = new Date();
  const key = `rate-limit:user:${userId}:${timeWindow}`;
  
  try {
    // Get current count
    const current = await redis.get(key) || 0;
    const currentCount = typeof current === 'number' ? current : Number.parseInt(String(current), 10) || 0;
    
    if (currentCount >= limit) {
      // Rate limit exceeded
      const ttl = await redis.ttl(key);
      const resetTime = new Date(now.getTime() + (ttl * 1000));
      
      return {
        allowed: false,
        limit,
        remaining: 0,
        resetTime,
        timeWindow
      };
    }
    
    // Increment counter
    const newCount = await redis.incr(key);
    
    // Set TTL if this is the first request in the window
    if (newCount === 1) {
      const ttlSeconds = timeWindow === 'minute' ? 60 : 24 * 60 * 60;
      await redis.expire(key, ttlSeconds);
    }
    
    // Calculate reset time
    const ttl = await redis.ttl(key);
    const resetTime = new Date(now.getTime() + (ttl * 1000));
    
    return {
      allowed: true,
      limit,
      remaining: Math.max(0, limit - newCount),
      resetTime,
      timeWindow
    };
  } catch (error) {
    console.error('Redis error in rate limiting:', error);
    
    // If Redis fails, allow the request but log the error
    return {
      allowed: true,
      limit,
      remaining: limit - 1,
      resetTime: new Date(now.getTime() + (timeWindow === 'minute' ? 60000 : 24 * 60 * 60 * 1000)),
      timeWindow
    };
  }
}

export async function getNextTierLimits(currentRole: UserRole): Promise<{ role: UserRole; limits: { limit: number; timeWindow: 'minute' | 'daily' }[] } | null> {
  const tierOrder: UserRole[] = ['guest', 'regular', 'premium'];
  const currentIndex = tierOrder.indexOf(currentRole);
  
  if (currentIndex === -1 || currentIndex >= tierOrder.length - 1) {
    return null; // No higher tier available
  }
  
  const nextRole = tierOrder[currentIndex + 1];
  const nextTierLimits = await getRateLimitsForRole(nextRole);
  
  return {
    role: nextRole,
    limits: nextTierLimits
  };
}

export async function checkRateLimit(userId: string, role: UserRole): Promise<RateLimitCheck> {
  try {
    // Get rate limits for the user's role
    const limits = await getRateLimitsForRole(role);
    
    // Check all time windows
    const results = await Promise.all(
      limits.map(({ limit, timeWindow }) => 
        checkSingleRateLimit(userId, timeWindow, limit)
      )
    );
    
    // Find if any limit is exceeded
    const blockedResult = results.find(result => !result.allowed);
    
    if (blockedResult) {
      return {
        allowed: false,
        blockedBy: {
          timeWindow: blockedResult.timeWindow,
          limit: blockedResult.limit,
          remaining: blockedResult.remaining,
          resetTime: blockedResult.resetTime
        }
      };
    }
    
    return { allowed: true };
  } catch (error) {
    console.error('Error in checkRateLimit:', error);
    
    // If there's an error, allow the request but log it
    return { allowed: true };
  }
}