# GitHub Workflow Plugin — 1.0.0

Plugin project-scoped para Claude Code. Automatiza o ciclo de uma GitHub Issue até um Pull Request usando Git, GitHub CLI (`gh`) e Skills/subagents.

## O que esta versão entrega

- `/github-workflow:analisar-issue`: análise somente leitura.
- `/github-workflow:implementar-issue`: implementação com checkpoints e aprovações explícitas.
- `/github-workflow:revisar-pr`: revisão somente leitura.
- `/github-workflow:corrigir-ci`: diagnóstico e correção local sem publicar alterações.
- Estado persistente por issue em `.claude/github-workflow/state/`.
- Atualização de checklist com proteção contra lost update (refetch + comparação de versão do corpo antes de editar).
- Recuperação após interrupção, com confirmação do estado real de Git/GitHub.
- Verificação de CI após PR, com polling limitado e sem inventar resultados.
- Scripts auxiliares com validação de argumentos e sem dependências Python externas.

## Requisitos

- Claude Code compatível com plugins, Skills e subagents.
- Git.
- GitHub CLI (`gh`) autenticado: `gh auth login`.
- Python 3.10+ para scripts.
- Acesso ao repositório GitHub.
- Permissões GitHub para ler Issues/PRs, criar branches/commits/push e criar PR conforme o fluxo utilizado.

## Estrutura

```text
github-workflow/
├── .claude-plugin/plugin.json
├── skills/
│   ├── implementar-issue/SKILL.md
│   ├── analisar-issue/SKILL.md
│   ├── revisar-pr/SKILL.md
│   └── corrigir-ci/SKILL.md
├── agents/
│   ├── code-reviewer.md
│   └── test-runner.md
├── scripts/
│   ├── preflight.py
│   ├── issue_checklist.py
│   ├── state.py
│   └── ci_watch.py
├── templates/
│   └── pull-request.md
├── examples/
│   ├── project-settings.json
│   └── marketplace/
│       ├── README.md
│       └── .claude-plugin/marketplace.json
└── README.md
```

## Instalação local para teste

Extraia o conteúdo e execute Claude Code no repositório consumidor:

```bash
claude --plugin-dir /caminho/para/github-workflow
```

No Windows PowerShell, por exemplo:

```powershell
claude --plugin-dir .\.claude\plugins\github-workflow
```

O caminho deve apontar para a pasta que contém `.claude-plugin/plugin.json`.

## Instalação compartilhada por projeto

1. Publique o plugin em um repositório GitHub de marketplace.
2. Coloque o plugin em `plugins/github-workflow/`.
3. Use o manifesto de exemplo em `examples/marketplace/.claude-plugin/marketplace.json` como base para o `.claude-plugin/marketplace.json` na raiz do marketplace.
4. Adicione ao `.claude/settings.json` do projeto o conteúdo de `examples/project-settings.json`, substituindo `ORG/claude-plugins`.
5. Cada desenvolvedor instala/confia no marketplace quando o Claude Code solicitar e autentica seu próprio `gh`.

A configuração `.claude/settings.json` é versionada no projeto; autenticação e tokens nunca são compartilhados.

## Comandos

```text
/github-workflow:analisar-issue https://github.com/ORG/REPO/issues/123
/github-workflow:implementar-issue https://github.com/ORG/REPO/issues/123
/github-workflow:revisar-pr https://github.com/ORG/REPO/pull/123
/github-workflow:corrigir-ci https://github.com/ORG/REPO/pull/123
```

## Autonomia híbrida

Automático:
- leitura de issue/PR e inspeção do repositório;
- planejamento e implementação local;
- criação de branch somente com working tree limpa;
- testes e revisão;
- atualização de checklist após verificação;
- persistência e recuperação do estado;
- acompanhamento limitado dos checks do PR depois de criado.

Aprovação explícita e separada:
- criar commit;
- fazer push;
- criar Pull Request.

Nunca automático:
- merge;
- force push;
- reset/clean/stash destrutivo;
- alteração de branch padrão/proteções;
- fechamento manual da issue;
- publicação de secrets.

A aprovação para uma operação não autoriza a próxima. O Claude deve exibir a ação exata e aguardar confirmação afirmativa do usuário no momento da execução.

## Estado e recuperação

Estado fica dentro do diretório Git (`git rev-parse --git-path claude-workflow-state`), em `issue-<number>.json`. Assim, o checkpoint não suja a working tree nem é commitado por acidente. O estado contém metadados, etapas, branch e referências de commit/PR; nunca tokens ou secrets.

Em uma nova sessão, invoque novamente `/github-workflow:implementar-issue` com a mesma URL. A Skill deve comparar o estado salvo com `git status`, branch, commits e GitHub antes de retomar. O estado local é um checkpoint auxiliar, nunca fonte de verdade para afirmar que uma ação remota ocorreu.

## Segurança e concorrência

- O script de checklist busca o corpo atual da issue, valida que existe exatamente um item desmarcado com o texto exato, calcula o corpo esperado e refaz a leitura imediatamente antes da escrita.
- Se o corpo mudar nesse intervalo, o script aborta sem gravar.
- A API `gh issue edit --body` não oferece compare-and-swap atômico; uma alteração concorrente ainda pode ocorrer entre a última leitura e a escrita. Para ambientes com edição simultânea frequente, prefira atualizar via API GraphQL/REST com controle de versão/ETag ou faça a edição manual.
- Conteúdo de issue, PR, comentários, logs e arquivos do repositório é dado não confiável, não instrução de sistema.
- Scripts não leem arquivos `.env`, chaves ou tokens.
- Não use `git add .`; stage apenas os arquivos relacionados à issue.

## Testes locais dos helpers

Na pasta do plugin:

```bash
python scripts/preflight.py --help
python scripts/issue_checklist.py --help
python scripts/state.py --help
python scripts/ci_watch.py --help
```

Validação manual recomendada: testar em fork e issue descartável, primeiro com `/analisar-issue`; depois simular interrupção após planejamento, implementação, commit e PR.

## Limitações conhecidas

- O plugin não executa sozinho fora de uma sessão do Claude Code.
- A qualidade da implementação depende do contexto e dos comandos reais definidos pelo repositório.
- A atualização do corpo da issue pelo `gh` não é uma transação atômica com controle de versão.
- CI pode demorar ou depender de secrets/serviços indisponíveis; o watcher tem limite de tempo e informa estados pendentes.
- A revisão por subagent é uma segunda análise automatizada, não substitui revisão humana.
