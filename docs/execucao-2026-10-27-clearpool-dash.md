# 27/10 — Clear Pool Tucson: dashboards, pipeline e resultado (Pedro: "ele quer ver se nosso serviço traz resultado")

- Dashboards (API `services /reporting/dashboards?locationId`; detalhe `/reporting/dashboards/{id}`): eram 10, 9 vindos do
  snapshot em 30/04 (4 "Dashboard" iguais, 2 "Call Tracking", Appointment, Customer Communication). Apagados 7 com
  `DELETE /reporting/dashboards/{id}` corpo `{locationId, version: curVer-1}` (backup em
  `backup/clear-pool-solutions-tucson/dashboards-20261027.json`). Ficaram: "Dashboard" (padrão), "Call Tracking Dashboard",
  "Lead Attribution and Overview Dashboard Template". Renomear/editar pela API não deu (PUT → 409 "outdated version").
- Pipeline: tiradas as etapas vazias e sem uso "Current Customer" e "Drip Campaign | Reactivate" (backup). Ficam 8.
- Resultado (contatos com tag `new lead`/`won`, spam/DND à parte), abr–out: 166 leads reais, 37 viraram cliente (22%);
  Google Ads 44 → 8, Website & GBP 112 → 26, outros 10 → 3; 100 spam filtrados. Página: Artifact "Clear Pool Tucson Lead
  Results" (https://claude.ai/artifact/Rv8ANR4PAYzp6n7NuEJYaJ), dados fixos de 27/10.
