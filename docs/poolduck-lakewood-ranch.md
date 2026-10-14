# Pool Duck — landing pages de anúncio de Wesley Chapel → Lakewood Ranch (14/10)

Outra agência (GHL white-label `portal.poolduck.com`, company `yDnTmXSiDo0egbt77IY2`, 10 sub-contas).
Token Firebase próprio, fora do repo (`set -a; . <poolduck.env>; set +a` antes dos scripts; o
`.env` do repo continua sendo o da Pool Profits). Dumps em `dump/poolduck/` (`GHL_DUMP_DIR`).

- Origem: **Pool Duck Wesley Chapel** `uJr8H2qaQM5ffZxeYFqn`, pasta de funis "Ad Landing Pages".
- Destino: **Pool Duck Lakewood Ranch** `MosKIX4oux96vchwHZ5W` (941-588-2227).

## Feito

| O quê | Lakewood Ranch |
|---|---|
| Funil "Love Us Free, Hate Us Free" (Google) | `KVsiYlxVtBTUKYzRVkNt` → lakewoodranchflorida.poolduck.com/google-landing-page e /fb-thank-you-171844 |
| Funil "Love Us Free, Hate Us Free - FB" | `zfqO82ZBuj0LYBcAuel6` → /fb-promo e /fb-thank-you |
| Pasta de funis | "Ad Landing Pages" |
| Form "Google AdWords" | `L35gq3SnSDyoda4Kl9D4` (cópia da versão atual do WC; redireciona para /fb-thank-you-171844) |
| Form "Facebook Leads" | `331LWSK5w0JSbZFswx4q` (idem; redireciona para /fb-thank-you; sem o Pixel do WC) |
| Workflows (pasta "Ad Landing Pages") | Google AdWords / Facebook - Qualified Lead (Form Fill) **publicados**; (Call In) **draft sem gatilho** |
| Tags | `new lead`, `google adwords`, `fb leads`, `form fill`, `call in`, `lakewood ranch` |

Páginas: clonadas com o "clone to sub-account" do GHL (mesmo design/estrutura) e localizadas por
`scripts/pd_lwr_pages.py`: forms do LWR (inline e popup), telefone principal do LWR, "POOL DUCK
LAKEWOOD RANCH", "Pasco County" → Lakewood Ranch (a frase dos 15 anos virou "Over 15+ years of
pool service experience!" para não afirmar 15 anos em LWR), áreas atendidas, mapa (imagem nova,
link para o Google "Pool Duck of Lakewood Ranch"), "Centrally Located in Lakewood Ranch, FL", título
e descrição SEO. Reviews do WC (widget Trustindex do WC + depoimento Dennell M. + selos) ocultos.
Códigos de rastreamento (Google Ads/GTM/Meta Pixel) não foram copiados (decisão do cliente).

Workflows: espelho dos do WC com pipeline/etapa do LWR ("Leads --> Sales Pipeline" / Lead),
alerta SMS para **Kenton Dashiell (941-241-7595) e Pool Duck Service (941-549-3125 — no CRM é o
celular do Ricky)**, textos "Pool Duck Lakewood Ranch", tag `lakewood ranch` além de fonte +
meio. Sem os passos "Add to Google Ads" / "Meta Conversion API" até o LWR ter as contas.
SMS para o lead do FB: "Hi {{contact.first_name}}, this is Pool Duck in Lakewood Ranch…".

## Testes (14/10)

- Páginas ao vivo (navegador): sem nenhum texto de WC, forms do LWR carregando (inline e popup),
  título certo, sem Trustindex; mapa e áreas novos.
- Workflows rodados em 2 contatos de teste ("TEST - Pool Duck setup (… please ignore)", sem
  telefone): tags e card certos na pipeline do LWR; **alertas SMS entregues** (status delivered)
  para Kenton e para o 941-549-3125. Os 2 contatos/cards de teste ficaram para revisão do cliente.
- Envio do form: bloqueado por Cloudflare Turnstile para navegador automatizado (proteção legítima;
  não contornar) → teste manual (abaixo).
- Ligação: sem números de rastreamento no LWR ainda → teste depois (abaixo).

## Pendências (Pedro / cliente)

1. **Teste manual do form (1 min cada)**: abrir /google-landing-page e /fb-promo, enviar com dados
   de teste → deve cair no LWR com as tags, card em Lead e SMS para Kenton e 941-549-3125.
2. **Números de rastreamento** (cliente vai comprar, um Google e um Facebook, no LWR): depois,
   (a) nos 2 workflows "(Call In)" adicionar gatilho *Call Status → inbound, In phone number = número*
   e publicar; (b) trocar 941-588-2227 pelos números nas páginas (rodar `pd_lwr_pages.py` com o
   mapeamento novo); (c) ligar para cada número e conferir tags/card.
3. **Rastreamento de anúncios**: quando o cliente mandar Google Ads/GTM/Pixel do LWR, colocar nos
   funis e recolocar os passos de conversão nos workflows.
4. **Reviews**: criar o widget Trustindex do LWR (Google "Pool Duck of Lakewood Ranch") e reexibir a
   seção de reviews.
5. **Conferir com o cliente**: lista "Areas We Serve" (34202, 34211, 34212, 34240 / Lakewood Ranch /
   Bradenton / Sarasota / Manatee & Sarasota Counties) e horários (mantidos os do WC).
6. Apagar os 2 contatos/cards "TEST - Pool Duck setup" depois da revisão.
7. Fora do escopo, para avisar: os alertas de lead que o LWR já tinha ("… - Steve") não têm
   destinatário e atribuem a um usuário que não existe na conta. No WC, o popup do form está
   configurado com o form "Poolfessionals AdWords" de **outra empresa**; ao vivo aparece o form do
   WC, mas vale reselecionar o form do WC no popup para não arriscar.

## API do GHL (funis) — verificado ao vivo

- Clonar funil para outra sub-conta: `POST backend /funnels/funnel/clone-funnel-to-locations
  {funnelId, funnelName, locationIds}` (assíncrono, ~10 s). Não copia forms: **todo elemento de form
  vira `formId: "none"`**; não copia domínio nem códigos de rastreamento do funil.
- Corpo da página: JSON em `page.pageDataDownloadUrl` (`GET backend /funnels/page/{id}`).
  Salvar: `POST backend /funnels/builder/autosave/{pageId}` com `{funnelId, pageData, pageVersion,
  pageType: "live", manualSave: true, integrations, meta}`. **Sem `pageType: "live"` vira só
  rascunho** (Redis) e a página não muda. Live mantém o `pageVersion`.
- Domínio do funil: `POST backend /funnels/funnel/update-settings` (corpo do app de funis).
  Pastas: `/funnels/funnel/folder/create|list`, mover: `/funnels/funnel/move {folderId, funnelId,
  locationId, userId}`.
- Imagem na mídia da conta: `POST services /medias/files/ {name, contentType, parentId, altType,
  altId, size}` → PUT no `url` assinado → `POST services /medias/files/verify {altId, altType, id}`.
- Elementos (seção/linha/coluna/elemento) escondem com `extra.visibility.value.hideDesktop/hideMobile`.
