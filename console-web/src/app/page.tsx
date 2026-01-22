import LoginButton from "@/components/LoginButton";
import CaseList from "@/components/CaseList";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import Image from "next/image";
import Link from "next/link";

export default async function Home() {
  const session = await getServerSession(authOptions);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header
        className="sticky top-0 z-10 border-b border-border/60 bg-background/80 backdrop-blur"
        data-testid="console-header"
      >
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <Image
                src="/brand/truffles-logo.png"
                alt="Truffles"
                width={140}
                height={40}
                className="h-7 w-auto"
                data-testid="console-logo"
                priority
              />
              <span
                className="text-xs uppercase tracking-[0.3em] text-muted-foreground hidden sm:inline"
                data-testid="console-title"
              >
                Truffles Console
              </span>
            </div>
            {session && (
              <nav className="flex gap-4 text-sm font-medium text-muted-foreground">
                <Link
                  href="/"
                  className="text-foreground hover:text-foreground"
                  data-testid="nav-cases"
                >
                  Заявки
                </Link>
                <Link href="/calendar" className="hover:text-foreground" data-testid="nav-calendar">
                  Записи
                </Link>
                <Link href="/ops" className="hover:text-foreground" data-testid="nav-ops">
                  Статус
                </Link>
                <Link href="/audit" className="hover:text-foreground" data-testid="nav-audit">
                  Журнал
                </Link>
                <Link href="/settings" className="hover:text-foreground" data-testid="nav-settings">
                  Настройки
                </Link>
              </nav>
            )}
          </div>
          <LoginButton />
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-8" data-testid="console-main">
        {session ? (
          <CaseList />
        ) : (
          <div className="text-center py-16">
            <h2 className="text-3xl font-bold mb-4">Панель управления AI‑ассистентом</h2>
            <p className="text-muted-foreground mb-8">
              Войдите в систему для управления заявками и мониторинга.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
