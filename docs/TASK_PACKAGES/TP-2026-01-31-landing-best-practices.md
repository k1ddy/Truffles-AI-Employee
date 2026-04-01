# TP-2026-01-31 — truffles.kz landing best practices

- Название/цель (1–2 предложения)
  - Улучшить best practices лендинга truffles.kz по performance, SEO, accessibility, security headers, оптимизации логотипа, содержимому /subprocessors и аналитике CTA без изменения структуры основного лендинга.
- Canon refs (owner‑doc + STATE.md NOW/GAP)
  - `STATE.md` (NOW: landing perf fix; NEW GAP: best practices)
  - `STRUCTURE.md` (процесс), `STRATEGY/REQUIREMENTS.md` (качество)
  - `/home/zhan/infrastructure/docker-compose.yml` (website service)
- Invariant
  - Контент секций/CTA/якоря не меняются (кроме легальной страницы /subprocessors).
  - Без новых внешних зависимостей и без backend/console изменений.
  - Визуальная айдентика сохраняется.
- Scope
  - Performance: preload/preconnect шрифтов, lazy/decoding для нижних изображений, reduced‑motion поведение.
  - SEO: корректные meta/OG/Twitter, canonical, sitemap/robots.
  - Accessibility: skip‑link, aria для mobile menu.
  - Security/ops: базовые security headers + gzip + cache‑policy для assets.
  - Assets: оптимизация логотипа + webp fallback.
  - Legal: заполненный список субобработчиков на /subprocessors.
  - Analytics: GA4 wiring (env‑based) + CTA tracking + UTM capture.
  - Icons: favicon на базе логотипа Truffles.
- Out of scope
  - Редизайн, новая структура секций, новые страницы продукта (кроме /subprocessors).
  - Внедрение серверной аналитики/бекенд‑событий.
- Touch-list (files/tables)
  - `/home/zhan/infrastructure/frontend/index.html`
  - `/home/zhan/infrastructure/frontend/public/robots.txt`
  - `/home/zhan/infrastructure/frontend/public/sitemap.xml`
  - `/home/zhan/infrastructure/frontend/public/og-truffles.svg`
  - `/home/zhan/infrastructure/frontend/public/favicon.ico`
  - `/home/zhan/infrastructure/frontend/src/index.css`
  - `/home/zhan/infrastructure/frontend/src/main.tsx`
  - `/home/zhan/infrastructure/frontend/src/App.tsx`
  - `/home/zhan/infrastructure/frontend/src/lib/analytics.ts`
  - `/home/zhan/infrastructure/frontend/src/components/landing/Navbar.tsx`
  - `/home/zhan/infrastructure/frontend/src/components/landing/FooterSection.tsx`
  - `/home/zhan/infrastructure/frontend/src/components/landing/ScrollReveal.tsx`
  - `/home/zhan/infrastructure/frontend/src/components/landing/HeroBackground.tsx`
  - `/home/zhan/infrastructure/frontend/src/components/landing/AnimatedCounter.tsx`
  - `/home/zhan/infrastructure/frontend/src/components/landing/HeroChatPreview.tsx`
  - `/home/zhan/infrastructure/frontend/src/components/FloatingWhatsApp.tsx`
  - `/home/zhan/infrastructure/frontend/src/components/StubPage.tsx`
  - `/home/zhan/infrastructure/frontend/src/pages/Index.tsx`
  - `/home/zhan/infrastructure/frontend/src/pages/Subprocessors.tsx`
  - `/home/zhan/infrastructure/frontend/src/assets/truffles-logo.png`
  - `/home/zhan/infrastructure/frontend/src/assets/truffles-logo.webp`
  - `/home/zhan/infrastructure/frontend/nginx.conf`
  - `docs/SESSIONS/SESSION-2026-01-31-landing-perf-a4.md`
  - `docs/SESSION_INDEX.md`
- Plan (1..N)
  1) Обновить HTML meta/OG/Twitter, canonical, lang, preconnect/preload fonts.
  2) Перенести font import из CSS и добавить reduced‑motion поведение в анимациях.
  3) Добавить skip‑link и aria для mobile menu.
  4) Обновить robots.txt, добавить sitemap.xml и OG asset.
  5) Добавить security headers + gzip + cache policy в nginx.conf.
  6) Оптимизировать логотип (png/webp), обновить img/picture и размеры.
  7) Наполнить /subprocessors списком из канона.
  8) Добавить GA4 wiring (env) + CTA tracking + UTM capture.
  9) Пересобрать сайт и перезапустить контейнер.
  10) Проверить доступность `https://truffles.kz`.
- DoD
  - Ленд отвечает 200, сборка проходит.
  - Meta/robots/sitemap доступны, skip‑link и aria присутствуют.
  - Security headers/gzip/cache включены.
  - Логотип оптимизирован, webp fallback работает.
  - /subprocessors содержит список.
  - Analytics wiring включён и не ломает без env.
- Checks
  - `npm --prefix /home/zhan/infrastructure/frontend run build`
  - `docker compose -f /home/zhan/infrastructure/docker-compose.yml build website`
  - `docker compose -f /home/zhan/infrastructure/docker-compose.yml up -d website`
  - `curl -I https://truffles.kz`
- Evidence
  - `/tmp/landing_bestpractices_build_*.txt`
  - `/tmp/landing_bestpractices_docker_build_*.txt`
  - `/tmp/landing_bestpractices_docker_up_*.txt`
  - `/tmp/landing_bestpractices_curl_*.txt`
- Rollback
  - Вернуть файлы из `/tmp/landing-perf-backup/` и пересобрать контейнер.
- No-go
  - Не менять текст/структуру секций и ссылки.
  - Не добавлять серверные зависимости/аналитику без согласования.
- Branch + Worktree path + Base ref + Merge policy + Cleanup
  - branch: `feat/2026-01-31-landing-perf-a4`
  - worktree: `/home/zhan/worktrees/2026-01-31-landing-perf-a4`
  - base: `origin/main`
  - merge policy: merge only (no rebase)
  - cleanup: удалить worktree/branch после закрытия (Brain/Architect)
- Риски/блокеры
  - Нет git-репозитория для `/home/zhan/infrastructure/frontend` → откат только через локальный backup.
