# Layout do repositório marketplace

O manifesto `marketplace.json` deve ficar em `.claude-plugin/` na raiz do repositório marketplace.

```text
claude-plugins/
├── .claude-plugin/
│   └── marketplace.json
└── plugins/
    └── github-workflow/
        ├── .claude-plugin/plugin.json
        ├── skills/
        ├── agents/
        ├── scripts/
        └── templates/
```

Copie o conteúdo da raiz deste plugin para `plugins/github-workflow/`.
