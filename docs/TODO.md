# TODO do Pedro — só o que está aberto (26/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`. Testes são nossos: nada aqui vai para a equipe ou
para o cliente testar. Teste que dispara aviso para o cliente: **me avisa antes** e eu desvio os avisos.

## Pool Profits (sub-contas da nossa agência)

1. **Poolheads** (A2P aprovado: Brand + Campaign CN1AUUF; SMS "delivered" desde 23/10). Captura no ar desde 23/10:
   IVR "Business Hours Call Routing" + "After Hours Message" nas 3 linhas, Contact Created → add owner, Website & GBP
   Call - Tag, Answered Incoming, Missed New Lead (texto deles), Missed Incoming, Website Form Fill.
   - **Teste** (depois das 17h CT ou no fim de semana, quando o IVR não toca o Felipe): ligar para 936-314-9255, deixar
     recado → me avisa; eu confiro tag, SMS no seu celular e card, e apago o contato antes da tarefa de 1 h.
   - Felipe (27/10): SMS 2 do Missed New Lead tirado; ele mesmo conecta o WhatsApp.
   - **Conta antiga → nossa**: contatos importados (27/10, 1.513 novos). Automações antigas: perguntar ao Frank se
     alguma ainda é usada; só se for, precisamos do token da conta antiga (outra agência; o login pede código):
     1. avisar o Frank na hora (o login manda código para info@poolheadscare.com, e-mail do cliente);
     2. Chrome → app.gohighlevel.com com o login que o Frank mandou + o código;
     3. sub-conta da Poolheads → Ctrl+Shift+J → colar o trecho de `docs/get-firebase-token.md` → Enter;
     4. colar o token no chat.
     Com ele eu copio todos os workflows em draft (pasta "Conta antiga") e todos os contatos (tag `existing customer`).
   - Depois disso e do OK do Frank: publico o resto (No Response, Quote, No-Show, Lost, Won, Review…).
   - **Na tela**: Call Recording no 936-314-9255 (sem a mensagem); Felipe/Jorge no app com a conta nova; deskphone.
   - **E-mail do Jorge Arias**: crio o usuário e ponho no IVR.
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
4. **Google Lead Form "Weekly Pool Service Done Right"**: workflows no ar; form mapeado e ativo em Wrigley's,
   BluVantage, Precision, Reign e Damon's. Nenhum lead chegou ainda. **Teste parado**: a conta Google do seu amigo
   (pedrolp2005@gmail.com) não acessa o Google Ads dos clientes. Os forms estão ligados a val@poolprofits.com (Wrigley's,
   BluVantage, Reign, Damon's) e dane.precision@ (Precision). Ou a Val dá acesso pela MCC 486-503-6899, ou alguém com
   acesso faz o Send Data (me avisa antes). **Simple**: a conta 258-800-5448 não mostra o form (Val diz que é essa).
5. **Pool Shack: 2 landing pages de Google Ads**. Forms "GOOGLE ADS – WEEKLY" (`mlRZlBRFVFIJjiTYiWKX`) e "GOOGLE ADS –
   REPAIRS" (`Hb5KiQHQZkGFmSgzJbIk`) + "Google Ads LP - Weekly/Repairs" no ar e testados (`scripts/ps_ads_forms.py`). Falta:
   URLs e páginas de obrigado do Atif (eu ponho a URL e ligo o redirecionamento); Google Ads conectado no GHL da Pool
   Shack (Val); números de rastreamento de ligação (decisão sua); envio real de cada form (me avisa antes).
6. **BluVantage: 3 landing pages**: forms prontos e testados (envio real quando o Atif puser nas páginas; me avisa
   antes). Números por página no ar (26/10): Weekly 470-470-8874, Repairs 470-450-6322, Winter 470-450-4427, no IVR e
   com tag/card/conversão por serviço. **Teste**: ligar fora do horário (o IVR toca a equipe no horário) para os 2 novos
   e me avisar; eu confiro tags/card e apago.
7. **Southern: SMS do Google Ads** no ar (26/10). Teste final: mandar um SMS do seu celular para (972) 632-3259 →
   me avisa antes (o aviso vai para o Brett) e eu confiro tag/card/tarefa e apago.
8. **NorTex: ligação de teste** (27/10): ligar para (469) 238-2660 e desligar durante a mensagem do IVR (não toca
   ninguém) → o SMS de chamada perdida chega no seu celular; me avisa e eu confiro a tag/card e apago antes da tarefa de 1 h.
9. **YardSpring: 3 landing pages** (27/10): forms, tags e workflows no ar e testados (`scripts/ys_ads_forms.py`).
   Falta: (a) as 3 páginas de obrigado no WordPress (yardspringpools.com/thank-you-…): ou o Atif cria com o texto que
   mandei, ou me dão um Application Password do WP; (b) Google Ads conectado no GHL da YardSpring (Val); (c) envio real
   de cada form quando as páginas subirem (me avisa antes: o aviso vai para o Joe).
10. **NorTex: 2 landing pages** (27/10): forms, tags, workflows e a linha (469) 218-3416 (no IVR, como a principal) no ar
   e testados (`scripts/nx_ads_forms.py`). Falta: as 2 páginas de obrigado no WordPress (Atif, com o texto que mandei,
   ou Application Password do WP); Google Ads conectado no GHL da NorTex (Val); envio real de cada form quando as
   páginas subirem (me avisa antes: o aviso vai para o Fareed).
11. **SwimReady**: Jeremy aprovou o PDF e vai mandar ajustes por código (mapa em `config/guide_codes/swimready-2026-10-22.json`).
   A troca pelo snapshot novo é uma migração; Ed pergunta quando o Jeremy quer virar.
12. **Refresh do snapshot** "Snapshot Pool Profits v9" (você, na tela): o master já tem as correções de 22–23/10; a WP
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
