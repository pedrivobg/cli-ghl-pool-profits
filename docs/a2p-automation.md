# A2P / LC Phone / conta nova por API (10/11)

Pergunta do Pedro: dá para automatizar a criação de conta inteira (Business Profile, domínio, A2P) com app do
Marketplace / API?

## Resposta curta
- **API oficial (v2/v3, Marketplace app, PIT): não.** O spec público (`GoHighLevel/highlevel-api-docs`) não tem
  campos de A2P no `/locations`, nem brand/campaign/Trust Center, nem domínio de funil, nem encaminhamento de número.
  Existe pedido aberto "Automated A2P Registration" no ideas.gohighlevel.com. Um app do Marketplace teria os mesmos
  limites (só ganharia um token por sub-conta sem a private key manual: `/oauth/locationToken` com app de agência).
- **API interna (a que o próprio app usa, com o nosso token Firebase de agência): sim** para quase tudo. Achei os
  endpoints no código do Trust Center (`appcdn.leadconnectorhq.com/revex/phone-integration/<ver>/remoteEntry.js`,
  módulo `LocationTrustCenterV2`; host ISV em `static.leadconnectorhq.com/<ver>/js/*.js`: `ISV: …/isv_service`).
  Não é documentado: pode mudar sem aviso → `pp_a2p.py status` acusa quando quebrar.

## Endpoints (verificados ao vivo 10/11)
| Passo | Endpoint | Testado |
|---|---|---|
| Business Profile (A2P) | `PUT services /locations/{loc}` com `legalBusinessName`, `businessInformation {type, industry, registrationId: "EIN", registrationNumber, regions: ["USA_AND_CANADA"], businessNotRegistered}`, `authorizedRepresentative {firstName, lastName, email, phoneNumber, title, position}` | escrita em "test inc" + restaurado; Corolla gravada |
| Padrão das contas aprovadas | `industry: CONSUMER`, `position: CEO`, `title: CEO`, `type: Limited Liability Corporation`/`Corporation` | leitura de 60 contas |
| Dados da campanha | `GET backend /phone-system/twilio-accounts?entityId={loc}&entityType=LOCATION`; `PUT …/twilio-accounts?locationId={loc}` com `campaignDetails` (useCase LOW_VOLUME, useCaseDescription, sampleMessages, endUserConsent, optInMessage/Keywords/Method/ImageUrl, privacyPolicyUrl, termsAndConditionsUrl, checkboxStates) | Corolla gravada (modelo = Southern, campanha VERIFIED) |
| Status | mesmo GET: `compliance.standardRegistration {brandSid, brandData.status, campaignSid, campaignStatus, campaignErrors}`; `GET backend/isv_service /compliance/{companyId}/brands/{loc}`, `…/campaigns/{loc}`; `GET backend /phone-system/sub-account/is-a2p-registration-restricted/{loc}` | 60 contas |
| **Enviar** (pago) | `POST backend/isv_service /compliance/{companyId}/standard-registration/{loc}?brandType=standard` (sem corpo; usa os dois acima). High volume: `&standardBrandType=direct-standard`. Sole prop: `/compliance/{companyId}/sole-prop/{loc}?brandType=sole-prop` (OTP no celular). Reenviar brand: `POST …/resubmit-brand/{loc} {brandSid}`; campanha: `PUT /compliance/campaign/{loc}` | **não testado** (é o envio real; só com OK do Pedro) |
| Encaminhamento de número | `POST backend /phone-system/twilio-accounts?locationId= {number, forwardingNumber}` (o PUT com `forwardingNumbers` é ignorado) | Corolla e Blissful gravados e relidos |
| Comprar número | `GET backend /phone-system/numbers/location/{loc}/available?countryCode=US&firstPart=<DDD>&numberTypes=local` → `POST …/purchase {phoneNumber, countryCode, numberType: "local", locality, region, fingerprintId, skipLocationKYC: false, addressSid/bundleSid/stripe*: ""}` | busca ok; compra barrada na 1ª vez por KYC (`GUARD_LOCATION_NOT_KYC_VERIFIED`, status em `GET backend /phone-system/kyc-verification/status?entityId&entity=LOCATION`) |
| Domínio do site | `GET services /funnels/domain/?locationId=`; `POST /funnels/domain/validate {domain, locationId}` → `{state: CONNECTED}`; criar = `POST /funnels/domain`, ligar ao site = `POST /funnels/domain/attach-domain` (corpo ainda não visto) | leitura/validate ok |

O DNS (CNAME `go` → `sites.ludicrous.cloud`) continua do lado do cliente/registrador (Wix, GoDaddy…); SSL sai sozinho
depois que o GHL vê o DNS.

## Script
`scripts/pp_a2p.py`:
- `status --all` (só leitura) mostra, por conta: brand/campanha, números sem encaminhamento, campanha
  preenchida, campos do perfil faltando.
- `campaign -n "<conta>" [--apply]` monta a campanha a partir da Southern (troca razão social + site da
  privacy/terms do custom value `privacy_policy`).
- `forward -n … --to +1… [--apply]` grava o encaminhamento.
- `submit -n … --yes` faz o envio, depois de checar perfil + campanha e que nada foi enviado antes.

## Estado 10/11 (status --all)
- Sem envio e **com número**: Corolla (pronta, esperando SSL do go.corollapoolandspa.com + OK), Clear Conceptz (3 números,
  campanha vazia, cargo "Other"), Cleverblu (campanha ok, falta privacy/terms do site + pagamento, TODO 5).
- Sem envio e sem número: Rosebrook, Bonneville, WP Pools, Capital Lawn, West Coast (perfil sem EIN/tipo/setor), Bluebird,
  Pool Duck, Premier 1 (2), Summer Wave (sem EIN), Smart Chem (perfil vazio), Leisure (perfil vazio).
- Campanha recusada: Pool Profits (Sales) FAILED (High Risk, 30885). Dream Pools e Net Positive: VERIFIED com erro antigo.
- Números sem encaminhamento (pode ser intencional: IVR/usuários): Clean Co (4), Clear Conceptz (2), GID (3), Ponchos (3),
  Pool Palooza (2), Pool Profits (1), Pooly (4), Pool Keepers (1), Wrigley's (3), YardSpring (1), Corolla (1).

## SOP
Regras do Pedro para o envio (textos exatos, raiz do go., 3 números, revisão por IA): `docs/a2p-sop.md`.

## Pendências conhecidas
- Corolla: domínio CONNECTED no GHL e DNS certo, mas o SSL não sai nem apagando/adicionando de novo (10/11) → suporte do GHL ou outro subdomínio.
- Criar/ligar domínio por API (corpo do `POST /funnels/domain` e do `attach-domain`) para tirar esse passo do Frank.

## Próximos passos possíveis
1. Pedro aprova → `submit` na Corolla; acompanhar `status` até APPROVED/VERIFIED.
2. Testar `forward` numa conta com número de teste antes de usar em cliente.
3. Achar o POST de domínio (`/funnels/domain`) e o de compra de número interno → onboarding sem tela, exceto o DNS
   do cliente e o pagamento.
