# Indicadores de atividade no GitHub

A automação gera três cards em português (`assets/github-analytics.svg`) e inglês (`assets/github-analytics.en.svg`), diariamente às 09:17 UTC (06:17 em São Paulo). Também pode ser executada em Actions → Atualizar GitHub Analytics → Run workflow. Alterações no script ou workflow disparam uma execução ao serem enviadas ao GitHub.

## Critérios

Todos os indicadores consideram os últimos 12 meses, incluindo o dia atual, com datas em UTC e somente repositórios públicos visíveis à consulta.

- **Pull requests mesclados:** PRs de autoria de `yada071` mesclados dentro do período, independentemente da data de abertura. Consulta de busca do GitHub com `author:`, `is:merged`, `is:public` e `merged:`.
- **Pull requests revisados:** PRs distintos associados a contribuições de revisão reconhecidas pelo GitHub no período. Revisões repetidas do mesmo PR contam uma vez. Não equivale ao número de comentários, aprovações ou eventos de revisão.
- **Repositórios com contribuições:** união, sem duplicação, dos repositórios com commits reconhecidos pelo GitHub, issues abertas, PRs abertos ou contribuições de revisão no período. Repositórios próprios também contam. Criar um repositório, receber estrelas ou apenas comentar não conta.

As conexões de issues, PRs e revisões são paginadas até o final. A API limita a consulta de repositórios com commits a 100; se esse limite for atingido, a execução falha em vez de publicar uma contagem potencialmente incompleta. Exclusões de recursos, regras de atribuição e atrasos de indexação do GitHub podem afetar os valores. Os indicadores descrevem atividade, não qualidade de código ou produtividade.

## Execução

O workflow usa o token temporário do GitHub Actions, sem token pessoal. Precisa de permissão de escrita para atualizar os dois SVGs. Proteções da branch podem impedir o commit automático.

Localmente, configure `GH_TOKEN` no ambiente e execute `python scripts/github_analytics.py`. Não coloque tokens no código nem no repositório.

Falhas de consulta preservam a última imagem gerada. A imagem inicial mostra um travessão e “Aguardando primeira atualização”, sem inventar números. `--placeholder` recria esse estado e deve ser usado apenas na configuração inicial.

## Validação local

Execute `python -B -m unittest discover -s scripts -p "test_*.py"`. Os testes usam respostas simuladas para verificar paginação, deduplicação, filtros de visibilidade, datas e os SVGs dos dois idiomas.
