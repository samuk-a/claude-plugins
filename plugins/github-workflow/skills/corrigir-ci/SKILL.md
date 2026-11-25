---
name: corrigir-ci
description: Diagnostica falhas de GitHub Actions de um PR e pode preparar correção local sem commit ou push.
argument-hint: "<github_pull_request_url>"
disable-model-invocation: true
---

Investigue `$ARGUMENTS`.

1. Validar URL, remote e `gh auth status`.
2. Consultar `gh pr view`, `gh pr checks`, `gh run list` e `gh run view`.
3. Não imprimir secrets ou tentar recuperar valores de secrets.
4. Classificar a falha: código, teste instável, ambiente, serviço externo, permissão ou configuração.
5. Reproduzir localmente quando possível, sem alterar configurações automaticamente.
6. Se a causa for código e a working tree estiver limpa, pode preparar uma correção local mínima.
7. Não desabilitar testes, reduzir critérios, ignorar checks ou alterar workflow para mascarar falha.
8. Não fazer commit, push, comentário, aprovação ou merge.
9. Apresentar diff, testes e causa provável; solicitar orientação para qualquer publicação.
