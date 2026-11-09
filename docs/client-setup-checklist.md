# Checklist padrão de leads por cliente (Val, 09/11)

Pedido da Val: toda vez que ela pedir um form novo para um cliente (e antes de lançar campanha), fazer também uma
checagem rápida da conta inteira. Ferramentas: `pp_notify_map.py <loc>` (linhas, usuários, quem recebe cada aviso —
só leitura), `pp_audit.py` / `pp_ready.py` (dump), `pp_source_audit.py` (tags de origem). Pool Duck: `GHL_AGENCY=poolduck`.

Resultado vai para a Val no ClickUp em formato curto (✅ ok / ⚠️ corrigido / ❓ pergunta), uma linha por item.

## 1. Telefones
- [ ] Cada número da conta (`/phone-system/numbers`): para onde toca — encaminhamento, IVR (`inboundCallService`) ou
      usuários. Nenhuma linha que não toca ninguém.
- [ ] Linhas de anúncio (Google Ads/FB/LSA) do mesmo jeito que a linha principal (Pool Duck: pelo menu principal).
- [ ] IVR: todo ramo conecta alguém (usuário ou número), sem loop (não ligar para número do próprio IVR), recado de voz
      e tag `missed call` dentro do IVR (com IVR as ligações viram "completed").
- [ ] Missed-call text-back: nativo off **ou** é o único text-back da conta (não duplicar).
- [ ] Ligação de teste em cada linha (passo do Pedro): tocou, card/tags, aviso chegou.

## 2. Avisos (SMS / e-mail / tarefa)
- [ ] Todo workflow publicado que recebe lead (form do site, LP, Google Ads lead form, ligação de Ads, SMS de Ads, chat
      widget, Facebook) avisa a pessoa certa por SMS **e** e-mail e/ou tarefa.
- [ ] Destinatário é usuário desta conta (sem "Steve"/usuário de outra conta, sem `—`); telefone do usuário preenchido.
- [ ] Atribuição de contato (assign user / dono do card) para quem atende.

## 3. Forms e páginas
- [ ] Forms do site, das landing pages e do funil: cada um ligado a um workflow publicado (gatilho `form_submitted`
      com o id do form) → tags de origem, card no pipeline, aviso.
- [ ] Redirect para a página de obrigado (`redirectUrl` + `redirect_url`), telefone com seletor de país.
- [ ] Páginas com o número de rastreamento certo e o form certo.
- [ ] Google Ads Lead Form: gatilho `google_lead_form_submitted` publicado e form **Active** em Integrations (Pedro).

## 4. Tracking
- [ ] Tags de origem por canal (`pp_source_audit.py`), fonte do card.
- [ ] Conversões do Google Ads nos workflows (passo `google_adword`) quando a conta tem Ads ligado; tag/GTM nas páginas.

## 5. Workflows
- [ ] Nada publicado que veio de outra conta (nomes, números, usuários de outro cliente) — `pp_ready.py`.
- [ ] Todo publicado com gatilho ativo; re-entry como no modelo; tags usadas existem (`pp_tags_missing.py`).

## 6. Teste e fechamento
- [ ] Cópia "ZZ TEST" por cadeia nova (gatilho por tag, avisos trocados por tag), contato @example.com; apagar tudo.
- [ ] O que precisa de mão humana (ligação, envio real de form, tela do GHL/Google Ads) → passo a passo ao Pedro.
- [ ] Só dizer "ok" à Val depois de testado.
