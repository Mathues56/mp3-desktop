# Arquitetura

`app.py` inicia por padrão `mp3_desktop/web.py`, um servidor HTTP vinculado somente a `127.0.0.1` em porta efêmera. Ele abre a interface em `web_assets/` no navegador padrão. A API JSON exige um token gerado a cada execução; os arquivos HTML/CSS/JS são locais. Tkinter é usado apenas nos diálogos nativos para escolher arquivos e pastas. `app.py --classic` mantém a interface Tkinter anterior em `ui.py`.

O serviço web cria uma conexão SQLite por operação e fecha cada conexão. Downloads e exportações rodam em threads de trabalho. A interface consulta estado e progresso periodicamente, enquanto `core.py` e `media.py` continuam responsáveis por validação, transferência e processamento. A interface não habilita telas de IA, transcrição ou automação que ainda não tenham implementação.

`mp3_desktop/core.py` valida URL e resposta, baixa em blocos de 64 KiB para arquivo temporário e cria o destino final sem sobrescrever. Só HTTPS é aceito pela interface. Redirecionamentos passam pela mesma validação. O parâmetro `allow_http` existe apenas para testes locais.

`mp3_desktop/ui.py` executa o download numa thread e envia eventos para a thread Tkinter. Há uma transferência ativa por vez. `storage.py` guarda histórico e preferências na pasta de dados do usuário; não armazena a URL nem credenciais.

Para testes isolados, `MP3_DESKTOP_DATA_DIR` pode apontar para uma pasta local temporária.

A pausa guarda o arquivo parcial apenas em memória da sessão; retomada exige resposta `206` com `Content-Range` correspondente. Falhas e cancelamento removem o temporário. A finalização usa um hard link exclusivo no mesmo volume para evitar sobrescrita.

`media.py` usa FFprobe para metadados e FFmpeg para exportação MP4. Os processos recebem caminhos como argumentos, sem shell. O progresso vem de `-progress pipe:1`; cancelamento termina o processo e remove o temporário. O vídeo não é carregado inteiro na memória. SQLite persiste vídeos, intervalos, tarefas de exportação e projetos. `project_videos` organiza vídeos já importados sem copiar os arquivos. Excluir um projeto remove somente as associações; vídeos e intervalos permanecem. Tarefas em andamento na inicialização seguinte ficam como `interrupted`, para revisão manual.

O player do navegador solicita `/media/<id>` para um vídeo já importado. A rota resolve o ID pela tabela local, exige o token da sessão na query string e serve intervalos HTTP `Range` em blocos de 64 KiB. Ela não recebe nem abre caminhos arbitrários enviados pelo navegador. O player depende dos contêineres e codecs suportados pelo navegador. As faixas V1/A1 são uma visualização dos intervalos salvos sobre a mesma fonte; ainda não há clips de áudio independentes nem mixagem.

Integrações de IA e sugestões locais não fazem parte desta versão. Nenhuma credencial é armazenada.
