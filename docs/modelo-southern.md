# Modelo Southern Pool + Outdoors — o que mudou na call (base para espelhar)

Fonte: transcrição da call Edmund / Frank / Val / Pedro (outubro/2026), feita ao vivo
na sub-conta **Southern Pool + Outdoors** sobre o snapshot **V9**. Esta lista é o
"estado-alvo" que `scripts/pp_compare.py` usa para medir as outras sub-contas.
Os pontos que a call deixou em aberto foram conferidos ao vivo na Southern em 13/10.

Princípios decididos na call:

- **Menos é mais.** O baseline deve servir para quase qualquer empresa de piscina;
  customizações entram depois, na call de estratégia com o cliente.
- **Mensagens "evergreen".** O dono move o card dias depois; nenhuma mensagem pode
  depender de tempo ("ontem", "hoje cedo"). Tem que fazer sentido se sair 1 dia ou 2
  semanas depois.
- **Sem link de calendário no baseline.** A maioria usa Skimmer / PoolBrain; o
  calendário do GHL não está sincronizado e o link cai numa página vazia.
- **Os donos não aplicam tags — eles (às vezes) arrastam o card.** Todo gatilho por tag
  ganha também o gatilho por mudança de etapa.
- O que não é usado fica no snapshot em **draft** (não é apagado).

---

## 01 — Incoming Lead

| Workflow | Estado-alvo |
|---|---|
| **Website Form Fill To Pipeline** | Publicado. Gatilho = form **Website Form Fill / Main Website Form** (o form novo, colocado em todas as páginas do site). O gatilho antigo do form **Landing Page** foi **removido** daqui — o Landing Page é das campanhas (08 — AdWords), e com os dois o lead entrava em dobro. Aplica tag `new lead` → só entra em New Lead, **não** recebe o SMS de missed call. Notificação interna com **usuário selecionado** (faltava e quebrava a execução). |
| **Missed Incoming Call to Pipeline** (renomeado do antigo *Incoming Call To Pipeline*) | Publicado. Gatilho: chamada recebida com status busy / canceled / voicemail / no answer. Tags `new lead`, `inbound call` **+ `missed call`**. Cria oportunidade (nome completo – inbound call) e tarefa. |
| **Answered Incoming Call to Pipeline** (novo, duplicado do anterior) | Publicado. Gatilho: chamada recebida **atendida**. Mesmas ações, **sem** a tag `missed call` → não dispara SMS ao lead (evita "acabamos de falar e recebi mensagem"). |
| **New Lead - Initial SMS Follow-up** | Publicado. Gatilho trocado de tag `new lead` → tag **`missed call`** (é o missed-call text back). Ver textos abaixo. Espera **10 → 30 minutos**. |

Textos do *New Lead - Initial SMS Follow-up*:

1. SMS 1 (imediato): *"Hey {{contact.first_name}}, this is {{owner}} from {{business}}. We're sorry we
   missed your call. We will be calling you back shortly. Is this the best number to call you back at?"*
   (termina em pergunta de propósito — puxa resposta).
2. Espera **30 min**. Se respondeu → tag `in communication`.
3. SMS 2: *"Hey, I just want to make sure you got my last message. We'd love to help keep your pool
   clean. Text or call this line back, please."* — **sem booking link**. O template antigo
   *New Lead SMS 2* tinha `{{custom_values.booking_link}}`; foi criada versão sem link
   ("…When is a good time to chat?"). A versão com link fica como opcional para quem
   configurar calendário.

Separado do workflow: o **missed-call text back nativo** do GHL (`enableMissedCallText`
da location) manda um SMS próprio — o que aparece sem o ícone roxo. Desligado na Southern
na call e, em 13/10, também na Bahama, Passion, Pool Shack e Pool Keepers.

## 02 — Lead Nurturing

| Workflow | Estado-alvo |
|---|---|
| **No Response Follow-up** | Publicado. Gatilho: tag `follow up` **ou** etapa → **No Response / Follow-up** (etapa nova). SMS 1 mantido (*"Hey {{first}}, still thinking about getting your pool cleaned? We'd love to help. Give us a call."*); espera 1 dia; SMS 2 novo: *"Hey {{first}}, just checking in from {{business}}. Spots are filling up fast this week for initial estimates."*; espera 2 dias; SMS 3 novo: *"Hi {{first}}! We understand now might not be the best time, but if you ever need us, here we are."*; espera 2 dias → move para **Lost**. Respondeu em qualquer ponto → volta para In Communication. **Sem links.** |
| **Quote Sent Follow-up** | Publicado. Gatilho: etapa → Quote Sent. Espera 1 dia. SMS 1: última frase trocada de *"We'd love to get your pool sparkling clean"* para ***"We'd love to have an opportunity to work on your pool."*** (serve para limpeza, reparo e reforma). SMS 2 mantido (*"Hi {{first}}, still deciding? Your quote from {{business}} is ready whenever you are…"*). |
| **No-Show Follow-up** | Publicado. Gatilho: tag `no-show` **ou** etapa → **No-Show**. SMS 1 mantido. SMS 2: **remover o booking link** (trocar por "reply here or call us at {{business_phone}}"). No-show = o técnico foi à casa e o cliente não estava. |

## 03 — Appointment

Não usado no baseline (agenda fica no software de campo). Workflows de confirmação /
lembrete **em draft**; calendários continuam existindo como opção. A etapa **Scheduled**
é só organizacional, não dispara nada.

## 04 — Pipeline Automations

| Workflow | Estado-alvo |
|---|---|
| **In Communication Stage** | **Draft.** Etapa vira só organizacional (o follow-up agora vive em *No Response*). Fica no snapshot para empresas só de manutenção. |
| **Won Stage** | Publicado com e-mail de boas-vindas **genérico** (não falar só de limpeza semanal). Separação por tipo de serviço em andamento — ver abaixo. |
| **Recurring Customer Stage** | Publicado, sem mensagens. OK. |
| **Lost Stage** | Publicado. Espera 2 dias → e-mail de feedback; check-in em 90 dias. OK. |
| **Spam Contact / DND Contact** | Publicados. OK. |

## Pipeline **Pool Leads** — ordem final

Confirmado ao vivo na Southern (13/10):

🆕 New Lead → **No Response - Follow Up** → 💬 In Communication → 📅 Scheduled → 💰 Quote Sent →
**No Show** → 🏆 Won - Weekly Pool Service → 🏆 Won - One Time Repair or Install →
🏆 Won - Pool Construction or Remodeling → 🔄 Recurring Customer → ❄ Not Qualified Stage → ❌ Lost → 🚫 Spam

Won por tipo de serviço: ficaram **3 etapas** (Weekly, One Time Repair or Install, Pool
Construction or Remodeling). O *Review Request* tem um gatilho por etapa e espera
30 / 7-8 / 45 dias conforme o tipo. O *Won Stage* (boas-vindas) só dispara em Weekly.

Como o dono usa (explicar nas calls): ligou e não falou → No Response; falou → In
Communication (nada é enviado); agendou visita → Scheduled (nada é enviado); mandou
orçamento → Quote Sent (follow-up sai); fechou → Won; cliente não estava → No-Show.

## Forms → pipeline (regra aplicada em todas as contas, `scripts/pp_forms.py`)

Todo form de lead tem **exatamente um** workflow publicado escutando. O que nenhum outro
escuta vai para o *Website Form Fill To Pipeline*. O Landing Page (form do site `go.*` e
das campanhas) fica com o *AdWords Form* onde ele está publicado; onde o AdWords está em
draft (Southern, Pool Shack para a cópia usada no site) vai para o Website Form Fill.

## 05 — Customer Reviews

- **Review Request**: condição por tipo de cliente (Won) com esperas diferentes —
  manutenção semanal ~**30 dias**, reparo/instalação ~**1 semana**, construção/reforma
  ~**6 semanas**. Valores finais definidos com cada cliente. Confirmado ao vivo: 3 gatilhos
  (um por etapa Won) com esperas de 30 / 7-8 / 45 dias.
- Review Response – Negative: a tarefa vinha com vencimento em 1970 (`{{right_now.hour}}`);
  corrigido para "vence agora" em todas as contas (13/10).
- Review Response – Positive: o SMS promete *"every referral earns you a free month of
  service"* — confirmar com cada cliente (ver docs/TODO.md).
- **Reputation → Settings → e-mail de review**: o default trazia **logo de outra empresa**.
  Já corrigido no snapshot (usa `{{custom_values.logo_url}}` ou fica em branco), mas contas
  criadas antes (como a Southern) precisam da correção manual.

## 09 — System

**SMS Customer Reply** (resposta a blast de reativação): remove `reactivation`, aplica
`new lead`, notificação interna (com usuário!) e move para a etapa certa do pipeline.

## Depois das edições

Republicar em lote os workflows que foram para draft durante a revisão e testar o form
do site (lead de teste deve sair com tags e cair em New Lead).

---

## Checklist de auditoria por sub-conta (o que `pp_audit.py` procura)

- Nome de **outra** empresa em qualquer mensagem (outras sub-contas, exemplos do snapshot
  como *Crystal Clear Pools*, *Clear Pool Solution*, *Pool Smart OC*, e "Pool Profits").
- `{{custom_values.*}}` usado mas vazio/inexistente na sub-conta (mensagem sai quebrada).
- Link de calendário/booking sendo enviado.
- Notificação interna / tarefa / atribuição sem usuário.
- Gatilho apontando para form/etapa/calendário que não existe.
- Dois workflows publicados com o mesmo gatilho (envio em dobro).
- Workflow publicado que adiciona a outro que está em draft.
