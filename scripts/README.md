# GitHub Analytics

O workflow `Atualizar GitHub Analytics` gera `assets/github-analytics.svg` diariamente às 09:17 UTC (06:17 em São Paulo). Também pode ser executado na aba Actions, em Run workflow. Ao enviar a configuração ao GitHub, a primeira execução é iniciada automaticamente.

Usa a API GraphQL do GitHub e o token temporário fornecido pelo Actions. Não exige criar um token pessoal. O workflow precisa de permissão de escrita para atualizar o SVG; regras de proteção da branch podem impedir o commit automático.

O total soma calendários anuais sem sobreposição desde a criação da conta. Os últimos 12 meses usam um intervalo móvel de calendário, incluindo o dia atual. Os números seguem os critérios e a visibilidade da API do GitHub; não representam todos os commits já realizados nem garantem acesso a contribuições privadas. O total inclui as contribuições da própria manutenção deste perfil.

Falhas de consulta encerram a execução e preservam a última imagem válida. A imagem inicial informa que os dados ainda não foram consultados.
