import LoginButton from "@/components/LoginButton";
import CaseList from "@/components/CaseList";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import Link from "next/link";

export default async function Home() {
  const session = await getServerSession(authOptions);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-bold">Truffles Console</h1>
            {session && (
              <nav className="flex gap-4 text-sm">
                <Link href="/" className="text-blue-600 hover:underline font-medium">
                  Заявки
                </Link>
                <Link href="/calendar" className="text-gray-600 hover:text-blue-600">
                  Записи
                </Link>
                <Link href="/ops" className="text-gray-600 hover:text-blue-600">
                  Статус
                </Link>
                <Link href="/audit" className="text-gray-600 hover:text-blue-600">
                  Журнал
                </Link>
                <Link href="/settings" className="text-gray-600 hover:text-blue-600">
                  Настройки
                </Link>
              </nav>
            )}
          </div>
          <LoginButton />
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {session ? (
          <CaseList />
        ) : (
          <div className="text-center py-16">
            <h2 className="text-3xl font-bold mb-4">Панель управления AI‑ассистентом</h2>
            <p className="text-gray-600 mb-8">
              Войдите в систему для управления заявками и мониторинга.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
