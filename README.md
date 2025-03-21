# data-Injector

O DataInjector é um aplicativo Python que automatiza o processamento de arquivos .zip contendo dados estruturados. Ele realiza a extração, validação e injeção de registros em um banco de dados, garantindo integridade e consistência dos dados.

Fluxo do Aplicativo

1. Recebimento e Extração do Arquivo
O usuário faz o upload de um arquivo .zip.

O sistema extrai o conteúdo, que contém dois arquivos .txt:

Um arquivo com o nome base (exemplo: rl_procedimento_origem.txt).

Outro arquivo com "_layout" no nome (exemplo: rl_procedimento_origem_layout.txt).

O sistema identifica e separa os arquivos corretamente.

2. Leitura do Arquivo de Layout

O sistema lê o arquivo _layout.txt, que contém a estrutura dos dados.

Ele identifica:

Nome das colunas.

Tipos de dados esperados para cada coluna.

3. Validação do Layout com o Banco de Dados

O sistema busca no banco a tabela correspondente ao nome do arquivo base (rl_procedimento_origem).

Obtém a estrutura da tabela (nomes e tipos de colunas).

Compara com a estrutura descrita no arquivo _layout.txt.

Se houver divergências (nome da coluna diferente, tipo de dado incompatível), o sistema retorna um erro.

4. Comparação dos Dados com o Banco

Se a estrutura for válida, o sistema extrai todos os dados da tabela do banco.

Lê o arquivo base (rl_procedimento_origem.txt), que contém os novos dados.

Compara os dados do arquivo com os dados existentes na tabela.

Identifica os registros novos ou atualizados.

5. Inserção dos Novos Dados

Os dados novos ou atualizados são inseridos na tabela do banco.

O sistema mantém um log das inserções e atualizações.

Pontos Importantes

Tratamento de Erros

O sistema lida com erros de compatibilidade de layout.

Se o arquivo _layout.txt estiver incorreto, o processo é interrompido.

Se houver problemas com os dados (como valores incompatíveis com os tipos das colunas), o sistema registra e trata os erros.
