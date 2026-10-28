# Customs de referência (`MIDGUITAR_REFS`)

- `MIDGUITAR_REFS` aponta para uma pasta em que cada subpasta é um custom que **funciona no jogo**: uma pasta Clone Hero com `song.ini` e `notes.mid`/`notes.chart`, ou uma pasta RB3 com `songs/songs.dta`.
- A pasta fica **fora do Git** (são arquivos de terceiros/do dono; nunca os copie para o repositório).
- Sem a variável, os testes `refs` são pulados. Para rodar:

```
set "MIDGUITAR_REFS=D:\RefCustoms"
venv\Scripts\python -m pytest -m refs -v
```

Cada subpasta vira um caso de teste (o id é o nome da pasta). Em pastas RB3, a ida e volta
só roda nas músicas `songs/<pasta>/` que tenham um `.mid` legível (não só `.mid.edat`).
