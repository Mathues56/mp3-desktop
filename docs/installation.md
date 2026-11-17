# Instalação e build

No Windows, instale Python 3.12 ou superior com Tkinter. Para o estúdio de clipes, instale FFmpeg com os programas `ffmpeg`, `ffprobe` e `ffplay` funcionais no PATH. Execute cada um com `-version` para conferir. Na pasta do projeto:

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
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name MP3Desktop app.py
Get-FileHash .\dist\MP3Desktop.exe -Algorithm SHA256
```

O executável não é instalador nem é assinado. O arquivo de `dist` só deve ser distribuído após teste em Windows compatível. Nenhuma release foi publicada até agora.
