# CLI GoHighLevel — Pool Profits

CLI do GoHighLevel (mesma base do `cli-ghl-ff`, da Fórmula Fitness) configurado para a
**agência Pool Profits**: um único token de agência acessa **todas as sub-contas**, e os
scripts em `scripts/` fazem inventário, auditoria e comparação entre sub-contas.

Diferença para a Fórmula Fitness: lá era uma sub-conta só, com Private Integration Token.
Aqui são muitas sub-contas, então tudo roda na **sessão Firebase do usuário de agência**
(`GHL_FIREBASE_REFRESH_TOKEN`) — a mesma identidade do app web, que enxerga tudo o que o
usuário enxerga no navegador. Ver `cli_anything/gohighlevel/utils/agency.py`.

## Instalação

```bash
./install.sh                 # cria .venv/ e .env
```

Credencial: `GHL_FIREBASE_REFRESH_TOKEN` — de preferência como **variável de ambiente do
ambiente cloud** (não precisa de arquivo); senão, no `.env` (gitignored). Como obter:
[`docs/get-firebase-token.md`](docs/get-firebase-token.md).

Rede: o ambiente precisa permitir `services.leadconnectorhq.com`,
`backend.leadconnectorhq.com` e `securetoken.googleapis.com`.

## Uso

```bash
P=./.venv/bin/python

$P scripts/pp_dump.py --list                 # lista todas as sub-contas
$P scripts/pp_dump.py --priority             # Southern (modelo) + 5 prioritárias → dump/
$P scripts/pp_dump.py --only "Bahama Blue"   # uma sub-conta
$P scripts/pp_dump.py --all                  # todas

$P scripts/pp_audit.py                       # erros básicos nos workflows publicados → reports/
$P scripts/pp_compare.py                     # cada prioritária vs modelo Southern → reports/
```

Escrita (sempre plano primeiro; `--apply` grava com backup em `backup/`):

```bash
$P scripts/pp_mirror.py --target "Bahama Blue" [--apply] [--no-publish]  # espelha a Southern
$P scripts/pp_forms.py  --only "Bahama Blue" [--apply]   # todo form de lead → 1 workflow
$P scripts/pp_fix.py    --only "Bahama Blue" --drop-booking [--include-drafts] [--apply]
$P scripts/pp_e2e.py    --only "Test Snapshot"           # testes reais (só conta de teste)
$P scripts/pp_restore.py --list "Bahama Blue" | --file backup/... [--apply]
```

Sequência para uma conta: `pp_dump` → `pp_mirror --apply` → `pp_dump` → `pp_forms --apply`
→ `pp_fix --drop-booking --apply` → `pp_dump` → `pp_audit` / `pp_compare`.
O que já foi feito: `docs/execucao-2026-10-13.md`. Pendências: `docs/TODO.md`.

`dump/`, `reports/` e `backup/` contêm dados de clientes e são gitignored.

| Arquivo | O que é |
|---|---|
| `config/priority.json` | sub-conta modelo + lista de prioridade |
| `docs/modelo-southern.md` | estado-alvo definido na call (base do espelhamento) |
| `scripts/pp_dump.py` | inventário read-only: workflows completos + gatilhos, custom values, pipelines, forms, calendários, usuários, templates |
| `scripts/pp_audit.py` | auditoria offline: nome de outra empresa, custom value vazio, link de calendário, notificação sem usuário, gatilho duplicado/quebrado |
| `scripts/pp_compare.py` | diff por workflow (status, gatilhos, textos, esperas) e pipeline contra o modelo |
| `scripts/pp_mirror.py` | espelha o modelo numa conta do snapshot (pipeline, templates, workflows, gatilhos, status) |
| `scripts/pp_forms.py` | garante que cada form de lead tem exatamente um workflow publicado escutando |
| `scripts/pp_fix.py` | correções básicas (merge field quebrado, link de calendário, nome de outra empresa, tarefa/notificação sem usuário, pipeline inexistente) |
| `scripts/pp_e2e.py` | testes reais de gatilho → efeito numa sub-conta de teste |
| `scripts/pp_restore.py` | desfaz qualquer alteração a partir de `backup/` |
| `./ghl ...` | CLI original, para uma sub-conta (precisa `GHL_API_KEY` + `GHL_LOCATION_ID`) |

## Segurança

O refresh token equivale à sessão inteira da conta de agência. Nunca commitar; para
revogar, fazer logout no GHL e gerar outro.
