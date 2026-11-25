# ChatGPT Ads (OpenAI Conversions API) — ligações como conversão

Montado 25/11 na Passion Pool Care (Val, ClickUp `86bc6vqr9`). Receita para repetir em todo cliente de ChatGPT Ads.

## Peças
1. **Linha própria** do ChatGPT Ads na sub-conta (Passion: +1 629-290-1180) e o número na LP (Atif).
2. **GHL** (`scripts/pc_chatgpt_call.py plan|test|apply`, trocar `LOC`/`LINE`/`BASE` para outro cliente):
   - "ChatGPT Ads Call In - New Lead": cópia do "AdWords Call In - New Lead" da conta (avisos SMS/e-mail iguais),
     tags `new lead`/`chatgpt ads`/`chatgpt ads call in`, card com fonte "ChatGPT Ads - Call In". Gatilho: ligação de
     entrada na linha (qualquer status).
   - "ChatGPT Ads Call - OpenAI Conversion": gatilho ligação **atendida** (`call_status` completed) na linha → if/else
     sem spam/dnd/current customer → passo `custom_webhook` (POST JSON `contact_id`, `phone_raw`, `phone`, `email`,
     `validate_only`) para o n8n. O passo exige `saveResponse` (sem ele o PUT dá 400 "Save Response is required").
3. **n8n** "Passion - OpenAI CAPI (ChatGPT Ads calls)" (`MaPiK7MgXDfmSHiu`, webhook `oai-capi-passion-9d41e7b2c6`):
   normaliza o telefone (só dígitos, 10 → 1+10), SHA-256 em JS puro (o Code node bloqueia `crypto`) de telefone,
   e-mail (minúsculo) e contact id → `POST https://bzr.openai.com/v1/events?pid=<pixel>` com `Authorization: Bearer
   <chave>` e **User-Agent próprio** (sem ele o Cloudflare responde 403 "error code: 1010"). Evento `lead_created`,
   `action_source: phone_call`, `data.type: customer_action`, id = `call-<contact>-<minuto>` (retry não conta 2x).
   Falha (≥300) → e-mail "[URGENTE]" ao Pedro. A chave fica só no nó HTTP do n8n (nunca no repo/CRM).
4. **Teste**: `pc_chatgpt_call.py test` (cópias ZZ, avisos para o Pedro, webhook com `validate_only: true` → resposta
   `{"accepted_events":1}`; tudo apagado). Depois, 1 ligação real com a Val e conferir no ChatGPT Ads.

## Outro cliente
Novo pixel + chave da Val → duplicar o workflow n8n (trocar `pid`, chave e path do webhook) e rodar o script com a
location/linha do cliente. `oppref` só existe no clique da LP: ligação casa pelo telefone com hash.
