# Gerenciador de Vendas (Python)

Aplicação desktop simples para Windows e Linux, feita com Python, Tkinter e SQLite.

## Funcionalidades
- Editar quantidades no carrinho e aplicar desconto percentual antes de finalizar a venda.
- Consultar o histórico com filtros por período, pagamento e artigo, e exportar os resultados em CSV.
- Consultar detalhes de cada venda, incluindo anulações e descontos; anular ou apagar uma venda selecionada no histórico.
- Consultar relatórios de rendimentos por dia, mês, ano ou período personalizado, com faturação, custos, lucro bruto, margem, descontos, ticket médio, artigos mais vendidos, métodos de pagamento e desempenho diário.
- Repor a aplicação através de uma opção na aba Início, com dupla confirmação; remove produtos e vendas, limpa o carrinho, repõe o limite de stock baixo e reinicia os IDs.
- Mostrar um ecrã inicial de apresentação centrado no ecrã por 4 segundos antes de abrir a janela principal.
- Configurar o limite de stock baixo e filtrar a lista de artigos por esse limite.
- Ver indicadores: vendas de hoje, número de vendas, artigos, unidades em stock e artigos com stock baixo.
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

Nas próximas versões, os registos ficam numa pasta própria do utilizador, independente da localização do programa:
- Windows: `%LOCALAPPDATA%\VendeBem\gerenciador_vendas.db`
- Linux: `~/.local/share/VendeBem/gerenciador_vendas.db` (ou `$XDG_DATA_HOME/VendeBem/gerenciador_vendas.db`, se essa variável estiver configurada)

Para fazer uma cópia de segurança, feche o programa e copie o ficheiro `gerenciador_vendas.db` dessa pasta para um local seguro. Para restaurar, feche o programa e substitua o ficheiro pela cópia.

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
