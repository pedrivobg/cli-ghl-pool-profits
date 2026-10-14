# Contexto para o Claude — cli-ghl-pool-profits

- Cliente/agência: **Pool Profits** (GHL de agência, nicho de limpeza de piscina nos EUA).
  Operador: Pedro. Snapshot atual: **V9** (guia: Implementation Guide v1.0, 25 workflows em 9 pastas).
- Base do CLI copiada de `pedrivobg/cli-ghl-ff` (Fórmula Fitness). Lá: 1 sub-conta, PIT.
  Aqui: **todas as sub-contas** via token Firebase de agência (`utils/agency.py`).
- Credencial: `GHL_FIREBASE_REFRESH_TOKEN` (env do ambiente ou `.env`). Nunca imprimir,
  logar ou commitar. `dump/`, `reports/`, `backup/` são dados de clientes — gitignored.
- Sub-conta **modelo**: Southern Pool + Outdoors. Prioritárias (calls com clientes):
  Passion Pool Care, Stay Fresh Pools, Bahama Blue Pool & Spa, The Pool Shack, The Pool Keepers
  (`config/priority.json`). Estado-alvo: `docs/modelo-southern.md`.
- Fluxo: `pp_dump.py --priority` → `pp_audit.py` → `pp_compare.py` → revisar → aplicar
  (`pp_mirror` → `pp_forms` → `pp_fix --drop-booking`). Histórico: `docs/execucao-*.md`;
  pendências do Pedro: `docs/TODO.md`.
- Regras de escrita no GHL: sempre GET + backup em `backup/<slug>/<id>.json` antes de PUT;
  testar em 1 sub-conta e revisar o diff antes de aplicar no resto; não mudar lógica sem
  pedido — correções básicas (nome de outra empresa, custom value vazio, link morto,
  usuário faltando) e status draft/published conforme o modelo.
- Endpoints com mais de um caminho conhecido passam por `Agency.first_ok`; o caminho que
  funcionou aparece no fim do `pp_dump.py` — atualizar a ordem em `agency.py` se mudar.

## Comportamento da API do GHL (verificado ao vivo)

- Workflow PUT valida assets: id de pipeline/etapa/campo de outra location → 400
  `ASSET_VALIDATION_FAILED`. Leituras logo após escrita podem vir defasadas (pipeline,
  listagem pública de workflows, busca de contatos): reler com espera.
- Gatilho: `active` segue o status do workflow (draft → inativo); PUT não liga/desliga.
  Para tirar um gatilho: `DELETE /workflow/{loc}/trigger/{id}` (com backup).
- Pipeline: `PUT services /opportunities/pipelines/{id}` com `{name, stages}` (sem
  `locationId`); etapa sem `id` é criada; ids existentes preservados.
- Inbound webhook: gatilho `type: inbound_webhook`; URL
  `https://services.leadconnectorhq.com/hooks/{loc}/webhook-trigger/{triggerId}`; passo
  `create_update_contact` com `fields` em camelCase (`firstName`, `email`, `phone`,
  `address1`) e valores `{{inboundWebhookRequest.<campo>}}`.
- Missed-call text back nativo: `enableMissedCallText` via `PUT services /locations/{id}`.
- Submissão de form não automatizável (Turnstile no `/forms/submit`); testar gatilhos por
  tag/etapa (`pp_e2e.py`) e conferir submissões reais em `/forms/submissions`.
- SMS de workflow usam o template (`attributes.template_id`) — o texto vive no template;
  e-mail guarda cópia do html no passo **e** no template (corrigir os dois).
- Nunca rodar `pp_e2e.py` em conta de cliente (dispara mensagens e notificações reais).
- Filtro de gatilho por tag (formato da UI): `{"field": "contact.tags", "id": "doesnot-have-tag",
  "title": "Doesn't Have Tag", "type": "select", "operator": "index-of-false", "value": "<tag>"}`
  (Has Tag: `index-of-true`, id `has-tag`). Funciona em `pipeline_stage_updated`.
- Forms: ler `GET backend /forms/{id}`; gravar `POST backend /forms/{id}` com `{name, formData}`
  (sem `locationId`); criar `POST backend /forms/` (resposta `{"form": …}`). Campo customizado
  no form = `fields[].tag` com o id do custom field DA CONTA (snapshot traz id da origem).
- Merge fields em link de SMS: `{{contact.phone}}` sai "(480) 555-1234" (espaço quebra o link);
  usar `{{contact.phone_raw}}`. Filtros liquid (`| url_encode`) fazem o GHL não enviar o SMS.
- Link de review do Google: `writereview?placeid=<location.googlePlacesId>` da própria conta.
- IVR: gatilho `ivr_incoming_call` publicado liga o número ao workflow (`inboundCallService`). Com IVR,
  toda ligação de entrada vira "completed" → gatilhos de chamada perdida param; marcar `missed call`
  dentro do IVR (`scripts/pp_ivr.py`). Número externo em `ivr_connect_call.customNumbers`:
  `{country, phone (E.164), displayValue, isValid}`.

## Outra agência: Pool Duck

- Token Firebase próprio, **fora do repo** (arquivo de env carregado com `set -a; . <arquivo>`); o
  cache de token é por refresh token (`.token-cache-<hash>.json`), então as duas agências não se
  misturam. `GHL_DUMP_DIR=dump/poolduck` mantém os dumps fora do alcance dos scripts `pp_*`.
- Scripts `pd_*` (Lakewood Ranch); registro e pendências em `docs/poolduck-lakewood-ranch.md`,
  incluindo a API de funis (clone entre sub-contas, salvar página com `pageType: "live"`).
