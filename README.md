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

`dump/` e `reports/` contêm dados de clientes e são gitignored.

| Arquivo | O que é |
|---|---|
| `config/priority.json` | sub-conta modelo + lista de prioridade |
| `docs/modelo-southern.md` | estado-alvo definido na call (base do espelhamento) |
| `scripts/pp_dump.py` | inventário read-only: workflows completos + gatilhos, custom values, pipelines, forms, calendários, usuários, templates |
| `scripts/pp_audit.py` | auditoria offline: nome de outra empresa, custom value vazio, link de calendário, notificação sem usuário, gatilho duplicado/quebrado |
| `scripts/pp_compare.py` | diff por workflow (status, gatilhos, textos, esperas) e pipeline contra o modelo |
| `./ghl ...` | CLI original, para uma sub-conta (precisa `GHL_API_KEY` + `GHL_LOCATION_ID`) |

## Segurança

O refresh token equivale à sessão inteira da conta de agência. Nunca commitar; para
revogar, fazer logout no GHL e gerar outro.
