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

Windows 10/11 e Python 3.12+ para executar do código-fonte. A interface abre no navegador padrão; Tkinter, incluído no Python para Windows, fornece os seletores de arquivo e pasta. Para vídeo, instale **FFmpeg e FFprobe** funcionais no PATH. FFplay só é necessário para a interface Tkinter antiga (`app.py --classic`). Linux e macOS ainda não foram validados.

## Instalação no Windows

Ainda não há executável validado nem página de Releases publicada. Para executar do código-fonte:

```powershell
cd <CAMINHO_DO_PROJETO>
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe app.py
```

Python 3.12 também funciona: troque `py -3.13` por `py -3.12`.

Também é possível abrir `abrir-local.cmd` com dois cliques. Mantenha o terminal aberto enquanto usar a interface no navegador. Para a interface Tkinter anterior, execute `python app.py --classic`.

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

A interface padrão usa `mp3_desktop/web_assets/index.html`, `app.css` e `app.js`. As cores vêm da referência enviada: fundo azul-petróleo, painéis em teal e realce menta. A navegação, formulários, estados vazios, foco de teclado e layout responsivo ficam nesses arquivos. A interface Tkinter anterior permanece disponível em `app.py --classic`, com seus estilos em `mp3_desktop/design.py`.

## Desenvolvimento

```powershell
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
ruff check app.py mp3_desktop tests
ruff format --check app.py mp3_desktop tests
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --onefile --windowed --collect-data mp3_desktop --name MP3Desktop app.py
```

O executável gerado fica em `dist/MP3Desktop.exe`. A build precisa ser validada em Windows antes de publicar. Veja [instalação](docs/installation.md), [arquitetura](docs/architecture.md) e [contribuição](CONTRIBUTING.md).

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

Veja [solução de problemas](docs/troubleshooting.md) e a [especificação independente do editor](docs/editor-architecture.md). Use apenas materiais que você tenha direito de baixar. O aplicativo não concede direitos sobre nenhum conteúdo.

## Projeto aberto

Licença [MIT](LICENSE). Consulte [segurança](SECURITY.md), [código de conduta](CODE_OF_CONDUCT.md) e [guia de contribuição](CONTRIBUTING.md).

**Roadmap:** refinar edição em múltiplas trilhas, adicionar áudio independente e avaliar sugestões locais de clipes e provedores de IA. Executável Windows validado e release permanecem pendentes. Os itens futuros não são compromissos de prazo.
