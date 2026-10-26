# Gerenciador de Vendas (Python)

Aplicação desktop simples para Windows e Linux, feita com Python, Tkinter e SQLite.

## Funcionalidades
- Editar quantidades no carrinho e aplicar desconto percentual antes de finalizar a venda.
- Cadastrar custo, preço e stock por quilograma; vender quantidades em kg com precisão até ao grama.
- Consultar o histórico com filtros por período, pagamento e artigo, e exportar os resultados em CSV.
- Consultar detalhes de cada venda, incluindo anulações e descontos; anular ou apagar uma venda selecionada no histórico.
- Consultar relatórios de rendimentos por dia, mês, ano ou período personalizado, com faturação, custos, lucro bruto, margem, descontos, ticket médio, artigos mais vendidos, métodos de pagamento e desempenho diário.
- Repor a aplicação através de uma opção na aba Início, com dupla confirmação; remove produtos e vendas, limpa o carrinho, repõe o limite de stock baixo e reinicia os IDs.
- Mostrar um ecrã inicial de apresentação centrado no ecrã por 4 segundos antes de abrir a janela principal.
- Configurar o limite de stock baixo e filtrar a lista de artigos por esse limite.
- Ver indicadores: vendas de hoje, número de vendas, artigos, stock total em kg e artigos com stock baixo.
- Guardar os dados localmente numa base de dados SQLite, separada dos ficheiros do programa.
- Abrir a janela principal centralizada, com tamanho inicial de 1120 × 720 píxeis (adaptado a ecrãs menores).

## Requisitos
- Python 3.10 ou superior.
- Tkinter (normalmente incluído na instalação do Python).

## Executar no Ubuntu
1. Extraia o ZIP.
2. Abra o terminal dentro da pasta.
3. Se o Tkinter não estiver instalado, execute:
   ```bash
   sudo apt update
   sudo apt install python3-tk
   ```
4. Inicie:
   ```bash
   python3 app.py
   ```

## Executar no Windows
1. Instale Python 3 a partir do site oficial: https://www.python.org/downloads/
2. Durante a instalação, marque **Add Python to PATH**.
3. Extraia o ZIP.
4. Abra a pasta e faça duplo clique em `executar_windows.bat`, ou execute no terminal:
   ```bat
   py app.py
   ```

## Atualizar sem perder os dados
1. Feche o programa antes de atualizar.
2. Faça uma cópia de segurança da base de dados (os caminhos estão indicados abaixo).
3. Substitua os ficheiros do programa pela versão nova. Não apague a pasta de dados do utilizador.
4. Inicie a nova versão. Se encontrar uma base de dados antiga junto ao programa, ela será copiada automaticamente para a nova pasta de dados. O ficheiro antigo não será apagado.

Os registos ficam numa pasta própria do utilizador, independente da localização do programa:
- Windows: `%LOCALAPPDATA%\VendeBem\gerenciador_vendas.db`
- Linux: `~/.local/share/VendeBem/gerenciador_vendas.db` (ou `$XDG_DATA_HOME/VendeBem/gerenciador_vendas.db`, se essa variável estiver configurada)

Para fazer uma cópia de segurança, feche o programa e copie o ficheiro `gerenciador_vendas.db` dessa pasta para um local seguro. Para restaurar, feche o programa e substitua o ficheiro pela cópia.

### Vendas por peso

Todos os produtos são vendidos em quilogramas. Informe custo e preço por kg e mantenha o stock também em kg. No registo e na edição do carrinho, informe a quantidade, por exemplo `1,500` (ou `1,500 kg`); o total é calculado pela quantidade multiplicada pelo preço por kg. A precisão permitida é de três casas decimais (gramas). Os valores numéricos já cadastrados de stock e de vendas são mantidos sem conversão e passam a ser interpretados como kg.

### Atualização automática no Windows

No executável do Windows, abra a aba **Início** e clique em **Verificar e atualizar programa**. O programa consulta a Release mais recente deste repositório, baixa `GerenciadorDeVendas.exe` para a pasta de dados do utilizador, verifica o tamanho e o checksum SHA-256 quando publicado e substitui o executável depois de fechar. A base de dados permanece em `%LOCALAPPDATA%\VendeBem` e não é substituída. Esta opção não instala atualizações quando o programa é executado como código-fonte ou no Linux. A pasta de instalação precisa permitir escrita; se estiver em `Program Files`, execute o programa como administrador para atualizar.

Para publicar uma versão que possa ser instalada por este botão:
1. Atualize `APP_VERSION` em `app.py` para a versão nova, por exemplo `1.0.1`.
2. Crie e envie uma tag correspondente, por exemplo:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```
3. A GitHub Action compila o executável e publica-o como asset da GitHub Release. Builds da branch `main` e execuções manuais continuam disponíveis apenas como artifact do Actions.

## Criar um executável para Windows (opcional)
Dentro do terminal na pasta do projeto:
```bat
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --onefile --windowed --name GerenciadorDeVendas app.py
```
O executável será criado em `dist\GerenciadorDeVendas.exe`.

**Nota:** a primeira inicialização após esta alteração pode migrar a base de dados existente. Mantenha uma cópia de segurança antes de atualizar.

No histórico, selecione uma venda para a anular ou apagar. Apagar remove permanentemente o registo e os seus artigos do histórico, sem repor nem alterar o stock. Para manter o registo e repor o stock, use a opção de anulação.

O custo das mercadorias fica registado em cada venda para que os relatórios futuros não sejam alterados quando o custo do artigo for editado. Na primeira atualização com relatórios, os custos das vendas antigas são estimados com base no custo atual dos respetivos artigos.
