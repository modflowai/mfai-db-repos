import { type NextRequest, NextResponse } from 'next/server';
import { getNextTierLimits } from '@/lib/rate-limit';
import { z } from 'zod';

const querySchema = z.object({
  userRole: z.enum(['guest', 'regular', 'premium']),
});

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const userRole = searchParams.get('userRole');
    
    const { userRole: validatedUserRole } = querySchema.parse({ userRole });
    
    const nextTierInfo = await getNextTierLimits(validatedUserRole);
    
    return NextResponse.json({ nextTierInfo });
  } catch (error) {
    console.error('Error getting next tier limits:', error);
    return NextResponse.json(
      { error: 'Failed to get next tier limits' },
      { status: 500 }
    );
  }
}