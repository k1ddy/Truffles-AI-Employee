import InboxView from "@/components/InboxView";

export default async function CasePage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;

    return <InboxView initialCaseId={id} />;
}
