# Immortal Guard Security Contract

## Hard rules
- Never request, store, transmit, or log seed phrases or private keys.
- Never bypass CAPTCHA, KYC, eligibility controls, rate limits, Sybil controls, or identity checks.
- Never sign blockchain transactions automatically.
- Never claim rewards automatically.
- Never transfer funds automatically.
- A wallet connection is for address visibility/receivable workflows only; authorization remains with the owner.
- Suspicious reward instructions are blocked or sent to review.

## Decision pipeline
1. Public-source collection
2. Candidate normalization and deduplication
3. Risk/score heuristics
4. Astra coordinator layer
5. Claude review layer
6. Gemini verification layer
7. Immortal Guard final security gate
8. Owner-approval queue
9. Manual owner action only

The current repository implements steps 1–3, the safety gate, dashboard feed, history and owner-approval queue. AI model calls are intentionally not faked: Astra/Claude/Gemini are declared as architecture roles until their authenticated APIs are connected.
