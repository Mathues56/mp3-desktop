# Uso

Insira uma URL HTTPS direta para MP3. Selecione a pasta de destino, ajuste o limite em Configurações se necessário e inicie o download. A barra mostra progresso quando o servidor informa `Content-Length`; velocidade e tempo restante são aproximados. O botão Pausar aparece ativo apenas se houver suporte informado para retomada. Após concluir, abra a pasta pelo botão ou pelo Histórico.

O aplicativo recusa páginas HTML, outros formatos e links que exigem autenticação. Arquivos com o mesmo nome recebem sufixos `(1)`, `(2)` etc.

## Estúdio de clipes

Em **Projetos**, crie um projeto com nome e descrição e use **Adicionar vídeos** para associar arquivos locais. Também é possível importar vídeos sem projeto. O FFprobe lê duração e resolução. No **Editor de clipes**, selecione um vídeo, reproduza no player, navegue na timeline, marque entrada e saída e salve intervalos. Em **Exportação**, escolha a pasta, proporção e qualidade CRF para o intervalo selecionado. A fila executa um clipe por vez; progresso e estado aparecem na tela. O botão de cancelamento interrompe a exportação atual. A faixa A1 mostra o áudio incorporado no mesmo vídeo, sem edição independente de áudio nesta versão.

Os projetos, vídeos e intervalos permanecem após reiniciar. Excluir um projeto remove as associações, mas preserva os arquivos e intervalos. Uma tarefa interrompida pelo fechamento do app fica marcada `interrupted` e exige nova inclusão na fila. Transcrição automática, IA e seleção automática de destaques ainda não estão disponíveis.
