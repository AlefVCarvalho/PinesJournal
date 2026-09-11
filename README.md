# Pine's Journal

Aplicativo desktop compacto para Windows feito em **Python + Tkinter**, com persistência local em **SQLite** e geração opcional de um único `.exe` com **PyInstaller**.

## Alterações desta versão

- o ícone do aplicativo foi substituído pelo novo `app_icon.ico`, preservando transparência e contendo tamanhos de 16 a 256 px para melhor compatibilidade com o Windows;
- o calendário principal e o seletor de data agora começam a semana no **domingo**;
- tarefas podem receber **várias tags**;
- cada tag possui nome e cor escolhida pelo usuário;
- o botão `+ Nova` passou a se chamar `+ Tarefa`;
- foi adicionado o botão `+ Tag` para criar e excluir tags;
- as tags aparecem visualmente nas tarefas;
- foi adicionado um filtro independente por tag, incluindo `Todas as tags` e `Sem tag`;
- a pesquisa também encontra tarefas pelo nome das tags;

## Arquivos `.bat`

```text
PinesJournal.bat
```

Ao abrir o arquivo, há opções para preparar o ambiente, executar o aplicativo ou gerar o `.exe`. Também é possível chamar diretamente:

```text
PinesJournal.bat setup
PinesJournal.bat run
PinesJournal.bat build
```

### Preparar o ambiente

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt
```

### Executar em desenvolvimento

```powershell
py task_app.py
```

### Gerar o executável

```powershell
py -m PyInstaller --noconfirm --clean --onefile --windowed --name "Pine's Journal" --icon "app_icon.ico" --add-data "app_icon.ico;." --add-data "assets;assets" task_app.py
```

## Estrutura mínima recomendada do código-fonte

```text
task_app.py
app_icon.ico
requirements.txt
requirements-dev.txt
assets\        # somente se quiser usar os ícones auxiliares da interface
PinesJournal.bat  # opcional
```

Para o usuário final, depois do build, é possível distribuir somente:

```text
dist\Pine's Journal.exe
```