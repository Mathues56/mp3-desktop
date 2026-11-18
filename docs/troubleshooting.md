# Solução de problemas

- **URL rejeitada:** confirme que é HTTPS e não contém usuário/senha.
- **Conteúdo não é MP3:** abra a URL em um navegador e verifique se ela aponta ao arquivo, não a uma página.
- **Resposta 403/404:** a fonte pode exigir autorização ou ter removido o arquivo. O aplicativo não contorna restrições.
- **Pausa indisponível:** o servidor não informa `Accept-Ranges: bytes`.
- **Falha ao salvar:** escolha uma pasta com permissão de escrita e espaço suficiente.
- **Página local não abre:** mantenha o processo `python app.py` ativo e abra a URL `http://127.0.0.1:PORTA/` exibida no terminal. Confira se o navegador padrão está disponível. Se o erro ocorrer antes da URL aparecer, veja a mensagem no terminal e confira a permissão de escrita na pasta de dados do aplicativo.
- **Seletor de arquivos não abre:** confira `python -m tkinter` e use a instalação padrão de Python para Windows.
- **Vídeo não importa:** confira `ffprobe -version`, o formato do arquivo e se o arquivo ainda existe.
- **Vídeo não reproduz no player:** o navegador pode não decodificar o contêiner ou codec; use um MP4 compatível ou confira `ffmpeg -version` antes de exportar um novo arquivo. Na interface Tkinter antiga (`app.py --classic`), confira também `ffplay -version`.
- **Exportação falha:** confira `ffmpeg -version`, a permissão de escrita na pasta de destino e espaço livre. O aplicativo não instala FFmpeg automaticamente.
