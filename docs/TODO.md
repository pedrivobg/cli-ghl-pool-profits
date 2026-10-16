# TODO — só o que está pendente (16/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`.

## Agora

1. **Pool Keepers — linha 805-262-9070 não conecta** (Frank e você testaram). Encaminhamento certo; a
   ligação nem chega ao GHL. **Você abre chamado no suporte** (número, horários dos testes, erro "Trial
   mode not enabled for this agency" nos SMS de 07/10, telefone com rebilling). Resolvido → Frank testa.
2. **Stay Fresh — campanha de SMS** pronta em rascunho (texto do Mike sem alteração, 105 clientes,
   respostas avisam o Mike). Falta o Frank dizer **dia e hora** → eu rodo `pp_sms_campaign.py launch --confirm`.
3. **Chatbot (Atif)**: mandar para ele as 2 URLs de webhook (contas de teste "Test Snapshot" e "test
   inc", já testadas) e o formato do JSON — mensagem pronta no chat de 16/10. Decidir se ele ganha
   usuário nessas 2 contas para ver os leads (hoje ele recebe por e-mail).
4. **Bluewater (Bill)**: perguntar onde fica o GHL dele (não está na Pool Profits nem na Pool Duck —
   pista: Sharon Burch) e pedir pedro@poolprofits.com como Admin. Com acesso: 3 webhooks (calculadora,
   Seller's/Buyer's Guide) com tags, SMS de confirmação só com checkbox, calendário no lugar do Calendly.
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

## Decisões

11. **Master do snapshot**: corrigir (3 etapas Won e bugs antigos) e dar Refresh em Agency → Account
    Snapshots — só você libera.
12. **SMS com a linha rastreada** nas outras contas, como na Pool Shack (Southern: 214-308-1744 → 922-1914).
13. **Tag por linha** (`website & gbp`, `facebook`) nas contas que ainda não têm (`pp_line_tag.py`).
14. **Sunwave**: ligação da linha Adwords ganhar `adwords` + conversão (publicar AdWords Call In)?
    Avisar a Val: sunwavepoolpros.com redireciona para um domínio que não existe; no Zap do lead form,
    trocar a tag "website form fill".
15. **BluVantage**: bloquear no IVR quem tem tag `spam` (precisa do OK do cliente + ligação de teste).
16. **Passion**: os forms "PPC - … Quote" do site recebem anúncio? Se sim, entra a parte de Ads.
17. **Paid Ads** na Bahama, Passion e Pool Shack: rodam Ads para a landing `go.*`? Se não, draft.
18. **Limpeza**: drafts antigos da Stay Fresh (AdWords Tracking ×2, Won Customer, Pool Smart OC) e o
    "Sequential Call Routing" (IVR da BluVantage copiado em Southern, Passion, Bahama, Pool Shack, master).
19. **A2P da Pool Keepers** (Settings → Phone System → Trust Center). **Kari** (Southern): Won certo?

## Pool Duck — detalhes em `docs/poolduck-lakewood-ranch.md`

20. Campanha de review do LWR: aprovou → `pd_lwr_reviews.py launch`; confirmar os 2 McQuaid.
21. Landing pages LWR: teste manual do form, números de rastreamento, IDs de Ads/Pixel, Trustindex, áreas;
    apagar os 2 contatos de teste. Avisar: alertas antigos "… - Steve" sem destinatário; popup do WC.
