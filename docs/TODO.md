# TODO — o que depende de você (13/10/2026)

Só entrou aqui o que não deu para resolver daqui depois de tentar.

## Urgente

1. **Site da Passion manda os leads para outra conta do GHL.** O código de
   passionpoolcare.com envia o formulário para um webhook da location
   `Y7wOLPd7DJ1UPHzcD8hG`, que não é da agência (a API responde 403). Os leads do site não
   chegam na sub-conta da Passion.
   - Já existe na Passion o workflow **Website Webhook Lead To Pipeline**, testado ponta a
     ponta com o mesmo payload que o site envia.
   - Falta: quem mantém o site trocar `LEAD_WEBHOOK` pela URL em `docs/passion-webhook-url.txt`.
   - Vale descobrir de quem é a `Y7wO…`: os leads anteriores do site estão lá.
   - Tentei: não tenho acesso ao site nem a essa location.

2. **Trocar o refresh token do Firebase**, que foi colado no chat: fazer logout no GHL e
   gerar outro com `docs/get-firebase-token.md`.

## Decisões (copy e negócio)

3. **Review Response - Positive** promete *"every referral earns you a free month of
   service!"* em todas as contas. Confirmar com cada cliente se esse programa existe; se
   não existir, tirar a frase. Não mexi em copy comercial sem confirmação.
4. **Dois telefones nas mensagens**: algumas usam `business_phone`, outras
   `a2p_verification_number`. Na Southern são números diferentes (214-308-1744 e
   214-922-1914). Escolher um padrão.
5. **Paid Ads na Bahama, Passion e Pool Shack**: o AdWords Form está publicado e é ele quem
   recebe o form da landing `go.*`; adiciona a tag `adwords` e dispara conversão no Google
   Ads. Se esses clientes não rodam Ads para essa página, coloque os 08 Paid Ads em draft
   e rode `pp_forms.py --only "<conta>" --apply` (o Landing Page passa para o Website Form Fill).
   - Na Pool Shack, o AdWords Form escuta uma cópia do Landing Page que nenhuma página usa,
     então a conversão nunca disparou.
6. **Pool Keepers**: tudo em draft. Para ir ao ar (depois do A2P):
   `pp_mirror.py --target "The Pool Keepers" --apply` (sem `--no-publish`).
7. **Stay Fresh** não é do snapshot V9. Recebeu só as correções básicas; trazer para o
   modelo exige instalar o snapshot. Há um draft "Pool Smart OC Customers - SMS" com nome de
   outro cliente: revisar antes de usar.

## Manual no GHL (sem API)

8. **Reputation → Settings → e-mail de review**: conferir o logo nas contas antigas
   (Southern, Bahama, Passion, Pool Shack, Pool Keepers). A API não expõe essa tela;
   testei 7 endpoints.
9. **Duplicatas** "DUPLICADO - não publicar - …" na Pool Shack (26) e Pool Keepers (27):
   apagar quando quiser. Os forms também estão em dobro nessas duas contas.
10. **Site principal da Pool Shack** (thepoolshackarizona.com) ainda usa WPForms (forms
    440/443) nas 5 páginas que verifiquei. Quando trocarem por form do GHL:
    - se for um dos forms existentes (Landing Page, Service Page, Lead Gen), já cai no
      Website Form Fill;
    - se criarem um form novo, rodar `pp_forms.py --only "The Pool Shack" --apply`.
    - Bahama e Pool Keepers também usam WPForms no domínio principal; não dá para ver
      daqui como esses leads chegam ao GHL.

## Próximo passo sugerido

11. **Snapshot Pool Profits** (a sub-conta master) ainda tem todos os bugs corrigidos hoje:
    merge fields quebrados, tarefas sem responsável e vencendo em 1970, links de calendário,
    "Clear Pool Solutions Tucson" no AdWords Call In e notificação sem usuário. Corrigir
    antes de reinstalar o snapshot nas contas: `pp_mirror` + `pp_fix` nela, quando você liberar.

Obs.: a marcação "incompleto" que o GHL mostra nos passos "Add Task" é só visual. Testei os
4 passos de tarefa do modelo e todos criam a tarefa atribuída.
