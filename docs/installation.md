# Instalação e build

No Windows, instale Python 3.12 ou superior com Tkinter. A interface padrão abre no navegador local; Tkinter fornece os seletores nativos de arquivos. Para o estúdio de clipes, instale FFmpeg com `ffmpeg` e `ffprobe` funcionais no PATH. `ffplay` só é necessário para a interface antiga executada com `app.py --classic`. Confira os programas necessários com `-version`. Na pasta do projeto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe app.py
```

Para testes e build:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\ruff.exe check app.py mp3_desktop tests
.\.venv\Scripts\ruff.exe format --check app.py mp3_desktop tests
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --collect-data mp3_desktop --name MP3Desktop app.py
Get-FileHash .\dist\MP3Desktop.exe -Algorithm SHA256
```

O executável não é instalador nem é assinado. O arquivo de `dist` só deve ser distribuído após teste em Windows compatível. Nenhuma release foi publicada até agora.
