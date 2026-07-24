# Instrukcja wgrania strony na home.pl

## Co zawiera paczka

Paczka `paczka Home.pl website Gary Luciferson.zip` zawiera kompletną statyczną stronę Aureon Zorza / Project Envision przygotowaną z publicznego commita:

`f21fbdbca1d2eb26f2080f3c2f26733ac9d93794`

W paczce znajdują się gotowe do serwowania pliki HTML, CSS, JavaScript, JSON, SVG i WebP. Hosting nie musi uruchamiać Node.js, npm, Pythona, Git, bazy danych ani procesu budowania. Plik `.htaccess` nie jest potrzebny do działania tej wersji.

## Najważniejsza zasada struktury

Do katalogu dokumentów domeny należy wgrać **zawartość ZIP-a**, a nie dodatkowy katalog opakowujący.

Po wgraniu struktura musi zaczynać się tak:

```text
index.html
styles.css
script.js
robots.txt
sitemap.xml
assets/
data/
projects/
updates/
contact/
...
```

Plik `index.html` musi znajdować się bezpośrednio w katalogu przypisanym domenie. Niepoprawna struktura to na przykład `katalog-domeny/paczka Home.pl website Gary Luciferson/index.html`.

## 1. Zrób kopię poprzedniej strony

Przed wgraniem:

1. Otwórz menedżer plików hostingu home.pl albo połącz się swoim klientem FTP.
2. Ustal w panelu, który katalog jest katalogiem dokumentów wybranej domeny.
3. Pobierz istniejące pliki na komputer albo utwórz ich archiwum w panelu.
4. Zanotuj datę kopii i nie usuwaj jej przed zakończeniem testów nowej strony.

Nie zakładaj nazwy katalogu domeny na podstawie tej instrukcji — użyj katalogu wskazanego w konfiguracji hostingu.

## 2. Wgranie przez menedżer plików home.pl

Jeżeli panel potrafi rozpakować ZIP:

1. Przejdź do katalogu dokumentów domeny.
2. Wgraj `paczka Home.pl website Gary Luciferson.zip`.
3. Rozpakuj archiwum w tym katalogu.
4. Sprawdź, czy `index.html` leży bezpośrednio w katalogu domeny.
5. Jeżeli panel utworzył dodatkowy folder, przenieś jego **zawartość** o jeden poziom wyżej.

Jeżeli panel nie potrafi rozpakować ZIP:

1. Rozpakuj ZIP lokalnie na komputerze.
2. Zaznacz wszystkie pliki i foldery znajdujące się wewnątrz archiwum.
3. Wgraj je bezpośrednio do katalogu dokumentów domeny przez menedżer plików lub FTP.
4. Nie wgrywaj zewnętrznego folderu `paczka Home.pl website Gary Luciferson` jako dodatkowego poziomu.

## 3. Kontrola po wgraniu

Otwórz domenę w zwykłym i prywatnym oknie przeglądarki. Sprawdź co najmniej:

- stronę główną i banner z mechaniczną mrówką;
- sekcje oceanu i mechanicznych ryb;
- `/projects/` wraz z wyszukiwaniem, filtrami i sortowaniem;
- `/projects/aioa-core/`;
- `/projects/lsc-research/`;
- `/projects/aureon-trading-system/` z cyber-pszczołami;
- `/projects/epas-shield/` z guardian-bee;
- `/updates/` z datami i zielonymi punktami;
- `/contact/` oraz publiczne adresy e-mail i linki GitHub;
- widok telefonu oraz brak poziomego przewijania całej strony.

Jeżeli po podmianie widoczna jest stara wersja, wyczyść cache przeglądarki i cache hostingu/CDN, jeśli jest włączony.

## 4. Przywrócenie poprzedniej wersji

Jeżeli nowa wersja nie działa prawidłowo:

1. Nie zmieniaj DNS ani przypisania domeny.
2. Usuń lub przenieś wyłącznie pliki nowej wersji z katalogu dokumentów.
3. Przywróć wcześniej wykonaną kopię do tego samego katalogu.
4. Sprawdź, czy przywrócony `index.html` znów znajduje się bezpośrednio w katalogu domeny.

## Domena, SSL i sitemap

Przypisanie domeny, rekordy DNS i certyfikat SSL są osobnymi operacjami w panelu home.pl. Samo skopiowanie tych plików ich nie konfiguruje.

Nie podano końcowej domeny, dlatego paczka nie zawiera zgadywanych adresów canonical ani starej bazy GitHub Pages. `sitemap.xml` jest poprawnym, pustym szkieletem. Po potwierdzeniu domeny należy dodać do niego absolutne adresy HTTPS i dopiero wtedy dopisać w `robots.txt` linię `Sitemap:` z prawdziwym adresem. Nie wpływa to na działanie strony po uploadzie.

## Integralność paczki

Przed wgraniem porównaj SHA-256 ZIP-a z plikiem `HOMEPL_PACKAGE_MANIFEST.txt` umieszczonym obok archiwum na Pulpicie. Manifest wewnątrz ZIP-a nie może wiarygodnie zawierać sumy kontrolnej archiwum, którego sam jest częścią; ostateczna suma znajduje się w kopii manifestu obok ZIP-a.

W tej instrukcji nie ma i nie powinno być żadnych haseł, tokenów, kluczy FTP ani SSH.

## Automatyczny build i deploy (opcjonalnie) — Automated build & deploy (optional)

Ta ręczna procedura nadal działa bez zmian. Dostępne jest też powtarzalne narzędzie w
`scripts/website/` (czysta biblioteka standardowa Pythona), które audytuje stronę, buduje paczkę
home.pl (ZIP + suma SHA-256) i — opcjonalnie — wysyła ją przez FTP(S). Dane logowania FTP są
czytane **wyłącznie ze zmiennych środowiskowych** i nigdy nie są zapisywane w repozytorium.

The manual steps above still work unchanged. A repeatable helper also lives in
[`scripts/website/`](../scripts/website/README.md): it audits the site, builds the home.pl package
(ZIP + SHA-256), and can upload it over FTPS. FTP credentials are read **only from environment
variables** and are never committed.

```bash
python -m scripts.website.audit_site
python -m scripts.website.build_package --out dist
python -m scripts.website.ftp_deploy --package dist/website_package --dry-run
```
