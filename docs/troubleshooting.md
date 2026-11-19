# Solução de problemas

- **URL rejeitada:** confirme que é HTTPS e não contém usuário/senha.
- **Conteúdo não é MP3:** abra a URL em um navegador e verifique se ela aponta ao arquivo, não a uma página.
- **Resposta 403/404:** a fonte pode exigir autorização ou ter removido o arquivo. O aplicativo não contorna restrições.
- **Pausa indisponível:** o servidor não informa `Accept-Ranges: bytes`.
- **Falha ao salvar:** escolha uma pasta com permissão de escrita e espaço suficiente.
- **Página local não abre:** mantenha o processo `python app.py` ativo e abra a URL `http://127.0.0.1:PORTA/` exibida no terminal. Confira se o navegador padrão está disponível. Se o erro ocorrer antes da URL aparecer, veja a mensagem no terminal e confira a permissão de escrita na pasta de dados do aplicativo.
- **Seletor de arquivos não abre:** no Windows, confira `python -m tkinter` e use uma instalação de Python com Tk. No macOS, use a interface iniciada por `app.py`/Finder e confirme que o processo `/usr/bin/osascript` está disponível; cancelar o diálogo apenas fecha o seletor.
- **Vídeo não importa:** confira `ffprobe -version`, o formato do arquivo e se o arquivo ainda existe.
- **Vídeo não reproduz no player:** o navegador pode não decodificar o contêiner ou codec; use um MP4 compatível ou confira `ffmpeg -version` antes de exportar um novo arquivo. Na interface Tkinter antiga (`app.py --classic`), confira também `ffplay -version`.
- **Exportação falha:** confira `ffmpeg -version`, a permissão de escrita na pasta de destino e espaço livre. O aplicativo não instala FFmpeg automaticamente.
- **macOS diz que o desenvolvedor não pode ser verificado:** os pacotes sem assinatura Developer ID e notarização podem ser bloqueados pelo Gatekeeper. Não desative nem contorne a proteção; use somente uma release cuja origem e checksum você verificou e aguarde uma distribuição assinada/notarizada se o sistema impedir a abertura.
- **FFmpeg não encontrado no Finder:** confirme `ffmpeg -version` e `ffprobe -version`. O app verifica `/opt/homebrew/bin` em Apple Silicon e `/usr/local/bin` em Intel; instalações em outros prefixos precisam estar no PATH do processo. FFmpeg não é incluído no `.app`.
- **O app ainda parece ativo após fechar a aba:** fechar o navegador não encerra o servidor. Use **Configurações → Encerrar Media Studio** para parar o servidor e cancelar tarefas em andamento.
