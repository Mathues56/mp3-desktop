# MP3 Desktop — Media Studio

Aplicativo local em português para baixar **arquivos MP3 publicados para download direto e autorizado** e criar clipes MP4 de vídeos locais. A interface padrão abre no navegador com HTML, CSS e JavaScript; o núcleo funciona sem API ou conta externa.

## Funcionalidades

- Download em streaming com progresso, velocidade e estimativa quando o servidor informa o tamanho.
- Cancelamento; pausa e retomada quando o servidor anuncia suporte a `Range`.
- Nome de arquivo seguro, proteção contra sobrescrita e limite configurável (500 MB por padrão).
- Histórico SQLite e abertura da pasta de downloads.
- Sem cookies, contas, extração de streaming ou conversão de formatos.
- Projetos locais com nome e descrição; vídeos podem ser associados a eles sem duplicar arquivos.
- Importação em lote de vídeos locais MP4, MKV, MOV, WebM e AVI com metadados lidos pelo FFprobe.
- Intervalos manuais e fila persistente de exportação MP4 com presets original, 9:16, 16:9 e 1:1.
- Player local embutido com busca por bytes, controles de reprodução e marcação de entrada/saída.
- Faixas V1 e A1 para visualizar os intervalos salvos; a faixa A1 representa o áudio incorporado ao vídeo de origem.
- Processamento sequencial em segundo plano usando FFmpeg.

## Requisitos

Windows 10/11 e Python 3.12+ para executar do código-fonte. A interface abre no navegador padrão; Tkinter fornece os seletores no Windows. Para edição de vídeo, instale **FFmpeg e FFprobe** no PATH. FFplay só é necessário para a interface Tkinter antiga (`app.py --classic`).

O workflow macOS compila pacotes `.app` em runners Apple Silicon e Intel, executa os testes e faz um smoke test de inicialização, importação, edição e exportação. Os pacotes só são publicados após esses passos passarem. Isso ainda não equivale a validação em Finder num Mac de usuário, assinatura Developer ID ou notarização Apple.

## Instalação no Windows

Ainda não há instalador Windows validado. Para executar do código-fonte:

```powershell
cd <CAMINHO_DO_PROJETO>
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe app.py
```

Python 3.12 também funciona: troque `py -3.13` por `py -3.12`.

Também é possível abrir `abrir-local.cmd` com dois cliques. Mantenha o terminal aberto enquanto usar a interface no navegador. Para a interface Tkinter anterior, execute `python app.py --classic`.

## Instalação no macOS

A release macOS `v0.1.2`, validada para Apple Silicon e Intel pelo workflow de build e smoke test, está disponível em [GitHub Releases](https://github.com/Mathues56/mp3-desktop/releases/tag/v0.1.2). Escolha o ZIP conforme o processador:

O requisito mínimo declarado é macOS 15 (Sequoia); versões anteriores não são testadas. Para edição de vídeo, FFmpeg e FFprobe precisam estar instalados separadamente. O pacote inclui o Python da aplicação e não exige instalação do Python no Mac.

- `MediaStudio-macos-arm64.zip`: Apple Silicon (M1 ou posterior).
- `MediaStudio-macos-x86_64.zip`: Intel.

Descompacte o arquivo e mova `MediaStudio.app` para `Aplicativos`; abra pelo Finder. Python não é necessário para o pacote. O aplicativo inicia o servidor local em `127.0.0.1`, abre a interface no navegador padrão e pode ser encerrado em **Configurações → Encerrar Media Studio**. O encerramento cancela tarefas ativas; exportações pendentes permanecem no histórico.

O pacote não inclui FFmpeg. Para importar e exportar vídeo, instale FFmpeg e FFprobe separadamente, por exemplo com `brew install ffmpeg`, e confirme `ffmpeg -version` e `ffprobe -version`. O app procura também nos caminhos padrão do Homebrew (`/opt/homebrew/bin` e `/usr/local/bin`). A [fórmula FFmpeg do Homebrew](https://formulae.brew.sh/formula/ffmpeg) declara GPL-3.0-or-later; ela é instalada e distribuída pelo próprio Homebrew, não pelo Media Studio. O projeto FFmpeg explica as [licenças e opções de build](https://ffmpeg.org/legal.html); verifique os termos da distribuição escolhida antes de usar.

Os downloads do aplicativo são apenas para URLs HTTPS que entregam diretamente um MP3 autorizado. O editor importa vídeos locais e exporta clipes em MP4; conversão de vídeo para MP3 não está implementada. Para áudio, use o download MP3 direto.

O pacote não tem assinatura Developer ID nem notarização Apple. O Gatekeeper pode avisar que o desenvolvedor não foi identificado ou impedir a abertura; não desative as proteções do macOS. Uma distribuição pública sem esses certificados não deve ser apresentada como instalação confiável de uso geral. Veja [instalação e build](docs/installation.md) para requisitos, limitações e fluxo de desenvolvedor.

## Uso

1. Copie uma URL HTTPS que entregue diretamente um MP3 e cujo download seja permitido.
2. Escolha a pasta e clique em **Baixar MP3**.
3. Acompanhe a transferência; use **Pausar** apenas quando o servidor oferecer retomada.
4. Consulte **Histórico** ou **Abrir pasta** após a conclusão.

Para vídeo, abra **Projetos** e crie um projeto para organizar os arquivos locais, ou importe vídeos sem projeto. No **Editor de clipes**, reproduza o vídeo no player, navegue pela posição, use **Marcar entrada** e **Marcar saída**, ou informe os tempos diretamente. As faixas V1/A1 mostram os intervalos salvos sobre a mesma fonte. Em **Exportação**, escolha pasta, proporção e qualidade CRF para processar o intervalo selecionado.

A interface local usa a paleta verde-azulada da referência fornecida (#04222B, #0A3D4A, #10606F, #1D8B94, #4FB8B4, #98D8D0 e #E2F4F0). Nenhuma fonte ou imagem de terceiros é baixada. As páginas de transcrição e IA informam que esses recursos ainda não estão disponíveis; métricas mostram apenas contagens e tamanhos calculados dos dados locais.

## Como contribuir

Contribuições são bem-vindas. Leia [CONTRIBUTING.md](CONTRIBUTING.md), abra uma issue para discutir mudanças grandes e envie uma pull request com o problema, a solução e os testes executados. Os modelos de issue e pull request estão em `.github/`. Não inclua áudio, vídeo, credenciais ou URLs privadas nos exemplos.

Para um teste legal, use um MP3 disponibilizado por você mesmo em um servidor HTTPS ou um arquivo de exemplo cujo autor permita o download direto. Nenhuma URL de terceiros é embutida porque disponibilidade e licença podem mudar.

## Design visual

A interface padrão usa `mp3_desktop/web_assets/index.html`, `app.css` e `app.js`. As cores vêm da referência enviada: fundo azul-petróleo, painéis em teal e realce menta. A navegação prioriza downloads, transferências, projetos, clipes e exportação; páginas secundárias ficam em “Mais”, e os detalhes de um projeto são abertos pela biblioteca. Formulários, estados vazios, foco de teclado e layout responsivo também ficam nesses arquivos. A interface Tkinter anterior permanece disponível em `app.py --classic`, com seus estilos em `mp3_desktop/design.py`.

## Desenvolvimento

```powershell
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
ruff check app.py mp3_desktop tests
ruff format --check app.py mp3_desktop tests
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --onefile --windowed --collect-data mp3_desktop --name MP3Desktop app.py
```

O executável Windows gerado fica em `dist/MP3Desktop.exe`. Para macOS, veja a seção abaixo e [instalação](docs/installation.md). Consulte também [arquitetura](docs/architecture.md) e [contribuição](CONTRIBUTING.md).

### Desenvolvedores macOS

Execute em um Mac com Python 3.12+, Tkinter e FFmpeg/FFprobe. O app do usuário não precisa de Python; esta seção é apenas para executar e empacotar o código-fonte:

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

O workflow `.github/workflows/macos.yml` constrói e valida separadamente arm64 (`macos-15`) e x86_64 (`macos-15-intel`). Para gerar localmente, execute no Mac da arquitetura desejada:

```sh
python -m PyInstaller --noconfirm --windowed --collect-data mp3_desktop --name MediaStudio --osx-bundle-identifier org.mediastudio.desktop --target-architecture arm64 app.py
```

Troque `arm64` por `x86_64` num Mac Intel. A build local não assina nem notariza o app. Não inclua FFmpeg no pacote sem auditar a licença e a configuração exatas do binário distribuído.

## Limitações e perguntas frequentes

- **Links de plataformas de vídeo funcionam?** Não. A URL precisa responder com bytes MP3 diretamente.
- **Por que a pausa está indisponível?** O servidor não anunciou `Accept-Ranges: bytes`.
- **A estimativa é precisa?** É aproximada e depende de `Content-Length` e da velocidade corrente.
- **Um download interrompido após fechar o app é retomado?** Não. A retomada funciona somente na sessão atual.
- **Há downloads simultâneos?** Não; um por vez.
- **O formato é verificado?** Cabeçalho HTTP e assinatura inicial são verificados, mas não há decodificação integral do áudio.
- **O vídeo toca dentro do app?** Sim, no navegador local. Contêineres e codecs reproduzíveis dependem do navegador instalado; FFmpeg continua responsável pela exportação.
- **Posso editar áudio independente, volume ou sincronização?** Ainda não. A faixa A1 mostra o áudio embutido na fonte e acompanha os cortes de vídeo.
- **Há detecção automática ou IA?** Não. A edição de clipes é manual nesta versão; nenhuma chave de API é solicitada.
- **O que acontece ao excluir um projeto?** A associação é removida; vídeos e intervalos de edição permanecem no dispositivo.
- **Arrastar e soltar vídeos funciona?** Ainda não; use o seletor de arquivos com seleção múltipla.
- **Vídeos de quatro horas foram validados?** Não. FFmpeg processa em fluxo, mas desempenho e espaço em disco dependem do arquivo e da máquina.
- **O macOS está validado?** O workflow testa o app empacotado e exporta um clipe sintético em runners arm64 e x86_64. Finder, diálogos nativos interativos e Macs físicos ainda precisam de validação manual; assinatura Developer ID e notarização permanecem ausentes.

Veja [solução de problemas](docs/troubleshooting.md) e a [especificação independente do editor](docs/editor-architecture.md). Use apenas materiais que você tenha direito de baixar. O aplicativo não concede direitos sobre nenhum conteúdo.

## Projeto aberto

Licença [MIT](LICENSE). Consulte [segurança](SECURITY.md), [código de conduta](CODE_OF_CONDUCT.md) e [guia de contribuição](CONTRIBUTING.md).

**Roadmap:** refinar edição em múltiplas trilhas, adicionar áudio independente e avaliar sugestões locais de clipes e provedores de IA. As releases macOS só são publicadas após o workflow de build e smoke test; assinatura/notarização e validação em Macs físicos continuam pendentes. Os itens futuros não são compromissos de prazo.
