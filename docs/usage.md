# Uso

Insira uma URL HTTPS direta para MP3. Selecione a pasta de destino, ajuste o limite em Configurações se necessário e inicie o download. A barra mostra progresso quando o servidor informa `Content-Length`; velocidade e tempo restante são aproximados. O botão Pausar aparece ativo apenas se houver suporte informado para retomada. Após concluir, abra a pasta pelo botão ou pelo Histórico.

O aplicativo recusa páginas HTML, outros formatos e links que exigem autenticação. Arquivos com o mesmo nome recebem sufixos `(1)`, `(2)` etc.

## Estúdio de clipes

Em **Estúdio de clipes**, use **Importar vídeos** para selecionar vários arquivos locais. O FFprobe lê duração e resolução. Selecione um vídeo, navegue na timeline e clique em **Pré-visualizar no FFplay** para abrir uma janela externa no ponto atual. Informe início e fim em segundos, adicione quantos intervalos quiser e selecione um ou mais clipes para exportar. Escolha a pasta, proporção e qualidade CRF. A fila executa um clipe por vez; progresso e estado aparecem no painel. O botão de cancelamento interrompe a exportação atual.

O histórico de vídeos e clipes aparece em **Projetos** e no estúdio após reiniciar. Uma tarefa interrompida pelo fechamento do app fica marcada `interrupted` e exige nova inclusão na fila. Sugestões automáticas e IA ainda não estão disponíveis.
