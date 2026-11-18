# Como contribuir

Este projeto aceita correções, testes, melhorias de acessibilidade, documentação e propostas para os fluxos de download direto autorizado e edição de vídeos locais.

## Comece por aqui

1. Leia o [README](README.md) e a [arquitetura](docs/architecture.md).
2. Procure uma issue existente. Para uma mudança grande, abra uma issue antes de programar e descreva o problema e a solução proposta.
3. Faça um fork do repositório, crie uma branch curta e envie uma pull request para `main`. Uma pessoa mantenedora revisará a mudança.
4. Use os modelos de issue e pull request em `.github/` para informar como reproduzir, validar e revisar sua contribuição.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe app.py
python -m unittest discover -s tests -v
node --check mp3_desktop/web_assets/app.js
```

Python 3.12 também é aceito. FFmpeg, FFprobe e FFplay são necessários para testar os recursos de vídeo. A interface padrão é HTML/CSS/JS em `mp3_desktop/web_assets/`; `core.py`, `storage.py`, `media.py` e `web.py` cuidam da lógica local. A interface Tkinter anterior está disponível com `python app.py --classic`.

## Antes da pull request

- Preserve os downloads somente por URLs HTTPS diretas e autorizadas. Não adicione extração de plataformas, cookies, credenciais ou contornos de restrições.
- Não inclua músicas, vídeos, dados privados, links privados, bancos locais nem arquivos temporários.
- Execute os testes e descreva qualquer validação manual. Atualize README, arquitetura e CHANGELOG quando o comportamento mudar.
- Mantenha a mudança focada. Explique riscos, limitações e passos para reproduzir erros corrigidos.

Para começar com uma tarefa pequena, escolha uma issue marcada como `good first issue` quando o repositório tiver essa etiqueta, ou proponha uma melhoria de documentação, teste ou acessibilidade.
