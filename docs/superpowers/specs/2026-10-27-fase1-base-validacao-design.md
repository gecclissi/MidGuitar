# Fase 1 — Base de Validação e Mapa de Tempo (Design)

**Data:** 2026-10-27
**Status:** aguardando revisão do dono
**Roteiro maior:** "Músicas jogáveis" — fazer as músicas exportadas abrirem e tocarem sincronizadas em todos os destinos.

## Contexto

O MidGuitar exporta para Clone Hero/YARG, Rock Band 3 (PS3/RPCS3), Rock Band 2, Xbox 360 e PS4, mas hoje:

- não existe nenhum teste automatizado;
- nada verifica se o que é exportado segue as regras que os jogos exigem;
- o modelo guarda **um único BPM** (`ChartSong.bpm`): `chart_importer` fica só com o último `set_tempo` do MIDI (`src/creator/chart_importer.py:236`) ou o último `B` do `.chart`, e `midi_generator` grava um tempo único. Customs de fãs com mudança de tempo saem dessincronizados ao serem importados/reexportados;
- `requirements.txt` não lista `numpy`, `soundfile` e `tkinterdnd2`, que o código e o `build_exe.py` usam.

### Roteiro completo (cada fase tem spec própria)

| Fase | Entrega | Prova |
|---|---|---|
| **1. Base (esta spec)** | mapa de tempo, validador, testes, deps | testes automáticos + customs de referência |
| 2. Clone Hero/YARG | correções no exportador CH | teste real no CH/YARG |
| 3. RB3 PS3/RPCS3 | formato PS3 correto (EDAT, png_ps3, mogg, dta) | teste real no RPCS3 e PS3 |
| 4. RB2 + Xbox 360 | pacote CON/STFS, filtragem RB2 | só validação automática (sem Xenia/X360 disponível) |
| 5. PS4 | ajustes RB4 sobre a Fase 3 | teste real no PS4 |

## Entendimento acordado

- **O dono pediu:** músicas jogáveis em todos os destinos; abordagem "validador próprio + testes contra customs de referência".
- **O dono tem:** Clone Hero/YARG no PC, RPCS3 com RB3, PS3/PS4 reais desbloqueados, e customs RB3/CH que funcionam.
- **Sucesso da Fase 1:** (a) uma música gerada do zero e (b) cada custom de referência passam no validador sem erros; (c) importar e reexportar um custom com mudanças de tempo preserva o tempo de cada nota dentro de ±2 ms.

## Fora do escopo

- Melhorar o auto-chart (continua gerando tempo único).
- Refatorar `creator_studio_dialog.py` além do mínimo para exibir o resultado do validador.
- Corrigir os exportadores de cada destino (Fases 2–5). A Fase 1 só **detecta** os problemas.
- Mudar textos do README/tutorial.

## Design

### 1. Mapa de tempo — `src/creator/tempo_map.py`

```python
@dataclass
class TempoChange:
    tick: int
    us_per_beat: int          # microssegundos por semínima (MIDI set_tempo)

@dataclass
class TimeSigChange:
    tick: int
    numerator: int
    denominator: int

class TempoMap:
    ticks_per_beat: int = 480
    tempos: list[TempoChange]       # ordenado, sempre começa em tick 0
    time_sigs: list[TimeSigChange]  # ordenado, sempre começa em tick 0

    @classmethod
    def constant(cls, bpm: float, num: int = 4, den: int = 4) -> "TempoMap"
    def ms_to_tick(self, ms: float) -> int
    def tick_to_ms(self, tick: int) -> float
    def initial_bpm(self) -> float
    def rescaled(self, ticks_per_beat: int) -> "TempoMap"   # para importar MIDIs com outra resolução
    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, data: dict) -> "TempoMap"
```

- A conversão é por segmentos: acumula o tempo em ms de cada trecho entre mudanças de tempo.
- Se `tempos` vier vazio ou sem entrada no tick 0, é preenchido com 120 BPM (padrão MIDI).

### 2. Modelo — `src/creator/chart_model.py`

- O `ChartSong` ganha `tempo_map: TempoMap | None = None`.
- `ChartSong.get_tempo_map()` devolve `tempo_map` se existir, senão `TempoMap.constant(self.bpm, *time_signature)`.
- O `bpm` continua sendo o campo que a UI edita. Ao carregar um mapa importado, `bpm` = `tempo_map.initial_bpm()`.
- Se o usuário mudar o BPM na UI de uma música com mapa de várias mudanças, o mapa é descartado e volta a ser constante. Isso fica documentado num comentário, e o caso de uso principal (customs importados) não passa pela edição de BPM.
- `to_dict`/`from_dict` serializam `tempo_map` quando ele existe. Projetos antigos sem o campo carregam como hoje.
- As notas continuam em ms. Editor, auto-chart e playtest não mudam.

### 3. Importador — `src/creator/chart_importer.py`

- **`.mid`:** coleta todos os `set_tempo` e `time_signature` de todas as trilhas (em tick absoluto), monta o `TempoMap` com o `ticks_per_beat` do arquivo e converte o início e a duração de cada nota com `tick_to_ms` (a duração é calculada pelos dois extremos, não por BPM fixo).
- **`.chart`:** coleta todos os eventos `B` (tempo ×1000) e `TS` da seção `[SyncTrack]`, com o `Resolution` do arquivo, e faz a mesma conversão.
- No fim, `song.tempo_map` = mapa importado e `song.bpm` = BPM inicial.

### 4. Gerador — `src/creator/midi_generator.py`

- Usa `song.get_tempo_map()`, reescalado para 480 TPB.
- A trilha de tempo (trilha 0) grava todas as mudanças de tempo e de compasso.
- O `ms_to_ticks`/`ticks_to_ms` desse módulo passa a delegar ao mapa. As assinaturas atuais continuam funcionando para os chamadores existentes, com o mapa constante derivado do BPM.
- A trilha `BEAT` gera os tempos seguindo os ticks do compasso vigente: nota 12 no primeiro tempo do compasso e 13 nos demais, até o fim da música.
- Nenhum exportador gera `.chart` (o `pack_compiler` só lê `.chart` via importador), então não há gerador de `.chart` para ajustar.

### 5. Validador — `src/creator/validation/`

Funções puras, sem UI e sem I/O além de ler os arquivos indicados.

```python
@dataclass
class Issue:
    level: Literal["error", "warning"]
    code: str          # ex.: "MIDI_MISSING_EVENTS_END"
    message: str       # em português, para o usuário final
    location: str      # arquivo / trilha / tick
```

- **`midi_rules.py`** — `validate_midi(path, profile) -> list[Issue]`:
  - arquivo tipo 1, com 480 TPB (aviso se for outro valor);
  - trilha 0 com tempo, e nomes de trilha conhecidos (sem duplicatas);
  - `EVENTS` com `[music_start]`, `[music_end]` e `[end]`, e `[end]` depois da última nota;
  - `BEAT` presente, com notas 12/13 cobrindo a música toda;
  - em cada `PART`, as notas ficam nas faixas válidas de cada dificuldade (usando `rbn_specs.py`), sem note-on sem note-off e sem a mesma nota sobreposta a ela mesma;
  - `PART VOCALS` com frases (105/106) envolvendo as notas e letras alinhadas às notas;
  - Pro Guitar/Bass com velocidades de casa 100–117 e canal válido;
  - o perfil define quais trilhas são permitidas ou obrigatórias (ex.: RB2 não aceita `PART KEYS` nem `PART REAL_*`).
- **`dta_rules.py`** — `validate_dta(path, profile) -> list[Issue]`:
  - parênteses balanceados e campos obrigatórios (`name`, `artist`, `song`/`name`, `tracks`, `pans`, `vols`, `cores`, `rank`, `song_id`, `game_origin`, `vocal_parts`);
  - `rank` > 0 só para instrumentos com trilha no MIDI;
  - o número de canais em `pans`/`vols`/`cores` bate com `tracks` e com os canais do `.mogg`;
  - `vocal_parts 0` quando não há vocais.
- **`mogg_rules.py`** — `validate_mogg(path) -> list[Issue]`:
  - versão `0x0A`, offset do OGG apontando para `OggS`, tabela de seek coerente e OGG legível pelo `soundfile`;
  - devolve o número de canais para o `dta_rules`.
- **`targets.py`** — perfis `clonehero`, `rb3_ps3`, `rb2`, `xbox360` e `ps4`. Cada um lista os arquivos e pastas esperados e quais regras aplicar. Também expõe `validate_export(folder, target) -> list[Issue]`, que é o ponto de entrada.
- Nesta fase, os perfis descrevem o formato que **os jogos exigem**, não o que o MidGuitar gera hoje. Exemplo: o `rb3_ps3` espera `.mid.edat` e `.png_ps3`. Os erros que isso produzir são a lista de trabalho das Fases 2–5.

### 6. Testes — `tests/`

- `requirements-dev.txt` com `pytest`, e `pytest.ini`/`pyproject` mínimo apontando `testpaths = tests`.
- **Unitários:**
  - `TempoMap`: conversão ida e volta, várias mudanças de tempo, reescala de TPB e serialização;
  - regras do validador: cada regra com um MIDI ou DTA mínimo construído no próprio teste, um caso que passa e um que falha;
  - gerador + validador: uma música gerada pelo `auto_generate_chart` sem áudio e exportada pelo `generate_rbn_midi` passa em `validate_midi` sem erros;
  - modelo: `from_dict` de projeto antigo (sem `tempo_map`) continua funcionando.
- **Com referências** (marcados `@pytest.mark.refs`, pulados se `MIDGUITAR_REFS` não estiver definida):
  - a pasta indicada contém customs (pastas CH com `notes.mid` + `song.ini` e/ou pastas RB3 com `songs.dta` + `.mid` + `.mogg`), e fica fora do Git;
  - cada custom passa no validador do perfil correspondente sem erros. Isso prova que o validador não dá falso positivo; se der, a regra é corrigida, não o custom;
  - em cada custom: importar, exportar e reimportar preserva o tempo de cada nota dentro de ±2 ms e a quantidade de notas por trilha e dificuldade.
- Nenhum teste depende de UI, de dispositivo MIDI ou de áudio tocando.

### 7. Dependências

- `requirements.txt`: adicionar `numpy`, `soundfile` e `tkinterdnd2`, com versões mínimas compatíveis com Python 3.9+.
- `requirements-dev.txt`: `-r requirements.txt` + `pytest`.

### 8. UI — `src/ui/creator_studio_dialog.py`

- Depois de cada exportação bem-sucedida (os handlers `_on_export_*` e `_on_export_to_selected_game`), o app chama `validate_export(pasta, perfil)`.
- Sem erros nem avisos, a mensagem de sucesso atual continua igual.
- Com problemas, a mensagem de sucesso ganha um bloco "⚠️ Verificação de compatibilidade", com até 10 itens (erros primeiro) e a contagem do restante.
- Se o próprio validador lançar exceção, ela é capturada e vira um aviso. A exportação nunca falha por causa do validador.

## Tratamento de erros

- O validador nunca lança exceção para o chamador: arquivo ausente ou ilegível vira um `Issue` de nível `error`.
- O importador com mapa de tempo inválido (por exemplo, tempo 0) ignora a entrada inválida e registra um aviso no log.

## Riscos

- **As regras dos jogos não estão documentadas oficialmente.** Por isso os customs de referência são o "juiz": uma regra que acusa um custom que funciona está errada.
- **O perfil `xbox360` não pode ser confirmado em jogo real** (não há Xenia/X360 disponível) e fica marcado como "não verificado em jogo" na própria definição do perfil.
- **Hoje a validação vai gerar muitos erros nos exportadores PS3/Xbox.** Isso é esperado e é a entrada das próximas fases. A mensagem na UI precisa ser clara sem assustar quem exporta para Clone Hero.
