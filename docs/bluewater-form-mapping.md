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
| 5 | Contato (`59d31fac`) | home, /contact/ (botões "Schedule a Confidential Call" e "Get a Free Confidential Valuation" levam aqui) | name, email*, phone, message | Elementor → e-mail |
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

## O que o Vik faz no site (contrato)

POST `application/json` para a URL de cada form, **sem tirar o e-mail que já vai para o Bill**. Checkbox = `"yes"`/`"no"`;
`first_name`/`last_name` = nome dividido no primeiro espaço; campos vazios podem ir vazios.

- Calculadora (endpoint `bwb/v1/route-lead`): `type: gate` → URL "Route Calculator Lead" com `first_name, last_name, email,
  phone, business, city, report, talk, page`; `type: figures` → URL "Route Calculator Figures" com `first_name, last_name,
  email, monthly_billing, visits_per_week, quality_score, multiple, value_low, value_high, equipment_value,
  inventory_value, is_franchise ("yes"/"no"), agreements, page`.
- Seller's Guide (`bwr0009`): `first_name, last_name, email, opinion, page`. Buyer's Guide (`bwr0010`): `first_name,
  last_name, email, register, page`. Contato (`59d31fac`): `first_name, last_name, email, phone, message, page`.
  Newsletter (`36394603`): `email, page`. (Hook `elementor_pro/forms/new_record` no plugin dele, que já existe.)
- Honeypot preenchido = não enviar.
