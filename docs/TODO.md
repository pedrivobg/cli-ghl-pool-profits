# TODO do Pedro — só o que está aberto (28/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`. Testes são nossos: nada aqui vai para a equipe ou
para o cliente testar. Teste que dispara aviso para o cliente: **me avisa antes** e eu desvio os avisos.

## Pool Profits (sub-contas da nossa agência)

1. **Poolheads** (A2P aprovado: Brand + Campaign CN1AUUF; SMS "delivered" desde 23/10). Captura no ar desde 23/10:
   IVR "Business Hours Call Routing" + "After Hours Message" nas 3 linhas, Contact Created → add owner, Website & GBP
   Call - Tag, Answered Incoming, Missed New Lead (texto deles), Missed Incoming, Website Form Fill.
   - **Teste** (depois das 17h CT ou no fim de semana, quando o IVR não toca o Felipe): ligar para 936-314-9255, deixar
     recado → me avisa; eu confiro tag, SMS no seu celular e card, e apago o contato antes da tarefa de 1 h.
   - Felipe (27/10): SMS 2 do Missed New Lead tirado; ele mesmo conecta o WhatsApp.
   - **Conta antiga → nossa** (`scripts/ph_migrate_old.py`): contatos (27/10, 1.513), 5 templates de e-mail, 9 de SMS,
     16 campos, 5 forms, 5 calendários (inativos), 11 automações em draft "[Old account] …". Frank mandou o resumo ao
     Felipe (04/11) com 3 perguntas — **aguardando a resposta**:
     (a) histórico de 6 meses como nota em cada contato (~495 conversas)? (b) quem montou o webhook do "LVB - Meta
     Service" → trocar para `…/hooks/PeUynYCMm8e6PJMy785O/webhook-trigger/zxySSbrHhRqaWat6wF0i` e publicar o draft antes
     de cancelar; (c) Jorge Arias: criar usuário e pôr no IVR?
     Frank vai ver com o Jonathan pôr a conta antiga como sub-conta nossa: se der, o histórico fica lá (sem notas) e o
     webhook não se perde no cancelamento; aí o (a) pode nem ser preciso.
   - Depois do OK do Frank: publico o resto (No Response, Quote, No-Show, Lost, Won, Review…).
   - **Na tela**: Call Recording no 936-314-9255 (sem a mensagem); Felipe/Jorge no app com a conta nova; deskphone.
   - **3 landing pages de Google Ads (02/11, Val)** — `scripts/ph_ads_forms.py`: forms GOOGLE ADS – WEEKLY
     (`Xpcfh37RSgDWYHpyGzPl`), – REPAIR (`8i6m1oTeWFSanDFoNasS`), – LEAK DETECTION (`jmlPHTq3B6Cha86tKgfD`) e os 3 fluxos
     "Google Ads LP - …" no ar e testados em cópias (tags google ads / poolheads / landing page lead / serviço, card em New
     Lead, SMS + e-mail ao Felipe). Linha (936) 301-0309 entrou no IVR + "Google Ads Call - Tag". Falta:
     (a) Atif: páginas no funil do go.poolheadscare.com + 3 páginas de obrigado (/thank-you-pool-service,
     /thank-you-pool-repair, /thank-you-leak-detection) → eu rodo `ph_ads_forms.py thanks`;
     (b) Val: e-mail preferido do Felipe para os avisos (hoje felipe.cobo4@gmail.com); IDs do GTM / GA4 / conversões do
     Google Ads e conectar o Google Ads no GHL da Poolheads (conversão por form e por ligação);
     (c) ligação de teste para o 936-301-0309 e envio real de cada form (avisar o Felipe antes).
   - **Felipe vai fazer sozinho** (Frank, 30/10): criar o usuário do gerente de serviço e pôr no IVR; passar as automações
     e lembretes de calendário (confirmação por SMS para cliente avulso, separada do Skimmer). Foto de antes (30/10):
     1 usuário (Felipe); "Business Hours Call Routing" toca só o Felipe; 2 calendários inativos e sem membros;
     "Appointment Confirmation/Reminders" em draft. Quando ele avisar, eu confiro: IVR (tags de chamada perdida e recado
     intactos), calendário com membro/horário, lembretes do calendário × workflow (sem SMS em dobro), publicação.
2. **Cleverblu — A2P preenchido, não enviado** (24/10). Falta: (a) o site deles: a Privacy Policy não fala de SMS e diz
   que pode vender/compartilhar dados (precisa de "SMS opt-in data and consent will not be shared with or sold to third
   parties"); os Terms não falam de SMS (tipo, frequência, STOP/HELP, msg & data rates); a home não mostra endereço
   nem e-mail → pedir ao Frank/cliente; (b) liberar o pagamento ($22,50 uma vez + $10/mês); (c) marcar as 9
   declarações e enviar (o cadastro está salvo no GHL). Depois: ligação de teste (toca o celular do dono).
3. **Rosebrook, Blissful e WP Pools (contas novas)**: prontas no padrão (0 ALTA, 0 ERRO). Nenhuma tem número: nenhum
   SMS sai (nem o aviso para o dono). Para cada uma: **comprar um número** ("Website & GBP"; decisão sua) + A2P.
   - Rosebrook: EIN do onboarding com 8 dígitos; sem link do Google (Review Request em draft); site sem privacy.
   - Blissful: sem endereço no onboarding; site sem privacy; Brian e Jason: primeiro acesso + app; conectar o GBP.
   - WP Pools Ponds and spas (Wolbers-Possehn, Ionia MI): **telefone da Tiffany no usuário** (Settings → My Staff →
     (616) 522-2477; a API recusa); sem link do Google (Review Request em draft); Ryan (admin) e Aubrey (gerente) viraram
     usuários em 27/10: primeiro acesso dos três por "Forgot password" em app.poolprofits.com.
   - Rosebrook/Blissful/WP: os sites não têm política de privacidade → A2P precisa de site com privacy (o "New A2P
     Verification" num subdomínio deles, com o DNS do cliente). Pedir ao Frank junto com o EIN/endereço.
3b. **Bonneville Pool Maintenance (conta nova, 02/11)**: pronta no padrão (0 ALTA, 0 ERRO). Sem número na conta → nenhum
   SMS sai (nem o aviso interno). Falta: **comprar um número** ("Website & GBP"; decisão sua/Frank) + A2P (o site
   bonnevillepool.com não tem privacy/terms → "New A2P Verification" num subdomínio, DNS do cliente); conectar o Google
   Business; primeiro acesso do Justin no app; **Refresh do snapshot** (a conta nasceu da versão antiga: tirei a sobra da
   BluVantage do IVR; os 4 funis "Simple Pool Care" ainda vêm junto).
4. **Google Lead Form "Weekly Pool Service Done Right"**: workflows no ar; form mapeado e ativo em Wrigley's,
   BluVantage, Precision, Reign e Damon's. Nenhum lead chegou ainda. **Teste parado**: a conta Google do seu amigo
   (pedrolp2005@gmail.com) não acessa o Google Ads dos clientes. Os forms estão ligados a val@poolprofits.com (Wrigley's,
   BluVantage, Reign, Damon's) e dane.precision@ (Precision). Ou a Val dá acesso pela MCC 486-503-6899, ou alguém com
   acesso faz o Send Data (me avisa antes). **Simple**: a conta 258-800-5448 não mostra o form (Val diz que é essa).
5. **Pool Shack: 2 landing pages de Google Ads**. Forms "GOOGLE ADS – WEEKLY" (`mlRZlBRFVFIJjiTYiWKX`) e "GOOGLE ADS –
   REPAIRS" (`Hb5KiQHQZkGFmSgzJbIk`) + "Google Ads LP - Weekly/Repairs" no ar e testados (`scripts/ps_ads_forms.py`). Falta:
   URLs e páginas de obrigado do Atif (eu ponho a URL e ligo o redirecionamento); Google Ads conectado no GHL da Pool
   Shack (Val); números de rastreamento de ligação (decisão sua); envio real de cada form (me avisa antes).
   - Rob (03/11): só tem a nossa agência (a da Pool Monopoly, sem uso). Frank comprou os 2 números: Weekly (480) 418-1231
     e Repairs / Installs (480) 568-3370. **No ar** (`scripts/ps_ads_lines.py`, testado em cópias): "Google Ads Call -
     Weekly/Repairs" (tags, card em New Lead, SMS + e-mail + tarefa ao Rob, 1 aviso por dia por contato). "AdWords Call In -
     New Lead" (cópia da Clear Pool) e "Sequential Call Routing" (cópia da BluVantage) → draft. **Falta (você, na tela)**:
     Settings → Phone Numbers → cada número novo → encaminhar para (480) 798-2888 (sem API); depois ligar para cada um.
     Ele quer o teste da chamada perdida com a caixa postal do
     Google Voice: ligar para (480) 428-0655, não atender, deixar cair no recado → me avisa e eu confiro se o SMS saiu.
   - Site → GHL **no ar** (03/11, `scripts/ps_site.py`): os 2 forms do WPForms (440 "Request a Quote" da home, 443 "Main
     Contact / Service Form" da home e /contact/) chegam no GHL com nome, telefone, e-mail, endereço, CEP, Service Needed,
     Message / Are You A New Customer, tags `website form fill` + `new lead`, e entram no "Website Form Fill To Pipeline"
     (card New Lead, SMS + tarefa ao Rob — o mesmo de todo form). Testado do site até o GHL em cópias ZZ TEST (sem aviso).
     **Teste real (você)**: avisar o Rob antes (o SMS "NEW LEAD - Website Form" e a tarefa vão para ele) → em
     https://thepoolshackarizona.com/contact/ preencher o form com nome "ZZ Teste Pedro", seu celular e seu e-mail, Service
     Needed qualquer, marcar o consentimento, enviar; depois o "Request a Quote" da home com o mesmo nome e celular → me avisa
     e eu confiro (`ps_site.py status` = HTTP 200, contato/campos/tags, card, SMS/tarefa) e apago contato, card e tarefa.
6. **BluVantage: 3 landing pages**: forms prontos e testados (envio real quando o Atif puser nas páginas; me avisa
   antes). Números por página no ar (26/10): Weekly 470-470-8874, Repairs 470-450-6322, Winter 470-450-4427, no IVR e
   com tag/card/conversão por serviço. **Teste**: ligar fora do horário (o IVR toca a equipe no horário) para os 2 novos
   e me avisar; eu confiro tags/card e apago.
7. **Southern: SMS do Google Ads** no ar (26/10). Teste final: mandar um SMS do seu celular para (972) 632-3259 →
   me avisa antes (o aviso vai para o Brett) e eu confiro tag/card/tarefa e apago.
8. **NorTex: ligação de teste** (27/10): ligar para (469) 238-2660 e desligar durante a mensagem do IVR (não toca
   ninguém) → o SMS de chamada perdida chega no seu celular; me avisa e eu confiro a tag/card e apago antes da tarefa de 1 h.
9. **YardSpring: 3 landing pages** (27/10): forms, tags e workflows no ar e testados (`scripts/ys_ads_forms.py`).
   30/10: número das páginas (678) 448-4007 ("Google Adwords"): ligação e SMS viram lead (tags, card, conversão, SMS +
   e-mail + tarefa para o Joe; cliente atual só avisa; spam nada) — `scripts/ys_ads_line.py`, testado em cópias. O "AdWords
   Call In - New Lead" era cópia da Clear Pool (número, pipeline e texto deles) e nunca disparava: corrigido. Falta:
   30/10: Google Ads lead form "Leads Form - Google Ads" (Val integrou) → "Google Lead Form - New Lead" (tags new lead /
   new form fill / adwords, card, SMS + e-mail + tarefa ao Joe; o SMS de lead novo da conta vai para o lead), testado
   em cópias. Privacy para o Google: https://go.yardspringpools.com/privacy-policy. Teste real: Google Ads → Lead form →
   Send Data (Val; o form precisa estar mapeado e Active no app Google Lead Ads do GHL; pergunta de serviço → mapear em
   "Service Requested"). Falta também:
   (a) Atif pôr o número e as páginas de obrigado; (b) Google Ads conectado no GHL da YardSpring (Val); (c) ligação + SMS
   reais para (678) 448-4007 e envio de cada form (me avisa antes: o aviso vai para o Joe). Resto da conta: "Sequential
   Call Routing" publicado com números e usuários da BluVantage (não dispara aqui; limpar com o modelo).
10. **NorTex: 2 landing pages** (27–29/10): páginas do Atif no funil (go.nortexpools.com/premium-weekly-pool-cleaning,
   /pool-equipment-repair + 2 de obrigado), forms, tags, workflows e a linha (469) 218-3416 no ar. 29/10 (cliente via Val):
   o form agora vai para o calendário "Pool Service Appointment" já preenchido, igual ao site, e todo agendamento avisa
   o Fareed por SMS + e-mail (`scripts/nx_ads_booking.py`). Falta:
   - DNS: Frank criou o CNAME `go` → sites.ludicrous.cloud (30/10); as 4 URLs abrem (200) com os forms certos.
   - Teste real 30/10 (Pedro, form Weekly + agendamento): tags, campos, card, confirmações ao lead, SMS + e-mail de lead e
     de agendamento ao Fareed — tudo certo; teste apagado.
   - 03/11: Google Ads conectado (Val). Conversões offline ligadas (`scripts/nx_ads_conversions.py`): "LP Form Submit"
     (7888097011) nos 2 LP workflows, "Appointment Booked" (7887965192) no fim do "Appointment Booked -> Notify Fareed".
     Só conta contato com gclid (veio de clique no anúncio). Falta o teste real: clicar num anúncio da NorTex (Pedro),
     mandar o form e agendar; em até ~24 h aparece em Google Ads → Goals → Conversions (Val confere). Apagar o contato depois.
   - Send Data do lead form (NorTex e Pool Palooza): nenhum lead de teste chegou em nenhuma das contas até 03/11.
11. **Clear Pool Tucson** (call com Derek/Ed/Frank, 27/10; mensagem para o Ed no chat de 28/10):
    - **Ligação de teste**: sem "aperte 1", toda ligação toca o Derek. Ligar para (520) 777-9131 e deixar tocar até cair
      no recado (avisar o Derek antes) → me avisa e eu confiro tag/card/tarefa/aviso e apago.
    - **Frank**: telefone do GBP de volta para o número de rastreamento (520) 777-9131 e o site certo; depois refazer o
      teste do recado. A ligação "Frank Perez" (+1 346-763-6881, 27/10, não atendida) parece teste dele: confirmar.
    - **Derek, na tela** (nós não conseguimos pela API): escolher as etapas nos widgets de funil/pizza do dashboard;
      filtro de data "Till date" para ver os 32%.
    - **Dashboards**: ficar só com um? Você confirma e eu apago "Call Tracking" e "Lead Attribution" (dá pela API).
    - **Review Request** (draft, `scripts/cp_review_request.py`): 30 dias depois do Won semanal, 2 dias depois do
      One Time Repair, nota (NPS) → 5 = link do Google, menos = SMS para o Derek; 6 meses depois, o SMS de review de novo.
      Publicar = decisão do Derek (Ed pergunta). Antes de publicar eu testo numa cópia e confiro o texto do SMS/e-mail de
      review em Reputation → Settings.
    - **Ligações perdidas 29/09–27/10**: das 27 que não chegaram ao Derek, só 1 é lead real sem retorno: **P Carlson
      (520) 342-4654**, 18/10, desligou no IVR antigo (deixou gravação). O resto: spam/DND, cliente (Danielle Riggs),
      gente que o Derek atendeu depois, o próprio Derek testando (2/10) e o Frank (27/10). Derek liga para ele.
    - **Derek**: clientes da home warranty como contatos com tag (lista dele; eu importo).
    - **Val**: relatório Google Ads Search vs PMax, proposta de LSA e a mensagem "salve nosso número".
    - **Pool Brain / Skimmer** (`docs/poolbrain-review-integration.md`): a API do Pool Brain lista visitas/OS concluídas
      e cria cliente; falta a chave: Derek olha em Settings > API do Pool Brain (ou pede no chat de suporte). Skimmer:
      só no plano Enterprise (o cliente gera a chave no app). Com a chave: Won → cliente no app e review na conclusão.
12. **SwimReady**: Jeremy aprovou o PDF e vai mandar ajustes por código (mapa em `config/guide_codes/swimready-2026-10-22.json`).
   A troca pelo snapshot novo é uma migração; Ed pergunta quando o Jeremy quer virar.
13. **Refresh do snapshot** "Snapshot Pool Profits v9" (você, na tela): o master já tem as correções de 22–23/10; a WP
   Pools ainda nasceu da versão antiga.

### Esperando resposta (eu aplico quando chegar)

- **Pool Shack** (Rob): o Skimmer já manda boas-vindas/pedido de review ao cliente semanal? O horário comercial é 9–17?
- **Stay Fresh IVR** (draft): Ed escolhe o nome da opção 2; Frank/Mike: sem tecla → Mike?, Kris sem atender → Mike?,
  quais linhas, fora do horário; depois as gravações em MP3.
- **Stay Fresh inativos** (arquivos no scratchpad, fora do git): o Mike confirma a lista pelo Frank; tag do Ed (**não**
  "reactivation"); Jen Knight está como cliente ativa. Depois eu importo.
- **Tags universais**: Frank/Ed aprovam os nomes → piloto na Pool Shack → snapshot + script.
- **Ekahi**: Erik responde ao PDF de revisão por código e D1–D8 (mapa em `config/guide_codes/ekahi-2026-10-22.json`).
- **NorTex**: Fareed prefere 24 h em vez de 29 h de antecedência mínima? (troco em 1 minuto).

## Outras agências do GHL

### Pool Duck

- **Franchising — feira de Tampa**: 7 STOP. O SMS de qua 28/10 (último) já tem "Reply STOP to opt out."; Ed decide se
  corta. Albert Kollar respondeu "I'm ready" → Lee liga.
- **Google Lead Form da Wesley Chapel**: mesmo caso do item 4 (precisa de acesso ao Google Ads).
- **LWR — Google Ads** (27/10): SMS e lead form no ar. Falta no app Google Lead Ads da LWR (Integrations → Google Lead
  Ads → Manage Google Ads): ▶ no form "Weekly pool service done right" → mapear Full Name, Email, Phone, Zip → ativar
  (está "Sync Disabled"). Depois: Send Data no Google Ads (acesso só da Val) e SMS real para 941-541-5942 — me avisa
  antes (alerta vai para o Kenton).
- **The Pool Keepers**: os nossos 28 workflows estão em draft e ajustados; esperando o Frank/Nathan decidirem o que liga.

## Geral

- **Trocar os 3 refresh tokens** colados no chat (Pool Profits, Pool Duck, BurchTech) — `docs/get-firebase-token.md`.
