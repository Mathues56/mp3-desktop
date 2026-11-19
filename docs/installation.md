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

O executável Windows não é instalador nem é assinado. O arquivo de `dist` só deve ser distribuído após teste em Windows compatível; builds macOS são descritas abaixo.

## macOS

### Instalar uma release

Use o pacote correspondente ao processador do Mac:

- `MediaStudio-macos-arm64.zip` para Apple Silicon (M1 ou posterior).
- `MediaStudio-macos-x86_64.zip` para Intel.

O requisito declarado é macOS 15 (Sequoia) ou posterior; sistemas anteriores não são testados. Baixe o `.zip` e o `.sha256` com o mesmo nome. Na pasta dos downloads, valide o arquivo:

```sh
shasum -a 256 -c MediaStudio-macos-arm64.zip.sha256
```

Para Intel, use o nome do ZIP Intel. Extraia o arquivo no Finder, mova `MediaStudio.app` para `Aplicativos` e abra pelo Finder. O pacote contém o runtime Python, então o usuário não precisa instalar Python. O aplicativo vincula o servidor a `127.0.0.1`, abre a interface no navegador padrão e oferece **Configurações → Encerrar Media Studio**.

O pacote não contém FFmpeg ou FFprobe. Instale-os por uma distribuição de sua confiança, por exemplo `brew install ffmpeg`, e confirme ambos com `ffmpeg -version` e `ffprobe -version`. A [fórmula FFmpeg atual do Homebrew](https://formulae.brew.sh/formula/ffmpeg) declara GPL-3.0-or-later; o Media Studio não redistribui esses executáveis. O projeto FFmpeg descreve as [licenças e opções de build](https://ffmpeg.org/legal.html). O app procura nos prefixos Homebrew usuais arm64 (`/opt/homebrew/bin`) e Intel (`/usr/local/bin`), além do PATH.

Os arquivos de vídeo são importados pelo seletor nativo, organizados em projetos e cortados manualmente no player/timeline. A exportação de clipes é MP4 por FFmpeg. MP3 é baixado de uma URL HTTPS direta autorizada; extrair ou converter áudio de vídeo para MP3 não está implementado.

As builds públicas atuais não têm assinatura Developer ID nem notarização Apple. O Gatekeeper pode avisar sobre desenvolvedor não identificado ou impedir a abertura. Não desative nem contorne as proteções do macOS; uma distribuição para uso geral exige assinatura e notarização verificadas. O workflow de build testa startup, API local e exportação sintética no runner, mas ainda não valida uma abertura interativa pelo Finder ou os diálogos em um Mac físico.

### Executar do código-fonte no macOS

Use Python 3.12 ou superior com Tkinter (confirme com `python3 -m tkinter`) e instale FFmpeg/FFprobe. Na pasta clonada do repositório:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e . -r requirements-dev.txt -r requirements-build.txt
brew install ffmpeg
python -m unittest discover -s tests -v
ruff check app.py mp3_desktop tests
ruff format --check app.py mp3_desktop tests
python app.py
```

Para gerar um `.app` local, execute PyInstaller no Mac da arquitetura desejada. Em Apple Silicon, use `--target-architecture arm64`; em Intel, `--target-architecture x86_64`. O workflow `.github/workflows/macos.yml` é a referência para builds, smoke test, ZIP e checksum. Não inclua FFmpeg no pacote sem verificar a licença e a configuração de build do binário específico.
