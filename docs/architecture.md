# Arquitetura

`mp3_desktop/core.py` valida URL e resposta, baixa em blocos de 64 KiB para arquivo temporário e cria o destino final sem sobrescrever. Só HTTPS é aceito pela interface. Redirecionamentos passam pela mesma validação. O parâmetro `allow_http` existe apenas para testes locais.

`mp3_desktop/ui.py` executa o download numa thread e envia eventos para a thread Tkinter. Há uma transferência ativa por vez. `storage.py` guarda histórico e preferências na pasta de dados do usuário; não armazena a URL nem credenciais.

Para testes isolados, `MP3_DESKTOP_DATA_DIR` pode apontar para uma pasta local temporária.

A pausa guarda o arquivo parcial apenas em memória da sessão; retomada exige resposta `206` com `Content-Range` correspondente. Falhas e cancelamento removem o temporário. A finalização usa um hard link exclusivo no mesmo volume para evitar sobrescrita.

`media.py` usa FFprobe para metadados e FFmpeg para exportação MP4. Os processos recebem caminhos como argumentos, sem shell. O progresso vem de `-progress pipe:1`; cancelamento termina o processo e remove o temporário. O vídeo não é carregado inteiro na memória. `studio.py` mantém a fila sequencial na interface, enquanto SQLite persiste vídeos, intervalos e tarefas. Tarefas em andamento na inicialização seguinte ficam como `interrupted`, para revisão manual. `ffplay` abre a pré-visualização numa janela externa.

Integrações de IA e sugestões locais não fazem parte desta versão. Nenhuma credencial é armazenada.
