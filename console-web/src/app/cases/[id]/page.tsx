import InboxView from "@/components/InboxView";

export default async function CasePage({
    params,
    searchParams,
}: {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ panel?: string }>;
}) {
    const { id } = await params;
    const { panel } = await searchParams;
    const initialSidePanel = panel === "bookings" || panel === "details" ? panel : null;

    return <InboxView initialCaseId={id} initialSidePanel={initialSidePanel} />;
}
