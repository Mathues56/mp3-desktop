# Solução de problemas

- **URL rejeitada:** confirme que é HTTPS e não contém usuário/senha.
- **Conteúdo não é MP3:** abra a URL em um navegador e verifique se ela aponta ao arquivo, não a uma página.
- **Resposta 403/404:** a fonte pode exigir autorização ou ter removido o arquivo. O aplicativo não contorna restrições.
- **Pausa indisponível:** o servidor não informa `Accept-Ranges: bytes`.
- **Falha ao salvar:** escolha uma pasta com permissão de escrita e espaço suficiente.
- **Janela não abre:** confira `python -m tkinter` e use a instalação padrão de Python para Windows.
- **Vídeo não importa:** confira `ffprobe -version`, o formato do arquivo e se o arquivo ainda existe.
- **Pré-visualização não abre:** confira `ffplay -version`. A pré-visualização usa janela separada.
- **Exportação falha:** confira `ffmpeg -version`, a permissão de escrita na pasta de destino e espaço livre. O aplicativo não instala FFmpeg automaticamente.
