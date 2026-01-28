"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import { authApi, canAccessConsole } from "@/lib/api-client";

export default function TenantsPage() {
    const { data: session } = useSession();

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadTenants = canAccessConsole(role, "tenants", "read");

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра Tenants.
            </div>
        );
    }

    if (meLoading) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Загрузка роли...
            </div>
        );
    }

    if (!canReadTenants) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к Tenants." />
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="tenants-page">
            <h1 className="text-2xl font-bold mb-6" data-testid="tenants-title">Тенанты</h1>
            <ProvisioningWizard session={session} accessSection="tenants" />
        </div>
    );
}
