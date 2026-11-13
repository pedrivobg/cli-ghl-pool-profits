# Prompt para a extensão do Chrome — widgets de Google Analytics vazios (13/11)

Conferido pela API em 13/11: estas 15 contas têm o GA conectado, mas os 2 widgets de Google Analytics do "Pool Profits
Dashboard" estão sem propriedade (a cópia do dashboard zera). A propriedade certa de cada uma é a que a própria conta usa
(`googleAnalytics4PropertyId`), com o nome tirado da lista de propriedades. As outras 19 já apontam para o cliente certo.

```
You are working in GoHighLevel (app.poolprofits.com, I'm already logged in as the agency). Task: in the 15 sub-accounts below, set the two Google Analytics widgets of the default dashboard "Pool Profits Dashboard" to that client's own Google Analytics property. Work through the list in order.

RULES
- Only touch the dashboard "Pool Profits Dashboard" and only its 2 widgets "Google Analytics count" and "Google Analytics chart". Never delete, add, move or rename anything; don't change other dashboards, integrations, workflows, contacts or settings.
- Do not connect, disconnect or re-authorize any Google account. Only pick from what is already there.
- Pick EXACTLY the account and property written for that sub-account below. The GA account "Pool Profits" holds every client's property and GoHighLevel pre-selects the first one in the list, which belongs to ANOTHER client: always open the Property dropdown and choose the one named below. If that exact name isn't in the list, don't pick anything else: skip the widget and write it down.
- If the page says "outdated dashboard version", reload and start that account again.

STEPS FOR EACH ACCOUNT
1. Open the URL. Make sure "Pool Profits Dashboard" is the one shown.
2. Click Edit Dashboard.
3. For "Google Analytics count" and then "Google Analytics chart": open the widget's edit settings, choose the Google account, the Account and the Property listed below, keep the other settings, and save the widget.
4. Save/exit edit mode. Reload the page and check both widgets now show numbers (or "No data" for a quiet site) and not "select a property".

ACCOUNTS
1. Clean Co Pools — https://app.poolprofits.com/v2/location/GcsMfF3Np8B43qyum1aT/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Clean Co Pools"
2. Clear Pool Solutions Tucson — https://app.poolprofits.com/v2/location/ghUi89uCpNyNunNpbtAt/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Clear Pool Solutions GA4"
3. Ekahi Solutions LLC — https://app.poolprofits.com/v2/location/qtSUhAbLtnENh56h17a3/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Ekahi Solutions"
4. GID Pools — https://app.poolprofits.com/v2/location/8v9OLKghkGdkLyxmXnjF/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "GID Pools"
5. Golden View Pools LLC — https://app.poolprofits.com/v2/location/01HhBsJPYyBz9f5SamaT/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Golden View Pools"
6. JM Pool Service — https://app.poolprofits.com/v2/location/sjWTQf6NYR4sKxuBVGYO/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "JM Pool Service"
7. Legion Pools — https://app.poolprofits.com/v2/location/TReMqKUFpRfbLtAa65Ef/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Legion Pools"
8. Next Level Pools — https://app.poolprofits.com/v2/location/Xt71HRWlK3ZotYM9vErO/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Next Level Pools AZ"
9. Pool Palooza — https://app.poolprofits.com/v2/location/AjePy51fOb6BM1Kk2QQX/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Pool Palooza"
10. Pool Smart OC — https://app.poolprofits.com/v2/location/a2Dqe4n0gbEmIPKUL34P/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Pool Smart OC"
11. Pool Time — https://app.poolprofits.com/v2/location/Ue1ELGKBmfCpt5dyLGoy/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Pool Time Riverside"
12. Pooltexx LLC — https://app.poolprofits.com/v2/location/3WwQFxAYXqbxMOy2eYQ4/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "PoolTexx"
13. Signature Pool Care — https://app.poolprofits.com/v2/location/DejEGQDNwFL3xDwiR0YF/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Signature Pool Care"
14. Simple Pool Care LLC — https://app.poolprofits.com/v2/location/gCv3a9Y76Zzx50EjglGU/dashboard — Google account: hello@poolprofits.com — Account: "Pool Profits" — Property: "Simple Pool Care"
15. Sunwave Pool Pros — https://app.poolprofits.com/v2/location/GeeXTPcJXAoVUAmzLxfT/dashboard — Google account: sunwavepros@gmail.com — Account: "Google Ads Account" — Property: "sunwavepros.com"

REPORT (Portuguese): one line per account: OK (property set and saved, numbers shown) / sem dados (saved, widget shows no data) / pulado (why). Anything that looked different from these steps.
```
