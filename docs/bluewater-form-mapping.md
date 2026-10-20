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

## No GHL do Bill (fazer com o acesso)

- **Campos do contato**: nome → first/last, email, phone, business → `companyName`, city → `city` (texto livre
  "cidade, estado"). Custom fields (contato): Route Monthly Billing, Route Visits per Week, Route Quality Score,
  Route Multiple, Route Value Low, Route Value High, Route Equipment Value, Route Inventory Value, Route Is
  Franchise, Route Agreements, Website Message.
- **Tags**: 1 → `route-calculator` (+ `bluewater-report` / `wants-confidential-call` pelos checkboxes); 3 →
  `sellers-guide` (+ `wants-opinion-of-value`); 4 → `buyers-guide` (+ `buyer-registered`); 5 → `website-contact`;
  6 → `bluewater-report`. Criar todas na conta (`pp_tags_missing`).
- **Entrada**: 1 workflow por form com gatilho **inbound webhook** (mesmo padrão da Passion), passo
  `create_update_contact` (casa pelo e-mail), tags, custom fields, e:
  - `wants-confidential-call`, `wants-opinion-of-value`, contato (5): tarefa para o Bill vencendo hoje + aviso
    interno (e-mail; SMS só com número/A2P da conta).
  - números (2): só atualiza os campos do contato que já existe + nota com os valores.
  - Nada de SMS automático para o lead: nenhum form tem consentimento de SMS (o telefone é "text is fine").
- **Site (Vik)**: Elementor Pro → Actions After Submit → **Webhook** com a URL de cada workflow (forms 3–6, sem
  código; manter o e-mail). Calculadora: o endpoint `bwb/v1/route-lead` repassa o mesmo JSON para a URL do
  webhook (server-side), mantendo o e-mail ao Bill.
- **Teste**: nós mandamos 1 de cada pelo webhook (sem passar pelo Turnstile/Elementor), conferimos contato, tags,
  campos e tarefa, e apagamos; depois 1 envio real de cada form pelo site (Pedro).
