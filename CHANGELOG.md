# Changelog

## Não publicado

- Interface web alinhada às referências com navegação consistente, estados responsivos e limites de recursos claramente identificados.
- Projetos locais com nome, descrição, associação de vídeos e edição/exclusão sem apagar os arquivos de origem ou intervalos.
- Páginas de métricas e histórico baseadas nos registros SQLite existentes; sem gráficos ou eventos simulados.
- Nova interface local em HTML, CSS e JavaScript, com paleta verde-azulada baseada na referência fornecida, estados vazios e controles desabilitados quando falta seleção.
- Abertura padrão pelo navegador; a interface Tkinter anterior continua acessível com `app.py --classic`.
- API local para downloads, vídeos, intervalos, pré-visualização e fila de exportação, reutilizando o núcleo existente.
- Player web local com rota de mídia por ID importado, token da sessão, suporte HTTP Range e envio em blocos de 64 KiB.
- Faixas V1/A1 e marcação de entrada/saída no editor; A1 permanece sincronizada ao áudio incorporado na fonte.
- Especificação independente da arquitetura do editor, com evidência verificada, hipóteses, limites e itens pendentes.
- Orientações de colaboração e contribuição ampliadas no repositório.
- Corrigida a importação dos nomes de fonte Tkinter para permitir iniciar o app.

## 0.1.1 — 2026-11-18

- Refinada a interface Tkinter com hierarquia visual consistente, paleta azul-petróleo e turquesa, neutros e espaçamento em escala de 4 px.
- Design system único em `mp3_desktop/design.py`, compartilhado por `ui.py` e `studio.py` (sem duplicação de cores/tipografia).
- Botões primário/secundário com raio e preenchimento consistentes; cards com borda sutil; abas com estado ativo destacado.
- Treeviews com estados de linha reconhecíveis (header, seleção, foco); barra de progresso estilizada por tema.
- Tipografia Segoe UI, pesos 400–600, sem itálico, sem rastreamento negativo.
- Nenhum emoji, nenhum gradiente, nenhum brilho, nenhuma sombra colorida.
- Nenhuma alteração de funcionalidade; apenas design/UX.

## 0.1.0 — 2026-11-17

- Substituído o fluxo anterior de extração de streaming por download de MP3 via URL direta HTTPS.
- Adicionados progresso, cancelamento, pausa/retomada condicionada ao servidor, histórico SQLite e preferências locais.
- Adicionados testes locais, documentação e configuração inicial de CI e build Windows.
- Adicionado estúdio manual de vídeos locais, projetos persistentes, intervalos e fila sequencial de exportação MP4 via FFmpeg.
