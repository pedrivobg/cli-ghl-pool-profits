# Bluewater Brokerage — mapeamento dos forms do site → GHL (ClickUp "GHL Form Mapping")

Levantado em 20/10 no site público (bluewaterbrokerage.com, WordPress + Elementor). Hoje **nenhum form chega ao
GHL**: todos mandam e-mail para o Bill (o próprio código da calculadora diz "emails Bill until GoHighLevel is
connected"). O GHL do Bill fica na agência **BurchTech Solutions** — sem acesso ainda (TODO 10).

## Forms do site

| # | Form | Onde | Campos | Para onde vai hoje |
|---|---|---|---|---|
| 1 | Calculadora — destrava (`gateForm`, tipo `gate`) | /route-calculator/ | business, name*, email*, phone, city (cidade e estado), `report` (checkbox Bluewater Report), `talk` (checkbox conversa confidencial), honeypot `website` | `POST /wp-json/bwb/v1/route-lead` → e-mail ao Bill |
| 2 | Calculadora — números (tipo `figures`, ao sair da página se mexeu) | /route-calculator/ | os dados do 1 + monthly_billing, visits_per_week, quality_score, multiple, value_low, value_high, equipment_value, inventory_value, is_franchise, has_agreements | mesmo endpoint → e-mail ao Bill |
| 3 | BWB Seller Guide (`bwr0009`) | /resources/ | name*, email*, `opinion` (checkbox "confidential opinion of value"), honeypot | Elementor → e-mail ao Bill + PDF/link ao visitante |
| 4 | BWB Buyer Guide (`bwr0010`) | /resources/ | name*, email*, `register` (checkbox "register me as a buyer"), honeypot | idem |
| 5 | Contato (`59d31fac` na home, `c6411dd` em /contact/; os botões "Schedule a Confidential Call" e "Get a Free Confidential Valuation" levam aqui) | home, /contact/ | name, email*, phone, message | Elementor → e-mail |
| 6 | Newsletter do rodapé (`36394603`) | todas as páginas | email* ("news and insight for pool business owners") | Elementor → e-mail |

Tags definidas pelo arquivo do cliente (comentário no código da calculadora): `route-calculator`; checkbox report →
`bluewater-report`; checkbox talk → `wants-confidential-call` **com tarefa para o Bill no mesmo dia**.

## Feito no GHL do Bill (20/10, `scripts/bw_forms.py`, token da BurchTech em `burchtech.env` fora do repo)

Agência BurchTech (`syjenoyGz1jZ3ndDPkCm`), sub-conta Bluewater Brokerage `M6eDjuSa3RdwukFl2rW2`. 6 workflows publicados
("Website - …"), cada um com seu inbound webhook (URLs em `backup/bluewater-brokerage/webhook-urls.json`, fora do
git — são a "senha" de entrada de leads). 16 campos de contato e 9 tags novos; nada existente alterado, exceto o
"Blue Water Website Form Submitted" (antigo, form GHL que não está mais no site): SMS e tarefas iam para usuários que
não existem mais → Bill.

| Workflow | Contato | Tags | Card (Marketing Pipeline) | Bill |
|---|---|---|---|---|
| Route Calculator Lead | nome, e-mail, telefone, empresa, cidade | `route-calculator`, `source-website`, + `bluewater-report` / `wants-confidential-call` pelos checkboxes | New Lead - Seller | SMS; quer conversa → tarefa hoje |
| Route Calculator Figures | 10 campos "Route …" | `route-calculator` | — (mesmo contato) | — |
| Seller's Guide Download | nome, e-mail | `sellers-guide`, `source-website`, + `wants-opinion-of-value` | New Lead - Seller | SMS; opinião de valor → tarefa hoje |
| Buyer's Guide Download | nome, e-mail | `buyers-guide`, `source-website`, + `buyer-registered` | New Lead - Buyer | SMS |
| Contact Form | nome, e-mail, telefone, "Website Message" | `website-contact`, `source-website` | New Lead - Other | SMS + tarefa hoje |
| Newsletter Signup | e-mail | `bluewater-report`, `source-website` | — | — |

Testado com 1 envio por form (alertas desviados para e-mail de teste): contato, campos, tags, card na etapa certa,
tarefa para o Bill, ramo "não" do checkbox, reenvio sem telefone não apaga o telefone nem duplica o card. Contatos de
teste apagados; alertas de volta para SMS do Bill.

## Lado do site: nós, não o Vik (decisão do Pedro, 20/10) — NO AR desde 21/10

O host (Kinsta + Cloudflare) descarta o cabeçalho Authorization: Application Password não loga ("rest_not_logged_in" até
para usuário inexistente). Instalação: o Pedro colou o código gerado por `bw_site.py render` em Snippets → Add New (Code
Snippets) e ativou. Testes (21/10): `bw_site.py test` no site = payloads certos nos 6 forms; `bw_site.py test --send` com
os avisos desviados (`bw_forms.py test --to pedro@…`) = 6/6 contatos certos no GHL; envio real pelo navegador do rodapé
(newsletter) e da calculadora = contato, tags, página, card em New Lead - Seller; o Bill recebeu os 2 e-mails normais do
site marcados TEST. Contatos de teste apagados; `bw_forms.py live` (SMS ao Bill) reaplicado. `bw_site.py status` mostra os
últimos envios (rota com ?key=, chave em `backup/bluewater-brokerage/site-key.txt`).


O Vik não mexe com isso; quem liga o site ao GHL somos nós. Um snippet PHP (`site/bluewater/bwb-ghl.php`), instalado
pelo plugin **Code Snippets** (`scripts/bw_site.py apply`), manda cada envio para o webhook do form **depois** do que o
site já faz: o e-mail ao Bill, o PDF do guia e o endpoint da calculadora continuam iguais. O nome é dividido no primeiro
espaço, checkbox vira `"yes"`/`"no"`, honeypot preenchido não manda nada.

- Forms do Elementor: hook `elementor_pro/forms/new_record`, pelo id do form (`bwr0009` seller, `bwr0010` buyer,
  `59d31fac` e `c6411dd` contato, `36394603` newsletter); outro form qualquer é ignorado.
- Calculadora: filtro `rest_request_after_callbacks` na rota `/bwb/v1/route-lead` (o plugin do Vik não é alterado);
  `figures` com os mesmos números vai uma vez por dia (a página reenvia a cada troca de aba).
- Rotas só para admin: `GET /wp-json/bwb-ghl/v1/status` (últimos 30 envios e o HTTP do GHL) e `POST
  /wp-json/bwb-ghl/v1/test` (roda o mapeamento de um form; `send: true` manda ao GHL).
- Testes: `php site/bluewater/test-bwb-ghl.php` (local, com stubs do WordPress/Elementor, 16 casos);
  `bw_site.py test` (mapeamento no site = mesmos payloads já testados no GHL); `bw_site.py test --send` com o
  `bw_forms.py test --to <inbox>` antes (aviso desviado) e `bw_forms.py live` depois.
- Acesso: Application Password de um admin do WordPress em `<scratchpad>/bluewater-wp.env` (`BW_WP_USER`,
  `BW_WP_APP_PASSWORD`), fora do repo. Desligar: `bw_site.py off`.
