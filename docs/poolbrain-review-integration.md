# Pool Brain → GHL: pedido de review quando o trabalho termina (Clear Pool / Derek, 27/10)

Pedido do Derek: disparar o pedido de review quando a OS (work order) passa de aberta para concluída no Pool Brain, como
faz o Applause (parceiro oficial do Pool Brain).

## O que o Pool Brain oferece (docs: https://prodapi.poolbrain.com/OpenAPI/docs/, lido 27/10)
- **Webhooks** (no ar desde fev/2026; Settings > API > Webhooks, toggle "Use Webhooks", URL HTTPS, assinatura HMAC
  `X-Webhook-Signature`, retentativas 5/10/30 min). Eventos: `customer.created`, `customer.status.updated`,
  `job.one_time.created`, `job.one_time.deleted`, `job.one_time.schedule.changed`, `technician.route.changed`,
  `alert.triggered` (só quando um job concluído tem alerta aberto).
- **Não existe evento "job concluído"** em geral (nem de visita semanal). Os payloads trazem ids e nomes, sem telefone/e-mail.
- **Open API REST** (desde 03/2024; GET e POST de clientes, contatos, propriedades, jobs, cotações): chave sob pedido
  (team@poolbrain.com), sem preço publicado.

## Conclusão
- Exatamente como o Applause (no instante em que a OS fecha): **não dá com o que é público hoje**. O Applause é parceiro.
- Possível com a API REST, se ela listar jobs concluídos com data de conclusão e o cliente tiver telefone/e-mail:
  um serviço pequeno nosso consulta a API a cada hora e manda os concluídos para um webhook de entrada do GHL (tag
  `job completed`), que dispara o pedido de review com o NPS gate. Atraso de até 1 h.
- Sem Pool Brain (só GHL, já disponível): review X dias depois do card entrar em Won (One Time Repair: 2-3 dias; weekly:
  30 dias) + a cada 6 meses para quem não deixou review; clientes de garantia entram por tag manual.

## Perguntas para o Pool Brain (team@poolbrain.com)
1. Chave da Open API para a conta da Clear Pool: custo? exige plano?
2. Há endpoint de jobs concluídos (one-time e recorrentes) com data/hora de conclusão, filtrável por data?
3. O cliente vem com telefone e e-mail nesse endpoint (ou em outro)?
4. Está previsto um webhook `job.completed` (qualquer job)? É o que o Applause usa?
5. Limite de requisições.
