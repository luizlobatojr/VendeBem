# VendeBem — Gerenciador de Vendas

Aplicação desktop simples para Windows e Linux, feita com Python, Tkinter e SQLite.

## Funcionalidades
- Editar quantidades no carrinho e aplicar desconto percentual antes de finalizar a venda.
- Consultar o histórico com filtros por período, pagamento e artigo, e exportar os resultados em CSV.
- Consultar detalhes de cada venda, incluindo anulações e descontos.
- Configurar o limite de stock baixo e filtrar a lista de artigos por esse limite.
- Ver indicadores: vendas de hoje, número de vendas, artigos, unidades em stock e artigos com stock baixo.
- Guardar os dados localmente numa base de dados SQLite (`gerenciador_vendas.db`).

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

### Criar atalho na Área de Trabalho

Na pasta do programa, execute:

```bash
sh criar_atalho_linux.sh
```

O atalho **VendeBem** será criado na Área de Trabalho com o logo do programa.

## Executar no Windows
1. Instale Python 3 a partir do site oficial: https://www.python.org/downloads/
2. Durante a instalação, marque **Add Python to PATH**.
3. Extraia o ZIP.
4. Abra a pasta e faça duplo clique em `executar_windows.bat`, ou execute no terminal:
   ```bat
   py app.py
   ```

### Criar atalho na Área de Trabalho

Na pasta do programa, dê duplo clique em `criar_atalho_windows.vbs`. O atalho
**VendeBem** será criado na Área de Trabalho com o logo do programa.

Mantenha a pasta do programa no mesmo local depois de criar o atalho. O atalho
inicia o programa a partir dessa pasta, onde também fica o ficheiro de dados
`gerenciador_vendas.db`.

## Criar um executável para Windows (opcional)
Dentro do terminal na pasta do projeto:
```bat
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --onefile --windowed --name GerenciadorDeVendas app.py
```
O executável será criado em `dist\GerenciadorDeVendas.exe`.

**Nota:** a base de dados é criada na pasta de execução do programa. Faça cópias de segurança regulares do ficheiro `gerenciador_vendas.db`.
