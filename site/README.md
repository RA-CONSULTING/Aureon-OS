# Repository front door

Reading copy for strangers. It is not the company homepage and it is not a live deploy.

- Applicant: R&A Consulting and Brokerage Services Ltd, NI696693, trading as Aureon Zorza Technologies
- Company homepage: https://aureonzorzatechnologies.pl
- The live routes are active. With exchange keys in `.env`, the launcher boots into live trading. There is no verified live track record.
- Guarded smoke: `./install.sh --smoke` (does not read `.env`; live trading off for that run)
- License: MIT, file `LICENSE` at the repository root
- Go-live: HOLD. This checkout is never production ready and never a validated deployment.

`website/` is the Home.pl site source. `public/` is repository assets. `netlify/functions/` is function source. None of those is turned on by this folder.

GitHub Pages is off. `.github/workflows/pages-gated.yml` is dispatch-only. The upload job stays skipped unless Gary sets repository variable `AUREON_PAGES_DEPLOY` to `gary-yes` and dispatches with confirm `GARY-YES-DEPLOY-PAGES`. This folder does not enable the Pages feature. Do not add a CNAME, a push trigger, or a claim that Pages serves the company homepage.

Open `index.html` for the page.
