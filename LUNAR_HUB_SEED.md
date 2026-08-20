# Seed: projeto separado — Hub Lunar (não Lunar Ice Intelligence)

> STATUS: **não iniciado**. Nenhum repositório, nenhum deploy, nenhuma linha de
> código. Este arquivo é um backlog de referência, não uma spec para implementar
> em ordem. Última atualização: 2026-08-11 (pós-aplicação da "Regra zero" — ver
> seção final).

## Antes de abrir este arquivo de novo

> **Atualização 2026-08-20**: a trava #1 original ("resolver Lunar Ice
> Intelligence primeiro") está satisfeita — P3, P6 completos; Fase 9 encerrada
> por decisão do usuário (não vai submeter a journal, DOI/preprint já prontos);
> deps de frontend (React 19) confirmadas em dia. P7 (OOD) segue como decisão
> em aberto mas de baixa urgência (não bloqueia mais nada). Regra removida.
> Travas #2 e #3 continuam valendo integralmente.

Ordem obrigatória, não negociável:

1. **Primeiro deploy do hub antes de qualquer decisão nova de arquitetura.**
   `npm create astro@latest` → 1 página → deploy público na Vercel. Nada de
   Tailwind, i18n, CMS, CI ou automação de conteúdo antes disso existir.
2. **Proibido elaborar seção nova neste arquivo** até o passo 1 estar feito. Link ou
   ideia nova = 1 linha na seção "Backlog não-priorizado" no fim do arquivo. Sem
   parágrafo, sem "como isso conecta com o pilar X". Isso existe para quebrar o
   padrão observado nesta conversa: 6 mensagens seguidas de "adicione mais isso",
   zero linhas de código.

Diagnóstico completo do porquê dessa mudança está em `[[lunar_hub_seed]]`
(memória) e na resposta "Regra zero" desta sessão — resumo: o documento estava
crescendo (371 linhas, 7 pilares, stack completa, CMS, automação, paleta,
carrossel) sem nenhuma evidência de demanda e sem nenhum deploy — planejamento
como forma confortável de evitar tanto o artigo quase pronto quanto o risco de
publicar algo real.

### Regra para qualquer automação futura de busca ("/comando")

Se um dia existir um comando/agente que busca informação nova para este arquivo
automaticamente, ele **não pode driblar as 3 regras acima**. Constraints obrigatórias:

- Só escreve no "Backlog não-priorizado" (1 linha, sem elaboração) — nunca cria
  seção nova nem edita o MVP/stack.
- Bloqueado por completo enquanto o passo 2 (primeiro deploy) não existir — o
  comando deve recusar rodar, não só desencorajar.
- Não roda automaticamente/agendado — só sob pedido explícito, e no máximo pra
  processar links que você já trouxe, não para "descobrir" conteúdo novo sozinho.

Motivo de existir essa trava: otimizar a *busca* de informação não ataca o
gargalo real (é fácil demais acumular referência, difícil é fazer deploy) —
facilitar ainda mais a busca sem essas travas seria automatizar a fuga, não
corrigi-la. Antes de construir esse comando, cheque se o passo 2 já foi feito;
se não foi, a resposta é não construir o comando ainda.

## Decisão de escopo (mantida)

Hub lunar focado, não site generalista sobre o universo — compete direto com
Wikipedia/NASA/ESA e força superficialidade. Recorte editorial (Artemis,
economia, política, habitats) + link para o Lunar Ice Intelligence como prova de
competência técnica. **Isso valida a forma do conteúdo, não a demanda** — nenhuma
pessoa fora desta conversa validou que quer ler isso. Tratar como hipótese, não
como fato assumido.

## Escopo mínimo (MVP — o que de fato implementar primeiro)

Não os 7 pilares. **Três**, cortados deliberadamente:

1. **Missões** — timeline Apollo→Artemis II→III→IV + "o que aconteceu agora".
2. **Vozes da Lua** — 3 citações (Sagan/Newton/Einstein) como pull-quotes.
3. **Link de volta** — CTA para o Lunar Ice Intelligence como "ferramenta
   científica ao vivo".

Sem CMS, sem automação de conteúdo, sem carrossel, sem CI de Lighthouse, sem
verificação de completude i18n — tudo isso é v2+ e só se justifica com conteúdo e
leitores reais existindo primeiro. Um redeploy manual quando o conteúdo mudar é
suficiente até haver evidência de que vale automatizar.

Os pilares 3–6 (Habitats/túneis de lava, Infraestrutura água/energia/construção,
Economia lunar, Política/governança) ficam no backlog abaixo — pesquisados e
prontos, mas não fazem parte do que entra primeiro.

## Stack mínima para o MVP

- **Astro** + integração **React** (só se algo precisar de interatividade real —
  timeline da seção Missões). Sem MDX/content collections ainda: 3 seções cabem
  em componentes estáticos comuns.
- **Tailwind CSS** — paleta abaixo, sem mais que isso.
- **Hosting**: Vercel, mesmo padrão do Lunar Ice Intelligence.
- Nada de Framer Motion, Embla Carousel, i18n com lib externa, Octokit/rss-parser,
  Keystatic, Zod. Todos ficam no backlog — só entram quando o MVP estiver no ar e
  houver razão concreta (não hipotética) para cada um.

```css
--bg:            #f7fafc   /* branco levemente azulado, fundo principal */
--surface:       #ffffff   /* branco puro, cards/superfícies elevadas */
--primary:       #0ea5e9   /* azul principal (sky-500) — CTAs, links ativos */
--primary-dark:  #0369a1   /* azul escuro (sky-700) — texto sobre fundo claro, headers */
--accent:        #38bdf8   /* mesmo accent do Lunar Ice Intelligence — elo de marca */
--text:          #0f172a   /* slate-900 — texto principal, alto contraste sobre branco */
--text-muted:    #475569   /* slate-600 — texto secundário/legendas */
```

Regra de acessibilidade: texto de corpo sempre `--text`/`--text-muted` sobre
`--bg`/`--surface` (contraste AAA); `--primary`/`--primary-dark` só para destaque,
nunca bloco de leitura longo.

## Verificação (antes de considerar o MVP "no ar")

Checagem real, não aspiração — cada item é binário (passou/não passou):

- `npm run build` — zero erros
- URL pública da Vercel responde `200` (não só `localhost`)
- As 3 seções renderizam sem erro de console num navegador real, não só build
  verde
- O link de volta abre `lunar-ice.vercel.app` de verdade (não placeholder)
- Cada afirmação numérica/de missão na seção Missões tem fonte visível —
  checagem manual, não automatizável ainda
- Contraste `--text`/`--text-muted` sobre `--bg`/`--surface` passa AA (checagem
  única, ex. DevTools — não vira CI de Lighthouse, isso é v2+)

## Regra permanente de conteúdo (mantida)

Toda afirmação numérica ou de status de missão precisa de fonte com data —
Artemis muda de cronograma com frequência, ISRU de água ainda não confirmado,
reator nuclear ainda em desenvolvimento. Vale para o MVP e para tudo que vier
depois.

---

## Backlog não-priorizado (pesquisado, não implementar ainda)

Tudo abaixo é referência válida e verificada — só não é prioridade até o passo 2
("Antes de abrir este arquivo de novo") estar feito. Novos links entram aqui como
1 linha, sem elaboração.

**Pilares adiados**: Habitats/túneis de lava (Lunar Vertex, skylight Mare
Tranquillitatis 65m/36m); Infraestrutura (ISRU O₂ TRL6 140kg/ano/reator, água do
polo sul ainda não confirmada, reator de fissão NASA+DOE até 2030 <20MW,
manufatura in-situ arXiv 2408.05823); Economia lunar (PwC: US$72.7–88.5bi infra +
US$93.9–127.3bi receita 2026–2050); Política (Artemis Accords 70 signatários
jul/2026, Rússia/China fora, Senegal/Sérvia/Tailândia também no ILRS chinês).

**Missões — dados de apoio**: Artemis II voou e voltou 1–10 abr 2026
(Wiseman/Glover/Koch/Hansen); Artemis III reformulada (voo em órbita 2027, pouso
real fica pra Artemis IV/2028); VIPER revivido (Blue Origin, entrega 2027, drill
TRIDENT); PRIME-1; ispace ULTRA (2028); MAGPIE (ESA/ispace-Europe).

**Referências de arquitetura**: SpaceArchitect.org (HAVEN, Moon Village,
MoonFiber, FLEXhab) — https://spacearchitect.org/projects/. HAVEN — Lunar Port
and Base, Sabrina Kerber/TU Wien 2020 — https://repositum.tuwien.at/bitstream/20.500.12708/16324/2/Kerber%20Sabrina%20-%202020%20-%20HAVEN%20Lunar%20Port%20and%20Base%20design%20of%20a%20lunar%20arrival%20port...pdf .
LUNARK, SAGA Space Architects — https://www.saga.dk/projects/lunark .

**Vídeos**: "NASA Moon Base: Lunar Landers (August 2026 Update)", NASA+ —
https://www.youtube.com/watch?v=Sempwv5MPMQ . "Como será a primeira BASE LUNAR?",
PT-BR — https://www.youtube.com/watch?v=rrc7-DX7PUQ . "What we have Wrong about
Living on the Moon [SPACE ARCHITECTURE]", DamiLee —
https://www.youtube.com/watch?v=kwRSBcrpyj0 . "NASA FINALMENTE REVELA OS PLANOS
DA SUA BASE LUNAR", SpaceToday PT-BR (programa "Ignition Moon Base", 3 fases, 6
empresas) — https://www.youtube.com/watch?v=dY4kg3jsNMA .

**Citações**: Sagan (*Pale Blue Dot*, 1994) — placa Apollo 11 "we came in peace"
+ "Look again at that dot. That's here. That's home." Newton — menino catando
seixos na praia (não confundir com "se vi mais longe..."). Einstein — "I am only
passionately curious."

**Infra/segurança v2+ (só com conteúdo e leitores reais)**: content collections
MDX, CMS headless (Keystatic), GitHub Actions com Octokit+rss-parser abrindo PR
de conteúdo (nunca auto-merge), CSP restritiva, Dependabot, Framer Motion (mesma
lib do Lunar Ice Intelligence), Embla Carousel, i18n com `astro-i18next`.

**Estrutura técnica de longo prazo**: rotas separadas `/` editorial + link pro
Lunar Ice Intelligence (Opção B do plano original `zesty-brewing-firefly.md`) —
válido, mas só depois do MVP provar que há razão para crescer.
