import CaseView from "@/components/CaseView";
import LoginButton from "@/components/LoginButton";
import Link from "next/link";

export default async function CasePage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;

    return (
        <div className="grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-body)]">
            <main className="flex flex-col gap-8 row-start-2 items-center sm:items-start w-full max-w-6xl h-full">
                <div className="flex justify-between w-full items-center">
                    <div className="flex gap-4 items-center">
                        <Link href="/" className="text-blue-500 hover:underline">
                            ← Назад к заявкам
                        </Link>
                        <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)]">
                            Детали заявки
                        </h1>
                    </div>
                    <LoginButton />
                </div>

                <div className="w-full h-full bg-white rounded-lg shadow-sm border p-6">
                    <CaseView caseId={id} />
                </div>
            </main>
        </div>
    );
}
