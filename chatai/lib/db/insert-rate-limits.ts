import { config } from 'dotenv';
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { rateLimit } from './schema';

config({
  path: '.env.local',
});

const insertRateLimits = async () => {
  if (!process.env.POSTGRES_URL) {
    throw new Error('POSTGRES_URL is not defined');
  }

  const connection = postgres(process.env.POSTGRES_URL, { max: 1 });
  const db = drizzle(connection);

  console.log('🌱 Inserting rate limits...');

  const rateLimits = [
    { role: 'guest' as const, timeWindow: 'minute' as const, limitCount: 3 },
    { role: 'guest' as const, timeWindow: 'daily' as const, limitCount: 20 },
    { role: 'regular' as const, timeWindow: 'minute' as const, limitCount: 5 },
    { role: 'regular' as const, timeWindow: 'daily' as const, limitCount: 100 },
    { role: 'premium' as const, timeWindow: 'minute' as const, limitCount: 10 },
    { role: 'premium' as const, timeWindow: 'daily' as const, limitCount: 1000 },
  ];

  try {
    // Check if data already exists
    const existing = await db.select().from(rateLimit);
    if (existing.length > 0) {
      console.log('📊 Rate limits already exist:', existing.length, 'records');
      console.log('✅ Skipping insertion');
      return;
    }

    // Insert the data
    const result = await db.insert(rateLimit).values(rateLimits).returning();
    console.log('✅ Rate limits inserted successfully!');
    console.log('📊 Inserted records:');
    result.forEach(limit => {
      console.log(`   ${limit.role}: ${limit.limitCount}/${limit.timeWindow}`);
    });
  } catch (error) {
    console.error('❌ Error inserting rate limits:', error);
    throw error;
  } finally {
    await connection.end();
  }
};

insertRateLimits().catch((err) => {
  console.error('❌ Insertion failed');
  console.error(err);
  process.exit(1);
});