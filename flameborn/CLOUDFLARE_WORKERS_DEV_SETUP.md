# Cloudflare workers.dev setup (bez własnej domeny)

## 1. Ustaw workers.dev subdomain w panelu

1. Otwórz: https://dash.cloudflare.com/
2. Wejdź w `Workers & Pages`.
3. Ustaw `Your subdomain` (np. `twojprojekt.workers.dev`).

Dokumentacja:
- https://developers.cloudflare.com/workers/configuration/routing/workers-dev/

## 2. Wygeneruj poprawny API token (dla deployu Workers)

1. Otwórz: https://dash.cloudflare.com/profile/api-tokens
2. Kliknij `Create Token`.
3. Użyj template pod Workers lub ustaw ręcznie uprawnienia:
   - `Account` -> `Workers Scripts` -> `Edit`
   - `Account` -> `Workers Routes` -> `Edit` (opcjonalnie)
   - `Account` -> `Account Settings` -> `Read` (pomaga CLI pobrać account)
4. W `Account Resources` wybierz właściwe konto (`Include` -> twoje konto).
5. Zapisz token.

## 3. Przygotuj konfigurację bez ujawniania sekretów

Przekaż wartości przez bezpieczne środowisko procesu albo prywatny, ignorowany
przez Git plik `.env`. Dokumentacja i logi mogą zawierać wyłącznie nazwy
zmiennych, nigdy ich wartości ani przykładowych sekretów:

- `CLOUDFLARE_API_TOKEN` — sekret potrzebny tylko do uwierzytelnienia CLI.
- `CLOUDFLARE_ACCOUNT_ID` — identyfikator konta.
- `AUREON_WORKER_ACCESS_SECRET` — wymagany sekret Worker, bez białych znaków na
  początku i końcu, o długości co najmniej 32 bajtów UTF-8. Skrypt go nie
  generuje, nie zapisuje i nie wypisuje.
- `AUREON_ALLOWED_ORIGINS` — wymagane, rozdzielone przecinkami dokładne originy
  HTTPS, bez końcowego ukośnika, ścieżki, wildcardu i spacji. Nazwy originów
  skopiuj z zatwierdzonego rejestru wdrożenia, nie z przykładu w dokumentacji.
- `AUREON_ALLOW_PAID_PROVIDERS` — opcjonalne. Pomiń, aby zachować tryb
  free-only. Ustaw wyłącznie literalne `true`, jeśli istnieje osobna zgoda na
  płatnych providerów.

Skąd wziąć `CLOUDFLARE_ACCOUNT_ID`:
- Dashboard -> `Workers & Pages` -> Settings/Account details
- albo przez zatwierdzony, uwierzytelniony odczyt API, który nie umieszcza
  tokenu w linii polecenia, historii powłoki ani logach.

## 4. Skonfiguruj i potwierdź stan po stronie Cloudflare

Przed wdrożeniem ustaw w panelu Cloudflare:

- sekret Worker `AUREON_WORKER_ACCESS_SECRET`;
- zwykłą zmienną Worker `AUREON_ALLOWED_ORIGINS`;
- opcjonalną zwykłą zmienną `AUREON_ALLOW_PAID_PROVIDERS` tylko jako `true`;
- oba Rate Limiting bindings z `wrangler.jsonc`:
  `API_PREAUTH_RATE_LIMITER` oraz `API_RATE_LIMITER`.

Sekret można wprowadzić interaktywnie poleceniem
`npx wrangler secret put AUREON_WORKER_ACCESS_SECRET`; nie dopisuj wartości do
polecenia, dokumentacji ani logu powłoki.

Lokalny preflight sprawdza wyłącznie konfigurację procesu i wersjonowany
`wrangler.jsonc`. Nie odczytuje stanu providera. Provider-side binding/secret
readback pozostaje **PENDING** do czasu osobnego, uwierzytelnionego odczytu z
Cloudflare; bez takiego dowodu nie wolno oznaczać wdrożenia jako zakończonego.

## 5. Preflight, bootstrap i deploy

Offline preflight (bez wywołania Wrangler i bez sieci):

```bash
cd ~/CodexPROsSparrow
npm run cf:preflight
```

Bootstrap z `--deploy` wykonuje ten sam fail-closed preflight przed pierwszym
wywołaniem Wrangler. Brak któregokolwiek wymaganego ustawienia zatrzymuje
proces przed uwierzytelnieniem i wdrożeniem.

```bash
cd ~/CodexPROsSparrow
bash scripts/workers_dev_bootstrap.sh
bash scripts/workers_dev_bootstrap.sh --deploy
```

## 6. URL aplikacji po deployu

Po udanym deployu:
- `https://codexprosparrow.<twoj-subdomain>.workers.dev`

## 7. Limity free plan (ważne)

- Workers Free: limity dzienne requestów i CPU.
- Workers AI: darmowa pula dzienna neuronów, potem wymagany plan płatny.

Dokumentacja:
- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/workers-ai/platform/pricing/
