# Especificação independente do editor do Media Studio

**Estado:** especificação inicial; implementação parcial. Esta documentação descreve o Media Studio a partir do próprio repositório e dos requisitos visuais fornecidos pelo usuário. Não registra observações internas do CapCut.

## Evidência e limites

### Verificado no código do Media Studio

- `app.py` abre a interface local no navegador; a API escuta em `127.0.0.1` e usa token por sessão.
- `storage.py` persiste projetos, associação de vídeos, intervalos e fila de exportação em SQLite. Projetos referenciam os vídeos sem copiá-los.
- `media.py` usa FFprobe para metadados e FFmpeg para recortes e exportação. A execução passa argumentos sem shell e transmite progresso.
- `web.py` importa arquivos escolhidos pelo usuário, marca início/fim, enfileira exportação e resolve arquivos importados por ID.
- O player embutido serve arquivos importados com HTTP Range e blocos; a reprodução depende de codec compatível com o navegador.
- As telas de IA, transcrição e automação declaram indisponibilidade; não há chamadas a provedores implementadas.

### Não verificado

- Não foram inspecionados binários, arquivos, tráfego, processos ou interface do CapCut. Os Termos de Serviço oficiais restringem engenharia reversa e interação automatizada; a análise do produto de terceiros parou nessa fronteira.
- Não foram medidos tempos, uso de CPU/GPU ou comportamento do CapCut.
- Desempenho em resoluções altas, formatos variáveis e projetos grandes ainda não foi medido neste aplicativo.

## Arquitetura funcional

```text
Interface HTML/CSS/JS
        │ HTTP local + token de sessão
        ▼
web.py: rotas e coordenação de tarefas
   ├── storage.py: SQLite e metadados
   ├── media.py: FFprobe / FFmpeg
   └── core.py: downloads diretos autorizados
```

Responsabilidades desejadas:

- **Interface:** player, biblioteca e timeline; não acessa disco arbitrário nem executa comandos.
- **Serviço local:** valida IDs, intervalos e opções; associa cada mídia a um registro importado; transmite mídia em blocos.
- **Armazenamento:** guarda projetos, faixas e operações sem embutir o arquivo de origem no banco.
- **Adaptadores de mídia:** player nativo do navegador para revisão e FFmpeg para render final. A camada de domínio não conhece detalhes de interface.
- **Extensão de IA:** portas opcionais para transcrição/análise, sem dependência obrigatória. Cada adaptador deve declarar entrada, saída, processamento local/remoto e consentimento antes de ativar.

## Modelo de projeto

Modelo de destino para evolução, mantendo os registros existentes compatíveis:

- **Projeto:** `id`, `nome`, `descrição`, datas e preferências de exportação.
- **Asset de mídia:** `id`, caminho local escolhido, duração, dimensões, tamanho e metadados técnicos. Arquivo original continua fora do SQLite.
- **Timeline:** taxa de quadros, duração e lista ordenada de trilhas.
- **Trilha:** `id`, tipo (`video`, `audio`, `text`), ordem, nome e estado de mudo/visibilidade.
- **Clip de trilha:** asset, posição na timeline, intervalo da fonte, duração, ganho/transformações opcionais.
- **Exportação:** snapshot de parâmetros do projeto, estado, progresso e caminho do resultado.

**Implementado hoje:** projeto e associação com vídeos, intervalos de origem e fila FFmpeg. **Pendente:** timeline persistente com clips posicionados, trilhas independentes, efeitos e histórico desfazer/refazer.

## Timeline e trilhas

- Escala horizontal representa tempo; navegação e posição usam segundos no editor atual.
- `V1` e `A1` são faixas de origem sincronizadas. A1 representa o áudio embutido no mesmo arquivo de vídeo.
- Intervalos salvos aparecem nas duas faixas, podem ser selecionados e carregam os pontos de entrada/saída.
- O corte atual exporta um intervalo da fonte. Não há ripple edit, divisão não destrutiva de um clip, rearranjo de segmentos, transição, volume ou sincronização independente.
- Evolução: permitir mover/trimar clips na timeline, separar/reatribuir áudio e manter os pontos de fonte independentes da posição na sequência.

## Reprodução

- O elemento `<video>` do navegador faz reprodução e busca local. A rota recebe somente ID de asset importado, verifica token da sessão e atende Range requests.
- A resolução de decodificação, codecs e suavidade dependem do navegador e da máquina. FFmpeg continua usado para render.
- Requisito futuro: exibir estado de carregamento/erro, tempo atual e duração; preservar posição ao atualizar metadados; suportar seek frame a frame conforme a taxa de quadros.
- Reprodução acelerada por GPU é hipótese a validar; não é requisito prometido nem resultado medido.

## Operações de edição

1. Criar projeto opcional e importar uma mídia local pelo seletor de arquivos.
2. Revisar no player, buscar pelo controle de posição e marcar entrada/saída.
3. Salvar um intervalo nomeado, alterar ou excluir intervalo.
4. Escolher formato/proporção/qualidade e adicionar à fila de render.
5. Acompanhar progresso, cancelar a tarefa atual e localizar o resultado.

Validações: arquivo registrado, duração positiva, `0 ≤ início < fim ≤ duração`, preset conhecido, qualidade entre limites aceitos, caminho de saída escolhido. O serviço deve rejeitar valores inválidos antes de iniciar FFmpeg.

## Pipeline de renderização

1. Resolver `clip_id` para vídeo e intervalo no SQLite.
2. Revalidar limites contra a duração e mapear o preset para parâmetros explícitos.
3. Chamar FFmpeg sem shell; não carregar o vídeo inteiro em memória.
4. Escrever em temporário no destino e só publicar o arquivo final após sucesso.
5. Atualizar progresso/estado e remover temporário em erro ou cancelamento.

Metadados e opções selecionadas devem ficar registrados para reproduzir um export. Compatibilidade de codecs e filtros depende da versão local de FFmpeg e precisa ser checada antes de anunciar presets.

## Requisitos de desempenho

Metas iniciais para validar em hardware de referência, ainda **não medidas**:

- abrir a biblioteca com 500 assets sem bloquear a janela; atualizar só os componentes alterados;
- servir prévia em blocos e manter memória do app independente do tamanho total do vídeo;
- refletir progresso de export pelo menos uma vez por segundo sem bloquear controles;
- permitir cancelar export e remover apenas o temporário daquela tarefa;
- registrar CPU, RAM, GPU, tamanho/resolução do arquivo e tempo em testes repetíveis antes de comparar versões.

Valores de latência de seek/export serão definidos após baseline próprio; não há benchmark do CapCut para comparação.

## Componentes UI/UX

- Identidade própria Media Studio com azul-petróleo, teal e menta da paleta fornecida pelo usuário.
- Navegação entre visão geral, downloads, projetos, editor, exportação e configurações.
- Editor com player, posição, duas faixas sincronizadas, controles explícitos de entrada/saída e lista de intervalos.
- Estados vazios, carregando, erro, sucesso e indisponível devem refletir capacidades reais; recursos futuros ficam marcados como indisponíveis.
- Requisitos: navegação por teclado, foco visível, rótulos acessíveis, comportamento responsivo e confirmação ao excluir projeto/clip.

## Critérios para evoluir

- Testes de API cobrem token, acesso somente por ID importado, Range requests, limites de intervalo e cancelamento.
- Teste funcional com mídia de autoria própria confirma reproduzir, buscar, marcar, salvar e exportar com áudio sincronizado.
- Registrar versões e licenças de FFmpeg/FFprobe usados em build/release; confirmar termos de redistribuição antes de empacotar binários.
- Comparações de comportamento usam somente requisitos genéricos e dados produzidos pelo Media Studio; nenhuma coleta automatizada de outro editor.
- Implementações de IA permanecem opcionais, com entradas/saídas declaradas e sem enviar mídia a terceiros sem consentimento explícito.

## Autoria e licenças verificadas

- O repositório declara MIT em `LICENSE`; as alterações deste trabalho são código, documentação e interface original do Media Studio. Nenhum binário, imagem, fonte ou outro arquivo do CapCut foi adicionado.
- `pyproject.toml` declara `dependencies = []`; o app usa a biblioteca padrão do Python em execução.
- `requirements-dev.txt` fixa Ruff 0.15.10 (MIT) e `requirements-build.txt` fixa PyInstaller 6.16.0. O upstream do PyInstaller declara GPL-2.0-or-later com exceção de bootloader para executáveis combinados; o pacote é usado somente na etapa de build.
- Setuptools é requisito do backend de build e declara MIT.
- FFmpeg/FFprobe são programas externos instalados pelo usuário; o repositório não os inclui. O projeto FFmpeg declara LGPL 2.1 ou posterior para a configuração padrão e GPL quando se habilitam componentes GPL. Antes de redistribuir executável ou FFmpeg, registrar `ffmpeg -version`, `ffmpeg -buildconf`, origem do binário e avisos/licenças aplicáveis.
- Este inventário cobre declarações upstream e dependências declaradas; não confirma a configuração de uma cópia de FFmpeg instalada pelo usuário nem resolve questões de patentes de codecs.
