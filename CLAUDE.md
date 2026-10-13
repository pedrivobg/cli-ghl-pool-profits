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
- Fluxo: `pp_dump.py --priority` → `pp_audit.py` → `pp_compare.py` → revisar → aplicar.
- Regras de escrita no GHL: sempre GET + backup em `backup/<slug>/<id>.json` antes de PUT;
  testar em 1 sub-conta e revisar o diff antes de aplicar no resto; não mudar lógica sem
  pedido — correções básicas (nome de outra empresa, custom value vazio, link morto,
  usuário faltando) e status draft/published conforme o modelo.
- Endpoints com mais de um caminho conhecido passam por `Agency.first_ok`; o caminho que
  funcionou aparece no fim do `pp_dump.py` — atualizar a ordem em `agency.py` se mudar.
