# TODO — só o que está pendente (19/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`.

## Agora

1. **Pool Keepers — linha 805-262-9070 encaminha para ela mesma** (desde 10/10; por isso toca 1× e cai —
   o registro de 15/10 estava errado: 805-457-8212 é o telefone da empresa, não o encaminhamento). Sem API:
   Settings → Phone Numbers → 805-262-9070 → Edit → *Forward calls to* = **+1 805-457-8212** → salvar → ligar
   para testar (me avisa que eu confiro o registro). Chamado no suporte só se continuar caindo.
2. **Stay Fresh — campanha enviada** (19/10, 105): avisar o Frank. Respostas vão para o Mike; quem
   responder ganha `drain wash interested` (inclui o "Stop"). Depois de alguns dias, passar os 2 workflows
   "Drain & Wash Campaign" para draft.
3. **Chatbot (Atif)**: do nosso lado (GHL) está pronto — 2 webhooks enviados em 16/10. Ele pediu login do
   WordPress dos 3 sites (backend do chatbot + 2 fictícios), que não são nossos (você não tem acesso) →
   respondido devolvendo para o Frank / quem criou os sites.
4. **BurchTech Solutions (GHL do Bill)** — acesso no Basecamp; lá ficam a **Bluewater** e a **Pool Keepers**
   (decidido 19/10: o snapshot da Pool Profits vai para a BurchTech). Passos:
   a) Acesso por API para mim: entrar com o login do Basecamp e tirar o refresh token
      (`docs/get-firebase-token.md`, arquivo de env separado como na Pool Duck) — ou pedir pedro@poolprofits.com
      como admin da agência BurchTech.
   b) Snapshot (só na UI; a API de snapshots não aceita o token): Agência Pool Profits → Account Snapshots →
      Create → a partir da sub-conta **The Pool Keepers** (tem as correções; o master V9 ainda tem os bugs
      do item 11) → Share → link → na BurchTech: Account Snapshots → Imported → colar o link → carregar na
      sub-conta da Pool Keepers (e o que servir na Bluewater).
   c) Não viajam no snapshot (eu refaço/confiro com acesso): usuários nos avisos internos, número de telefone
      + A2P (o 805-262-9070 é da Pool Profits — portar = chamado), domínio go.thepoolkeepers.company (DNS
      para a BurchTech), integrações Google/Facebook, equipe dos calendários, custom values.
   d) Na Pool Keepers de cá há 3 funis "… - Simple Pool Care" (cópias de outra conta) — limpar antes do snapshot.
   e) Bluewater, com acesso: 3 webhooks (calculadora, Seller's/Buyer's Guide) com tags, SMS de confirmação
      só com checkbox, calendário no lugar do Calendly.
5. **Trocar os 2 refresh tokens** colados no chat (Pool Profits e Pool Duck) — `docs/get-firebase-token.md`.

## Testes da equipe

6. **Southern** (Val): teste final do form e de uma ligação no 972-632-3259; conversão na página
   https://service.southernpoolandoutdoors.com/ty-page-2934-3692. Se o builder da landing estiver aberto,
   recarregar antes de salvar (o form mudou para GOOGLE ADS - FORM).
7. **Sunwave** (Val): reenviar o form da landing e conferir tags/card/SMS dos Connolly.
8. **IVR da Southern**: ligar no (214) 922-1914 (1 → Brett; 2 → 214-308-1744; sem resposta → caixa postal).
9. **Orange Tree**: no próximo lead/SMS de cliente, a Vanessa confirmar o e-mail (com fotos). Para voltar
   a receber avisos por SMS, ela manda START para 623-343-0400 e 623-244-8621.
10. **BluVantage**: na próxima submissão, ver se aparece na conversa e o e-mail chega para Vanessa e Paul.
10b. **Passion**: no próximo lead do site ou da linha Website & GBP (629-247-6255), conferir se o e-mail
    chegou em passionpoolcare@gmail.com (procurar também no spam).
10c. **Teste do Google Lead Form (você, na UI)** — Reign, Damon's, Simple, form "Weekly Pool Service Done
    Right". Até 20/10 nenhum lead entrou (0 contatos com `google lead form`; Sunwave idem desde 07/10).
    (1) GHL da sub-conta → Settings → Integrations → Google Ads → Manage: o form está mapeado (Map Fields:
    nome, telefone, e-mail, CEP) e **Active**? Se não, Play → Map Fields → ativar. (2) Google Ads → campanha
    → Lead form → Edit → abrir o form → **Send Data**. Me avisa → eu confiro contato, tags, card e SMS e apago o
    teste. O SMS "NEW LEAD" do teste chega no Stephen/Damon/Nathan.
10d. **Ligações de teste (você)**: Wrigley's linha LSA 925-744-7750 (a do Google Ads já foi conferida com
    ligação real: Aaron Jones, tags + card ok) e Pool Duck LWR 941-541-5942 (ver quem atende). Sunwave e
    Passion já conferidos com tráfego real (`pp_source_check.py`).
## Decisões

11. **Master do snapshot**: corrigir (3 etapas Won e bugs antigos) e dar Refresh em Agency → Account
    Snapshots — só você libera.
12. **SMS com a linha rastreada** nas outras contas, como na Pool Shack (Southern: 214-308-1744 → 922-1914).
13. **Tag por linha** (`website & gbp`, `facebook`) nas contas que ainda não têm (`pp_line_tag.py`).
14. **Sunwave**: conversão do Google Ads nas ligações da linha Adwords (a tag já entra)? Avisar a Val:
    sunwavepoolpros.com redireciona para um domínio que não existe; no Zap do lead form, trocar a tag
    "website form fill" (aí os forms do site, hoje `website form`, podem voltar a `website form fill`).
    Número "Angi's Leads" só recebe spam para a dona anterior — trocar o número?
14b. **Wrigley's**: ligações do AdWords e do LSA sem o SMS de follow-up que a GBP manda — incluir?
15. **BluVantage**: bloquear no IVR quem tem tag `spam` (precisa do OK do cliente + ligação de teste).
16. **Passion**: os forms "PPC - … Quote" do site recebem anúncio? Se sim, entra a parte de Ads. A linha
    "Secondary" (629-324-1486) continua sem aviso — serve para quê?
17. **Paid Ads** na Bahama, Passion e Pool Shack: rodam Ads para a landing `go.*`? Se não, draft.
18. **Limpeza**: drafts antigos da Stay Fresh (AdWords Tracking ×2, Won Customer, Pool Smart OC) e o
    "Sequential Call Routing" (IVR da BluVantage copiado em Southern, Passion, Bahama, Pool Shack, master).
19. **A2P da Pool Keepers** (Settings → Phone System → Trust Center). **Kari** (Southern): Won certo?

## Pool Duck — detalhes em `docs/poolduck-lakewood-ranch.md`

20. Campanha de review do LWR: aprovou → `pd_lwr_reviews.py launch`; confirmar os 2 McQuaid.
20b. Número do Google Ads do LWR (941-541-5942) já ligado ao workflow e às páginas do Google (20/10) — falta a
    ligação de teste (10d).
21. Landing pages LWR: teste manual do form, números de rastreamento, IDs de Ads/Pixel, Trustindex, áreas;
    apagar os 2 contatos de teste. Avisar: alertas antigos "… - Steve" sem destinatário; popup do WC.
