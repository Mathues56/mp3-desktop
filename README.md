# MP3 Desktop — Media Studio

Aplicativo desktop em português para baixar **arquivos MP3 publicados para download direto e autorizado** e criar clipes MP4 de vídeos locais. O núcleo funciona sem API ou conta externa.

## Funcionalidades

- Download em streaming com progresso, velocidade e estimativa quando o servidor informa o tamanho.
- Cancelamento; pausa e retomada quando o servidor anuncia suporte a `Range`.
- Nome de arquivo seguro, proteção contra sobrescrita e limite configurável (500 MB por padrão).
- Histórico SQLite, abertura da pasta e temas claro e escuro.
- Sem cookies, contas, extração de streaming ou conversão de formatos.
- Importação em lote de vídeos locais MP4, MKV, MOV, WebM e AVI com metadados lidos pelo FFprobe.
- Intervalos manuais, seleção múltipla e fila persistente de exportação MP4 com presets original, 9:16, 16:9 e 1:1.
- Pré-visualização externa pelo FFplay no ponto escolhido da timeline; processamento sequencial em segundo plano.

## Requisitos

Windows 10/11 e Python 3.12+ para executar do código-fonte. Tkinter acompanha a instalação padrão de Python para Windows. Para vídeo, instale **FFmpeg, FFprobe e FFplay** funcionais no PATH. Linux e macOS ainda não foram validados.

## Instalação no Windows

Ainda não há executável validado nem página de Releases publicada. Para executar do código-fonte:

```powershell
git clone <URL_DO_REPOSITORIO> mp3-desktop
cd mp3-desktop
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe app.py
```

Se o projeto estiver numa pasta local, comece em `cd <PASTA_DO_PROJETO>` e ignore `git clone`. Python 3.12 também funciona: troque `py -3.13` por `py -3.12`.

## Uso

1. Copie uma URL HTTPS que entregue diretamente um MP3 e cujo download seja permitido.
2. Escolha a pasta e clique em **Baixar MP3**.
3. Acompanhe a transferência; use **Pausar** apenas quando o servidor oferecer retomada.
4. Consulte **Histórico** ou **Abrir pasta** após a conclusão.

Para vídeo, abra **Estúdio de clipes**, importe um ou mais arquivos locais, escolha o vídeo, navegue pela timeline e use **Pré-visualizar no FFplay**. Defina início e fim em segundos, adicione intervalos e selecione um ou vários para a fila de exportação. Escolha pasta, proporção e qualidade CRF antes de exportar.

Para um teste legal, use um MP3 disponibilizado por você mesmo em um servidor HTTPS ou um arquivo de exemplo cujo autor permita o download direto. Nenhuma URL de terceiros é embutida porque disponibilidade e licença podem mudar.

## Desenvolvimento

```powershell
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
ruff check app.py mp3_desktop tests
ruff format --check app.py mp3_desktop tests
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --onefile --windowed --name MP3Desktop app.py
```

O executável gerado fica em `dist/MP3Desktop.exe`. A build precisa ser validada em Windows antes de publicar. Veja [instalação](docs/installation.md), [arquitetura](docs/architecture.md) e [contribuição](CONTRIBUTING.md).

## Limitações e perguntas frequentes

- **Links de plataformas de vídeo funcionam?** Não. A URL precisa responder com bytes MP3 diretamente.
- **Por que a pausa está indisponível?** O servidor não anunciou `Accept-Ranges: bytes`.
- **A estimativa é precisa?** É aproximada e depende de `Content-Length` e da velocidade corrente.
- **Um download interrompido após fechar o app é retomado?** Não. A retomada funciona somente na sessão atual.
- **Há downloads simultâneos?** Não; um por vez.
- **O formato é verificado?** Cabeçalho HTTP e assinatura inicial são verificados, mas não há decodificação integral do áudio.
- **A pré-visualização fica dentro da janela?** Não. Esta versão abre FFplay em janela separada.
- **Há detecção automática ou IA?** Não. A edição de clipes é manual nesta versão; nenhuma chave de API é solicitada.
- **Arrastar e soltar vídeos funciona?** Ainda não; use o seletor de arquivos com seleção múltipla.
- **Vídeos de quatro horas foram validados?** Não. FFmpeg processa em fluxo, mas desempenho e espaço em disco dependem do arquivo e da máquina.

Veja [solução de problemas](docs/troubleshooting.md). Use apenas materiais que você tenha direito de baixar. O aplicativo não concede direitos sobre nenhum conteúdo.

## Projeto aberto

Licença [MIT](LICENSE). Consulte [segurança](SECURITY.md), [código de conduta](CODE_OF_CONDUCT.md) e [guia de contribuição](CONTRIBUTING.md).

**Roadmap:** 0.1 Media Studio manual; 0.2 sugestões locais de clipes, análise em janelas e contrato de provedores de IA; 0.3 integrações de IA verificadas; 0.4 ferramentas de criador e refinamento do player. Executável Windows validado e release permanecem pendentes. Os itens futuros não são compromissos de prazo.
