# Immortal Guard X

Independent legal reward/opportunity intelligence platform.

## Current engine
- Public feed radar every 5 minutes via GitHub Actions.
- Opportunity normalization, deduplication, scoring, risk classification and history.
- Live dashboard reads data/opportunities.json.
- Owner-approval queue for reviewed opportunities.
- TON Connect address connection plus owner-approved TON transfer requests; the Guard never holds keys or signs/transfers automatically.
- Security blocks for seed/private-key requests, forced-payment patterns, CAPTCHA/KYC bypass and Sybil/fake-account language.
- No guaranteed earnings.

## AI architecture
Astra = coordinator, Claude = critique/review, Immortal Guard = final security control. The roles are not represented as live AI API calls until credentials/integrations are deliberately connected.

## Automation boundary
The radar can discover and rank public candidates. It does not automatically claim rewards, sign transactions, or move funds. A transfer request can be prepared only for the owner's connected temporary wallet and must be approved in that wallet. No bypasses or wallet secrets are used.

See SECURITY.md for the non-negotiable safety contract.


<!-- engine pipeline refreshed -->
