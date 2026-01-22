import { NextAuthOptions, Account, Session } from "next-auth"
import { JWT } from "next-auth/jwt"
import KeycloakProvider from "next-auth/providers/keycloak"

type ExtendedJWT = JWT & { accessToken?: string };

export const authOptions: NextAuthOptions = {
    providers: [
        KeycloakProvider({
            clientId: process.env.KEYCLOAK_CLIENT_ID!,
            clientSecret: process.env.KEYCLOAK_CLIENT_SECRET!,
            issuer: process.env.KEYCLOAK_ISSUER,
            httpOptions: { timeout: 10000 },
        }),
    ],
    callbacks: {
        async jwt({ token, account }: { token: ExtendedJWT, account: Account | null }) {
            if (account) {
                token.accessToken = account.access_token
            }
            return token
        },
        async session({ session, token }: { session: Session, token: ExtendedJWT }) {
            session.accessToken = token.accessToken
            return session
        },
    },
}
