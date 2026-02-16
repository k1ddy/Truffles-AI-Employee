import { NextAuthOptions } from "next-auth"
import { JWT } from "next-auth/jwt"
import KeycloakProvider from "next-auth/providers/keycloak"

// Extend the built-in types
declare module "next-auth/jwt" {
    interface JWT {
        accessToken?: string
        refreshToken?: string
        expiresAt?: number
        error?: string
    }
}

declare module "next-auth" {
    interface Session {
        accessToken?: string
        error?: string
    }
}

async function refreshAccessToken(token: JWT): Promise<JWT> {
    try {
        if (!token.refreshToken) throw new Error("No refresh token");

        const url = `${process.env.KEYCLOAK_ISSUER}/protocol/openid-connect/token`;
        const response = await fetch(url, {
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            method: "POST",
            body: new URLSearchParams({
                client_id: process.env.KEYCLOAK_CLIENT_ID!,
                client_secret: process.env.KEYCLOAK_CLIENT_SECRET!,
                grant_type: "refresh_token",
                refresh_token: token.refreshToken,
            }),
        });

        const refreshedTokens = await response.json();

        if (!response.ok) {
            throw refreshedTokens;
        }

        return {
            ...token,
            accessToken: refreshedTokens.access_token,
            expiresAt: Math.floor(Date.now() / 1000) + refreshedTokens.expires_in,
            // Fall back to old refresh token if new one not provided
            refreshToken: refreshedTokens.refresh_token ?? token.refreshToken,
        };
    } catch (error) {
        console.error("Error refreshing access token", error);
        return {
            ...token,
            error: "RefreshAccessTokenError",
        };
    }
}

const SESSION_MAX_AGE_SECONDS = Number(process.env.CONSOLE_SESSION_MAX_AGE_SECONDS ?? 24 * 60 * 60);
const SESSION_UPDATE_AGE_SECONDS = Number(process.env.CONSOLE_SESSION_UPDATE_AGE_SECONDS ?? 5 * 60);
const KEYCLOAK_SCOPE = process.env.KEYCLOAK_SCOPE ?? "openid profile email offline_access";

export const authOptions: NextAuthOptions = {
    providers: [
        KeycloakProvider({
            clientId: process.env.KEYCLOAK_CLIENT_ID!,
            clientSecret: process.env.KEYCLOAK_CLIENT_SECRET!,
            issuer: process.env.KEYCLOAK_ISSUER,
            authorization: { params: { scope: KEYCLOAK_SCOPE } },
            httpOptions: { timeout: 10000 },
        }),
    ],
    session: {
        strategy: "jwt",
        maxAge: SESSION_MAX_AGE_SECONDS,
        updateAge: SESSION_UPDATE_AGE_SECONDS,
    },
    jwt: {
        maxAge: SESSION_MAX_AGE_SECONDS,
    },
    callbacks: {
        async jwt({ token, account }) {
            // Initial sign in
            if (account) {
                return {
                    accessToken: account.access_token,
                    refreshToken: account.refresh_token,
                    expiresAt: account.expires_at,
                };
            }

            // Return previous token if the access token has not expired yet
            // Give a 10 second buffer
            if (token.expiresAt && Date.now() < (token.expiresAt * 1000 - 10000)) {
                return token;
            }

            // Access token has expired, try to update it
            return await refreshAccessToken(token);
        },
        async session({ session, token }) {
            session.accessToken = token.accessToken;
            session.error = token.error;
            return session;
        },
    },
}
