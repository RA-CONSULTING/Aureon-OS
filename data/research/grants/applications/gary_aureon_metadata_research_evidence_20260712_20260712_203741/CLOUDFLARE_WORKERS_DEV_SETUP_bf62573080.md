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

## 3. Zapisz token i account id lokalnie

W `.env` projektu dodaj:

```env
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_ACCOUNT_ID=...
```

Skąd wziąć `CLOUDFLARE_ACCOUNT_ID`:
- Dashboard -> `Workers & Pages` -> Settings/Account details
- lub API:
  `curl -H "Authorization: Bearer <TOKEN>" https://api.cloudflare.com/client/v4/accounts`

## 4. Bootstrap i deploy

```bash
cd ~/CodexPROsSparrow
bash scripts/workers_dev_bootstrap.sh
bash scripts/workers_dev_bootstrap.sh --deploy
```

## 5. URL aplikacji po deployu

Po udanym deployu:
- `https://codexprosparrow.<twoj-subdomain>.workers.dev`

## 6. Limity free plan (ważne)

- Workers Free: limity dzienne requestów i CPU.
- Workers AI: darmowa pula dzienna neuronów, potem wymagany plan płatny.

Dokumentacja:
- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/workers-ai/platform/pricing/
