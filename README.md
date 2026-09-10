# Pine's Journal

Aplicativo desktop compacto para Windows que combina **tarefas**, **calendário** e um **bloco de notas visual** em uma única janela local.

O projeto é desenvolvido em **Python + Tkinter**, usa **SQLite** para persistência local e pode ser distribuído como um único `.exe` com **PyInstaller**.

## Funcionalidades

### Lista de Tarefas
- criar, editar, concluir e excluir tarefas;
- descrição e data de conclusão opcionais;
- pesquisa por tarefa;
- filtros por status;
- destaque de tarefas atrasadas;
- exclusão automática de concluídas há mais de 7 dias.

### Calendário
- visão mensal;
- dias com tamanho uniforme;
- indicação de tarefas por data;
- clique em um dia para visualizar ou criar tarefas.

### Bloco de Notas
- lápis para rabiscos;
- borracha que remove o traço inteiro;
- caixa de texto;
- cursor de desenho personalizado;
- exportação para PNG;
- escolha da pasta padrão de exportação.

### Configurações
- temas Vinho, Azul, Verde e Grafite;
- iniciar com o Windows;
- manter a janela sempre no topo;
- confirmação antes de excluir tarefas;
- acesso às pastas de dados e de imagens.

## Requisitos para desenvolvimento

- Windows 10/11;
- Python 3.11 ou superior;
- Pillow.

## Instalação para desenvolvimento

Clone o repositório e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt
py task_app.py
```

Ou execute `setup_dev.bat` e depois `executar_codigo.bat`.

## Gerar o executável

Execute:

```text
build_exe.bat
```

O resultado será criado em:

```text
dist\Pine's Journal.exe
```

O executável é gerado com `--onefile --windowed`, portanto não abre uma janela de terminal durante o uso normal.