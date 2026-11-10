# SOP A2P 10DLC (Pedro, 10/11) — o que `pp_new_account.py` / `pp_a2p.py` seguem

Fonte: SOP "Submissão A2P 10DLC" (Fulfillment / Onboarding). Revisão manual das operadoras: a causa nº 1 de rejeição é
divergência entre o que foi enviado e o que está no ar no site.

## Antes (Fases 1–2)
- Custom values: A2P Verification Number = número principal comprado; Business Address (igual ao do EIN); Business Email
  (de domínio, não Gmail, quando houver); Friendly Business Name; Legal Business Name (exato do EIN); Logo URL (abre direto em
  janela anônima — o script testa); Privacy Policy e Terms of Use.
- Três números por cliente (linhas Website & GBP = principal, Google Ads, Facebook Ads).
- Subdomínio `go.<domínio>` → site **New A2P Verification**. As páginas abrem na **raiz** do subdomínio, sem `/pools`
  (Southern: `/privacy-policy` 200, `/pools/privacy-policy` 404): `https://go.<domínio>`, `/contact-us`, `/privacy-policy`,
  `/terms-of-use` — minúsculo, sem barra no fim. Conferir que carregam publicamente.
- O go. fica no site de verificação até a aprovação; só depois reapontar para o funil do Google Ads.

## Brand + Campaign (Fases 3–6)
- Brand puxa o Business Information (legal, EIN, endereço, e-mail, site, logo). Site da brand = `https://go.<domínio>`
  (como a Southern aprovada).
- Campaign: Low Volume Standard, Manual Setup, use case misto (transacional + marketing), links e telefones marcados,
  nada de age-gated/financeiro. Textos aprovados copiados EXATAMENTE (só nome legal e links mudam) — estão em
  `scripts/pp_a2p.py` (`SOP_*`). Sem merge tags nas mensagens de exemplo.
- Consentimento: Opt-in Method Website; Opt-in Form/Image `…/contact-us`; Privacy e Terms; textos de consentimento e
  opt-in message do SOP.

## Compliance e envio (Fase 7)
- Revisão de compliance por IA do GHL ("Review Application") = `GET backend /phone-system/regulatory-compliance/opt-in-form/
  validate?locationId&optInFormUrl&optInMethod=website` (SSE; evento `final` com `isCompliant`, `passedChecks/totalChecks`,
  `optInValidationId`). Só envia com `isCompliant: true`; o `optInValidationId` vai no `campaignDetails` (Southern: 23/23).

## Depois (Fase 8)
- Revisão 1–5 dias úteis; nunca prometer data ao cliente.
- Aprovado: cada número com selo verde A2P Verified (faltando → vincular o número à campanha; erro 30034). Repetir quando
  comprar número novo. Só então reapontar o go. para o funil principal.
- "A2P approval not found" nos primeiros 3–4 dias úteis é normal; passou disso → ticket no suporte com Brand ID e Campaign ID.
- Rejeitado → suporte do GHL (LC Phone); reenvio sem custo.
