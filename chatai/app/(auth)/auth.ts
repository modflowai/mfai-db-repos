import NextAuth, { type DefaultSession } from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import Google from 'next-auth/providers/google';
import GitHub from 'next-auth/providers/github';
import { createGuestUser, getUser, createUser } from '@/lib/db/queries';
import { authConfig } from './auth.config';
import type { DefaultJWT } from 'next-auth/jwt';

export type UserType = 'guest' | 'regular';

// Role types from database schema
export type UserRole = 'guest' | 'regular' | 'premium';

// Utility to map database role to session UserType
export function roleToUserType(role: UserRole): UserType {
  switch (role) {
    case 'guest':
      return 'guest';
    case 'regular':
    case 'premium':
      return 'regular';
    default:
      return 'guest';
  }
}

declare module 'next-auth' {
  interface Session extends DefaultSession {
    user: {
      id: string;
      type: UserType;
    } & DefaultSession['user'];
  }

  interface User {
    id?: string;
    email?: string | null;
    type: UserType;
  }
}

declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    id: string;
    type: UserType;
  }
}

export const {
  handlers: { GET, POST },
  auth,
  signIn,
  signOut,
} = NextAuth({
  ...authConfig,
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID,
      clientSecret: process.env.AUTH_GOOGLE_SECRET,
    }),
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID,
      clientSecret: process.env.AUTH_GITHUB_SECRET,
    }),
    Credentials({
      id: 'guest',
      credentials: {},
      async authorize() {
        const [guestUser] = await createGuestUser();
        return { ...guestUser, type: 'guest' };
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      // Handle OAuth users (Google and GitHub)
      if ((account?.provider === 'google' || account?.provider === 'github') && user.email) {
        // Check if user exists in our database
        const existingUsers = await getUser(user.email);
        
        if (existingUsers.length === 0) {
          // Create new user for OAuth (no password needed)
          await createUser(user.email);
          const [newUser] = await getUser(user.email);
          user.id = newUser.id;
        } else {
          // User exists, use existing ID
          user.id = existingUsers[0].id;
        }
        
        user.type = 'regular';
        return true;
      }
      
      // Handle existing credential flows (email/password and guest)
      return true;
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id as string;
        token.type = user.type;
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id;
        session.user.type = token.type;
      }

      return session;
    },
  },
});
