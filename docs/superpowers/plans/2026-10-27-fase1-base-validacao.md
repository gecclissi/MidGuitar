# Fase 1 — Base de Validação e Mapa de Tempo — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar ao MidGuitar um mapa de tempo com várias mudanças de BPM, um validador de exportações por destino e uma suíte `pytest` calibrada contra customs reais, para que as próximas fases corrijam cada exportador com prova.

**Architecture:**
- Um `TempoMap` puro (`src/creator/tempo_map.py`) passa a ser a única fonte de conversão entre ms e tick para o importador e o gerador.
- O `ChartSong` guarda o mapa, mas as notas continuam em ms, então a UI, o auto-chart e o playtest não mudam.
- O validador (`src/creator/validation/`) é feito de funções puras que devolvem `list[Issue]`, organizadas por tipo de arquivo (MIDI, DTA, MOGG) e por perfil de destino.
- A UI só chama `validate_export` depois de exportar e mostra o resumo.

**Tech Stack:** Python 3.9+, `mido`, `numpy`, `soundfile` e `pytest`.

**Spec:** `docs/superpowers/specs/2026-10-27-fase1-base-validacao-design.md`

## Global Constraints

- Python 3.9+ (o README promete 3.9+): nada de `match`, nem `X | Y` em anotações avaliadas em tempo de execução. Use `Optional[...]`/`List[...]` de `typing` ou `from __future__ import annotations`.
- `TICKS_PER_BEAT = 480` (padrão Harmonix RBN/C3), lido de `src/creator/rbn_specs.py`.
- Tolerância de tempo no ida e volta: **±2 ms** por nota.
- Mensagens de `Issue.message` e da UI ficam em **português**, para o usuário final.
- O validador **nunca lança exceção** para o chamador: falha de leitura vira `Issue(level="error", ...)`.
- Projetos salvos antes desta fase (JSON sem `tempo_map`) continuam carregando.
- A exportação **nunca falha** por causa do validador.
- O perfil `xbox360` é marcado como "não verificado em jogo" (`verified_in_game=False`). O `rb2` também, porque o dono não citou RB2 no RPCS3.
- Os customs de referência ficam **fora do Git** e são lidos pela variável de ambiente `MIDGUITAR_REFS`. Os testes que usam essa pasta são pulados se ela não estiver definida.
- Identificadores em inglês e comentários/docstrings em português, como no código atual.

## Review Focus

1. **Notas iguais muito próximas:** uma passagem densa (fusas, ou notas com duração mínima de 100 ms importada) faz o fim de uma nota passar do início da seguinte na mesma altura. Hoje o importador sobrescreve a nota ativa e **perde notas** no ida e volta. O esperado é que nenhuma nota se perca. Teste na Task 4.
2. **MIDI sem tempo no tick 0, ou com `set_tempo` fora da trilha 0:** o esperado é assumir 120 BPM até o primeiro tempo e respeitar mudanças vindas de qualquer trilha. Testes nas Tasks 1 e 3.
3. **`songs.dta` de pacote com várias músicas, comentários `;` e strings com parênteses** (`(name "Song (Live)")`): o esperado é validar cada música sem acusar parêntese desbalanceado falso. Teste na Task 6.
4. **Projeto antigo sem `tempo_map`, ou usuário mudando o BPM de um custom importado:** o esperado é carregar com tempo constante, e a mudança de BPM descartar o mapa importado em vez de misturar os dois. Teste na Task 2.
5. **Arquivo corrompido ou truncado** (`.mid` que não é MIDI, `.mogg` cortado, pasta vazia): o esperado é receber `Issue` de erro, nunca uma exceção. Testes nas Tasks 5, 6 e 7.

---

### Task 0: Ambiente de testes e dependências

**Pré-requisito:** a máquina **não tem Python instalado** (`python`/`py` não existem; só há o alias da Microsoft Store). Antes desta task, peça ao dono para instalar o Python 3.11 ou aprovar `winget install Python.Python.3.11`. Não instale sem aprovação.

**Files:**
- Modify: `requirements.txt`
- Create: `requirements-dev.txt`, `pytest.ini`, `tests/__init__.py` (vazio), `tests/conftest.py`, `tests/test_smoke.py`

**Interfaces:**
- Produces:
  - fixture `refs_dir() -> pathlib.Path`, que pula o teste se `MIDGUITAR_REFS` não existir ou não for uma pasta;
  - marker `refs`;
  - a raiz do repositório no `sys.path`, para que `import src.creator...` funcione.

- [ ] **Step 1:** Adicione ao `requirements.txt` as linhas `numpy>=1.24`, `soundfile>=0.12.1` e `tkinterdnd2>=0.3.0`. Crie o `requirements-dev.txt` com `-r requirements.txt` e `pytest>=7.4`.
- [ ] **Step 2:** Crie o `pytest.ini` com `testpaths = tests` e `markers = refs: usa customs reais de MIDGUITAR_REFS`.
- [ ] **Step 3:** Escreva o `tests/conftest.py`: insira a raiz do repositório em `sys.path` e defina a fixture `refs_dir`.
- [ ] **Step 4:** Escreva o `tests/test_smoke.py`:

```python
def test_imports_core_modules():
    import src.creator.chart_model, src.creator.midi_generator, src.creator.chart_importer  # noqa
```

- [ ] **Step 5:** Crie o venv e instale: `python -m venv venv`, depois `venv\Scripts\pip install -r requirements-dev.txt`.
- [ ] **Step 6:** Rode `venv\Scripts\python -m pytest -q`. Esperado: `1 passed`.
- [ ] **Step 7:** Commit com a mensagem `chore: ambiente pytest e dependências faltantes`.

---

### Task 1: `TempoMap`

**Files:**
- Create: `src/creator/tempo_map.py`
- Test: `tests/test_tempo_map.py`

**Interfaces:**
- Produces:
  - `@dataclass TempoChange(tick: int, us_per_beat: int)` e `@dataclass TimeSigChange(tick: int, numerator: int, denominator: int)`;
  - `class TempoMap(ticks_per_beat: int = 480, tempos: List[TempoChange] = None, time_sigs: List[TimeSigChange] = None)`. O construtor ordena as listas, descarta tempos `<= 0`, insere 120 BPM (`500000`) e 4/4 no tick 0 se faltar entrada no tick 0, e remove entradas duplicadas no mesmo tick (a última vence);
  - os métodos `TempoMap.constant(bpm: float, numerator: int = 4, denominator: int = 4) -> TempoMap`, `tick_to_ms(tick: int) -> float`, `ms_to_tick(ms: float) -> int` (arredonda para o tick mais próximo), `initial_bpm() -> float`, `rescaled(ticks_per_beat: int) -> TempoMap`, `to_dict() -> dict` e `TempoMap.from_dict(d: dict) -> TempoMap`.

- [ ] **Step 1: Escreva os testes que devem falhar**

```python
def test_constant_120_one_beat_is_500ms():
    tm = TempoMap.constant(120.0)
    assert tm.tick_to_ms(480) == pytest.approx(500.0)
    assert tm.ms_to_tick(500.0) == 480

def test_two_tempos_accumulate_segments():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])  # 120 BPM, depois 60 BPM
    assert tm.tick_to_ms(960) == pytest.approx(1000.0)
    assert tm.tick_to_ms(1440) == pytest.approx(2000.0)
    assert tm.ms_to_tick(2000.0) == 1440

def test_roundtrip_ms_tick_within_one_tick():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(1000, 400000), TempoChange(5000, 650000)])
    for tick in range(0, 20000, 37):
        assert abs(tm.ms_to_tick(tm.tick_to_ms(tick)) - tick) <= 1

def test_missing_tick0_defaults_to_120bpm():
    tm = TempoMap(480, [TempoChange(960, 1000000)])
    assert tm.initial_bpm() == pytest.approx(120.0)
    assert tm.tick_to_ms(960) == pytest.approx(1000.0)

def test_zero_tempo_entry_is_discarded():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(480, 0)])
    assert len(tm.tempos) == 1

def test_rescaled_preserves_ms():
    tm = TempoMap(192, [TempoChange(0, 500000), TempoChange(384, 1000000)])
    tm2 = tm.rescaled(480)
    assert tm2.ticks_per_beat == 480
    assert tm2.tick_to_ms(960) == pytest.approx(tm.tick_to_ms(384))

def test_dict_roundtrip():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 600000)], [TimeSigChange(0, 4, 4), TimeSigChange(1920, 3, 4)])
    tm2 = TempoMap.from_dict(tm.to_dict())
    assert tm2.tempos == tm.tempos and tm2.time_sigs == tm.time_sigs
```

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/test_tempo_map.py -v`. Esperado: FAIL (`ModuleNotFoundError: src.creator.tempo_map`).
- [ ] **Step 3: Implemente `src/creator/tempo_map.py`.** A conversão é por segmentos: pré-calcule `ms_at[i]` no início de cada `TempoChange`. `tick_to_ms` acha o segmento por busca binária (`bisect`) nos ticks. `ms_to_tick` faz o mesmo nos `ms_at`. A fórmula de cada segmento é `ms = ms_at[i] + (tick - tick_i) * us_per_beat_i / ticks_per_beat / 1000`. `rescaled` multiplica os ticks por `novo/antigo` e arredonda.
- [ ] **Step 4:** Rode os testes. Esperado: PASS.
- [ ] **Step 5:** Commit com a mensagem `feat: TempoMap com várias mudanças de tempo e compasso`.

---

### Task 2: `ChartSong` guarda o mapa de tempo

**Files:**
- Modify: `src/creator/chart_model.py` (o dataclass `ChartSong`, `to_dict` e `from_dict`)
- Test: `tests/test_chart_model_tempo.py`

**Interfaces:**
- Consumes: `TempoMap` (Task 1).
- Produces:
  - o campo `ChartSong.tempo_map: Optional[TempoMap] = None`;
  - `ChartSong.get_tempo_map() -> TempoMap`:
    - devolve `self.tempo_map` se ele existir **e** `round(self.tempo_map.initial_bpm(), 2) == round(self.bpm, 2)`;
    - senão, devolve `TempoMap.constant(self.bpm, *self.time_signature)`.

  Essa regra implementa "mudar o BPM na UI descarta o mapa" sem tocar na UI, que atribui `song.bpm` direto em vários lugares. Documente isso num comentário no método.

- [ ] **Step 1: Escreva os testes que devem falhar**

```python
def test_default_song_uses_constant_map_from_bpm():
    s = ChartSong(bpm=150.0)
    assert s.get_tempo_map().initial_bpm() == pytest.approx(150.0)
    assert len(s.get_tempo_map().tempos) == 1

def test_imported_map_is_used_while_bpm_matches():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])
    s = ChartSong(bpm=120.0, tempo_map=tm)
    assert s.get_tempo_map() is tm

def test_changing_bpm_discards_imported_map():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])
    s = ChartSong(bpm=120.0, tempo_map=tm)
    s.bpm = 140.0
    assert len(s.get_tempo_map().tempos) == 1
    assert s.get_tempo_map().initial_bpm() == pytest.approx(140.0)

def test_to_dict_from_dict_keeps_tempo_map():
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(960, 1000000)])
    s2 = ChartSong.from_dict(ChartSong(bpm=120.0, tempo_map=tm).to_dict())
    assert s2.tempo_map is not None and s2.tempo_map.tempos == tm.tempos

def test_old_project_dict_without_tempo_map_loads():
    d = ChartSong(bpm=133.0).to_dict()
    d.pop("tempo_map", None)
    s = ChartSong.from_dict(d)
    assert s.tempo_map is None and s.get_tempo_map().initial_bpm() == pytest.approx(133.0)
```

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/test_chart_model_tempo.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implemente. `to_dict` grava `"tempo_map": self.tempo_map.to_dict()` só quando ele existe. `from_dict` lê com `data.get("tempo_map")`.
- [ ] **Step 4:** Rode o teste do passo 2 e depois `venv\Scripts\python -m pytest -q`. Esperado: tudo PASS.
- [ ] **Step 5:** Commit com a mensagem `feat: ChartSong guarda mapa de tempo importado`.

---

### Task 3: Importador lê todos os tempos (`.mid` e `.chart`)

**Files:**
- Modify: `src/creator/chart_importer.py` (`_parse_midi_into_song`, ~linha 231; `_parse_chart_file_into_song`, ~linha 157)
- Test: `tests/test_importer_tempo.py`

**Interfaces:**
- Consumes: `TempoMap`, `TempoChange`, `TimeSigChange` e `ChartSong.tempo_map` (Tasks 1–2).
- Produces: depois de importar, `song.tempo_map` fica com o mapa do arquivo, reescalado para 480 TPB, e `song.bpm == round(song.tempo_map.initial_bpm(), 2)`. Todos os `time_ms`/`duration_ms` são calculados pelo mapa. A duração é `tick_to_ms(fim) - tick_to_ms(início)`, mantendo os mínimos que já existem (100 ms no `.mid` e 120 ms no `.chart`).

- [ ] **Step 1: Escreva os testes que devem falhar.** Construa os arquivos no próprio teste com `mido` (MIDI) e com texto (`.chart`), usando `tmp_path`.

```python
def test_midi_tempo_change_mid_song(tmp_path):
    # trilha 0: set_tempo 120 BPM no tick 0 e 60 BPM no tick 960 (ticks_per_beat=480)
    # trilha "PART GUITAR": nota 96 (Expert green) no tick 1440, duração 480
    song = _import_mid(tmp_path, tempos=[(0, 500000), (960, 1000000)], guitar=[(1440, 480, 96)])
    n = song.guitar_notes[0]
    assert n.time_ms == pytest.approx(2000, abs=2)
    assert n.duration_ms == pytest.approx(1000, abs=2)
    assert len(song.tempo_map.tempos) == 2 and song.bpm == pytest.approx(120.0)

def test_midi_tempo_in_non_zero_track_is_used(tmp_path):
    # set_tempo 60 BPM no tick 480 colocado na trilha EVENTS, não na trilha 0
    song = _import_mid(tmp_path, tempos=[(0, 500000)], extra_tempo_in_events=(480, 1000000), guitar=[(960, 120, 96)])
    assert song.guitar_notes[0].time_ms == pytest.approx(1500, abs=2)

def test_midi_resolution_192_is_rescaled(tmp_path):
    song = _import_mid(tmp_path, tpb=192, tempos=[(0, 500000)], guitar=[(192, 96, 96)])
    assert song.guitar_notes[0].time_ms == pytest.approx(500, abs=2)
    assert song.tempo_map.ticks_per_beat == 480

def test_chart_multiple_bpm_events(tmp_path):
    # [Song] Resolution = 192; [SyncTrack] 0 = B 120000, 384 = B 60000, 0 = TS 4
    # [ExpertSingle] 576 = N 0 0
    song = _import_chart(tmp_path, resolution=192, bpms=[(0, 120000), (384, 60000)], expert_single=[(576, 0, 0)])
    assert song.guitar_notes[0].time_ms == pytest.approx(2000, abs=2)
    assert len(song.tempo_map.tempos) == 2
```

`_import_mid`/`_import_chart` são helpers locais do teste: gravam o arquivo em `tmp_path` e chamam `_parse_midi_into_song`/`_parse_chart_file_into_song` com um `ChartSong()` novo.

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/test_importer_tempo.py -v`. Esperado: FAIL nos asserts de tempo.
- [ ] **Step 3:** Implemente.
  - **`.mid`:** faça uma primeira passada em todas as trilhas acumulando o tick absoluto e coletando `set_tempo` e `time_signature`. Monte `TempoMap(mid.ticks_per_beat, ...)`, converta tudo por `tm.tick_to_ms`, inclusive os eventos `text`, e no fim atribua `song.tempo_map = tm.rescaled(480)`.
  - **`.chart`:** colete `N = B V` e `N = TS num [den_exp]` (o denominador é `2**den_exp`, padrão 4). Converta as notas depois de ler o arquivo inteiro, porque as seções de nota podem vir antes do `[SyncTrack]`: guarde as notas em ticks, monte o mapa e converta no fim.
- [ ] **Step 4:** Rode o teste do passo 2 e depois `-q` geral. Esperado: PASS.
- [ ] **Step 5:** Commit com a mensagem `fix: importador respeita todas as mudanças de tempo (.mid e .chart)`.

---

### Task 4: Gerador grava o mapa, `BEAT` por compasso, marcadores de `EVENTS` e notas sem sobreposição

**Files:**
- Modify: `src/creator/midi_generator.py` (todo o arquivo; os helpers `_build_*` passam a receber `tm: TempoMap` no lugar de `bpm: float`)
- Test: `tests/test_midi_generator.py`

**Interfaces:**
- Consumes: `ChartSong.get_tempo_map()` (Task 2) e o importador da Task 3 (nos testes de ida e volta).
- Produces:
  - `generate_rbn_midi(song, total_duration_ms=None, include_rb3_tracks=True) -> MidiFile`, com a mesma assinatura de hoje;
  - `ms_to_ticks(ms, bpm)`/`ticks_to_ms(ticks, bpm)` continuam existindo com a mesma assinatura e o mesmo comportamento, implementados via `TempoMap.constant(bpm)`;
  - regras novas:
    1. a trilha 0 grava todos os `set_tempo`/`time_signature` do mapa;
    2. a `BEAT` percorre os compassos com o compasso vigente: nota 12 no 1º tempo, 13 nos demais, cada batida com `ticks_per_beat * 4 / denominator` ticks, até o tick de `total_duration_ms`;
    3. a `EVENTS` remove de `song.events` qualquer `[music_start]`, `[music_end]` e `[end]` e regrava um de cada: `[music_start]` no tick 0, `[music_end]` no fim da última nota (ou em `total_duration_ms - 1000`, se não houver notas) e `[end]` em `total_duration_ms`, sempre depois de `[music_end]`;
    4. em cada trilha, se o fim de uma nota passar do próximo `note_on` da mesma altura, o fim é recortado para esse tick. Nessa situação o recorte vence a duração mínima de 120 ticks.

- [ ] **Step 1: Escreva os testes que devem falhar**

```python
def test_tempo_track_writes_all_tempo_changes():
    s = ChartSong(bpm=120.0, tempo_map=TempoMap(480, [TempoChange(0, 500000), TempoChange(1920, 400000)]))
    s.guitar_notes = [NoteEvent(time_ms=3000, lane="green", difficulty="Expert")]
    tempos = [m for m in generate_rbn_midi(s).tracks[0] if m.type == "set_tempo"]
    assert [m.tempo for m in tempos] == [500000, 400000]

def test_beat_track_follows_time_signature_change():
    # 4/4 até o tick 1920 e 3/4 depois: primeiros downbeats (nota 12) em 0, 1920, 3360
    ...assert downbeat_ticks[:3] == [0, 1920, 3360]

def test_events_have_single_markers_in_order():
    s = ChartSong(); s.events = [TextEvent(0, "[music_start]"), TextEvent(5000, "[end]")]
    s.guitar_notes = [NoteEvent(time_ms=4000, lane="green", difficulty="Expert")]
    texts = _event_texts(generate_rbn_midi(s))
    assert texts.count("[music_start]") == 1 and texts.count("[music_end]") == 1 and texts.count("[end]") == 1
    assert texts.index("[music_end]") < texts.index("[end]")

def test_dense_same_pitch_notes_do_not_overlap_and_survive_roundtrip(tmp_path):
    # 16 notas green Expert a cada 60 ms com duration_ms=100 (como sai do importador)
    s = ChartSong(bpm=200.0)
    s.guitar_notes = [NoteEvent(time_ms=1000 + i * 60, lane="green", duration_ms=100, difficulty="Expert") for i in range(16)]
    back = _roundtrip(s, tmp_path)   # generate_rbn_midi -> save -> _parse_midi_into_song
    assert len([n for n in back.guitar_notes if n.difficulty == "Expert"]) == 16

def test_roundtrip_with_tempo_changes_within_2ms(tmp_path):
    tm = TempoMap(480, [TempoChange(0, 500000), TempoChange(1920, 375000), TempoChange(7680, 600000)])
    s = ChartSong(bpm=120.0, tempo_map=tm)
    s.guitar_notes = [NoteEvent(time_ms=t, lane="red", difficulty="Expert") for t in range(500, 20000, 731)]
    back = _roundtrip(s, tmp_path)
    got = [n.time_ms for n in back.guitar_notes if n.difficulty == "Expert"]
    assert len(got) == len(s.guitar_notes)
    assert all(abs(a.time_ms - b) <= 2 for a, b in zip(s.guitar_notes, got))
```

Complete `test_beat_track_follows_time_signature_change` com um `ChartSong` de `tempo_map` com `TimeSigChange(0,4,4)` e `TimeSigChange(1920,3,4)`, coletando os ticks absolutos dos `note_on` de nota 12 da trilha `BEAT`.

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/test_midi_generator.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implemente as regras 1–4. Cada nota vira `start = tm.ms_to_tick(n.time_ms)` e `end = max(start + 120, tm.ms_to_tick(n.time_ms + n.duration_ms))`. Depois aplique a regra 4: agrupe os eventos por altura e ordene por início antes de inserir.
- [ ] **Step 4:** Rode o teste do passo 2 e depois `-q` geral. Esperado: PASS.
- [ ] **Step 5:** Commit com a mensagem `fix: gerador MIDI com mapa de tempo, BEAT por compasso e marcadores de EVENTS`.

---

### Task 5: Núcleo do validador e regras de MIDI

**Files:**
- Create: `src/creator/validation/__init__.py` (reexporta `Issue`, `validate_export`, `detect_target` e `format_issues_for_dialog` conforme cada task os cria), `src/creator/validation/issues.py`, `src/creator/validation/profiles.py`, `src/creator/validation/midi_rules.py`
- Test: `tests/validation/test_midi_rules.py` (e `tests/validation/__init__.py` vazio)

**Interfaces:**
- Produces:
  - `@dataclass Issue(level: str, code: str, message: str, location: str = "")`, com `level` em `{"error", "warning"}`;
  - `has_errors(issues) -> bool` em `issues.py`;
  - `@dataclass(frozen=True) TargetProfile`, com os campos:
    - `name: str`
    - `label: str` (nome para o usuário)
    - `verified_in_game: bool`
    - `allowed_tracks: FrozenSet[str]`
    - `require_beat: bool`
    - `require_end_markers: bool` (`[music_start]`, `[music_end]`, `[end]`)
    - `forbid_tracks: FrozenSet[str]` (ex.: o RB2 proíbe `PART KEYS` e `PART REAL_*`)
  - `PROFILES: Dict[str, TargetProfile]`, com as chaves `clonehero`, `rb3_ps3`, `rb2`, `xbox360` e `ps4`;
  - `validate_midi(path: str, profile: TargetProfile) -> List[Issue]`;
  - `midi_track_names(path: str) -> Set[str]`, que devolve um conjunto vazio se o arquivo for ilegível (usado pela Task 6).

  As trilhas conhecidas de `allowed_tracks` (todas, menos onde o perfil proíbe) são: `BEAT`, `EVENTS`, `VENUE`, `PART GUITAR`, `PART GUITAR COOP`, `PART RHYTHM`, `PART BASS`, `PART DRUMS`, `PART KEYS`, `PART VOCALS`, `HARM1`, `HARM2`, `HARM3`, `PART REAL_GUITAR`, `PART REAL_GUITAR_22`, `PART REAL_BASS`, `PART REAL_BASS_22`, `PART REAL_KEYS_X/H/M/E`, `PART KEYS_ANIM_LH`, `PART KEYS_ANIM_RH`, `PART REAL_KEYS_ANIM_LH` e `PART REAL_KEYS_ANIM_RH`.

  Os valores de cada perfil:
  - `clonehero`: `require_beat=False`, `require_end_markers=False`, `verified_in_game=True`;
  - `rb3_ps3` e `ps4`: `True`, `True`, `True`;
  - `rb2`: `True`, `True`, `False`, mais `forbid_tracks` com `PART KEYS` e todas as `PART REAL_*`;
  - `xbox360`: `True`, `True`, `False`.

  Códigos de `Issue` emitidos por `validate_midi`:

  | código | nível | quando |
  |---|---|---|
  | `MIDI_UNREADABLE` | error | o `mido` não abre o arquivo |
  | `MIDI_NOT_TYPE1` | error | `type != 1` |
  | `MIDI_TPB_NOT_480` | warning | `ticks_per_beat != 480` |
  | `MIDI_NO_TEMPO` | error | nenhum `set_tempo` em lugar nenhum |
  | `MIDI_UNKNOWN_TRACK` | warning | nome fora de `allowed_tracks` |
  | `MIDI_FORBIDDEN_TRACK` | error | nome em `forbid_tracks` |
  | `MIDI_DUPLICATE_TRACK` | error | dois nomes iguais |
  | `MIDI_NO_EVENTS` / `MIDI_NO_BEAT` | error se o perfil exigir, senão warning | trilha ausente |
  | `MIDI_MISSING_MARKER` | error se `require_end_markers`, senão warning | falta `[music_start]`, `[music_end]` ou `[end]` |
  | `MIDI_END_BEFORE_NOTES` | error | `[end]` antes do último `note_off` de qualquer `PART` |
  | `MIDI_BEAT_SHORT` | warning | a última nota da `BEAT` cai mais de 1 compasso antes da última nota tocável |
  | `MIDI_NOTE_OUT_OF_RANGE` | warning | uma nota em `PART GUITAR/BASS/KEYS/DRUMS` fora do conjunto aceito: valores de `FRET_NOTES`/`DRUM_NOTES`, 95, 103, 105–112, 116, 120–124, 127, 0–12 em KEYS (animação) e 12–15 (animação) |
  | `MIDI_UNTERMINATED_NOTE` | error | `note_on` sem `note_off` até o fim da trilha |
  | `MIDI_OVERLAPPING_NOTE` | error | `note_on` de uma altura que já está ativa na mesma trilha |
  | `MIDI_VOCAL_NOTE_OUTSIDE_PHRASE` | warning | nota vocal 36–84 fora de um intervalo da nota 105/106 |
  | `MIDI_PRO_FRET_VELOCITY` | error | nota de corda Pro Guitar/Bass (base + 0..5) com velocidade fora de 100–122 (22 casas no `_22`; 17 é o padrão do modelo) |

  Os locais seguem o formato `"<arquivo> › <trilha> › tick <n>"`. Agrupe os avisos repetidos: no máximo 1 `Issue` por código e trilha, com a contagem na mensagem (ex.: "37 notas fora da faixa"). Isso evita milhares de itens.

- [ ] **Step 1: Escreva os testes que devem falhar.** Use um helper `_write_mid(tmp_path, tracks)` que monta MIDIs mínimos com `mido`.

```python
def test_generated_song_passes_rb3_profile(tmp_path):
    s = auto_generate_chart(ChartSong(title="T", artist="A", bpm=120.0), total_duration_ms=60000,
                            selected_instruments=["guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys"])
    p = tmp_path / "x.mid"; save_midi(generate_rbn_midi(s), str(p))
    assert [i for i in validate_midi(str(p), PROFILES["rb3_ps3"]) if i.level == "error"] == []

def test_unreadable_file_is_error_not_exception(tmp_path):
    p = tmp_path / "bad.mid"; p.write_bytes(b"not a midi")
    assert [i.code for i in validate_midi(str(p), PROFILES["clonehero"])] == ["MIDI_UNREADABLE"]

def test_missing_beat_is_error_for_rb3_warning_for_ch(tmp_path): ...
def test_forbidden_keys_track_on_rb2(tmp_path): ...            # código MIDI_FORBIDDEN_TRACK, level error
def test_end_before_last_note(tmp_path): ...                    # MIDI_END_BEFORE_NOTES
def test_overlapping_same_pitch(tmp_path): ...                  # MIDI_OVERLAPPING_NOTE
def test_unterminated_note(tmp_path): ...                       # MIDI_UNTERMINATED_NOTE
def test_pro_guitar_bad_velocity(tmp_path): ...                 # nota 96 com velocity 90 em PART REAL_GUITAR
def test_vocal_note_outside_phrase_warns(tmp_path): ...         # nota 60 sem 105 em volta
def test_repeated_warnings_are_grouped(tmp_path):               # 50 notas fora da faixa -> 1 Issue com "50" na mensagem
    ...
```

Cada `...` monta o MIDI mínimo que provoca exatamente aquele código e confere `code` e `level`.

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/validation/test_midi_rules.py -v`. Esperado: FAIL (módulo inexistente).
- [ ] **Step 3:** Implemente `issues.py`, `profiles.py` e `midi_rules.py`. Leia com `mido.MidiFile(path)` dentro de `try` e percorra as trilhas uma vez acumulando o tick absoluto.
- [ ] **Step 4:** Rode o teste do passo 2 e depois `-q` geral. Esperado: PASS. Se `test_generated_song_passes_rb3_profile` falhar por uma regra que o gerador quebra, corrija o gerador, não a regra, a menos que a regra contradiga a tabela acima.
- [ ] **Step 5:** Commit com a mensagem `feat: validador de MIDI por perfil de destino`.

---

### Task 6: Regras de `songs.dta` e `.mogg`

**Files:**
- Create: `src/creator/validation/dta_parser.py`, `src/creator/validation/dta_rules.py`, `src/creator/validation/mogg_rules.py`
- Test: `tests/validation/test_dta_rules.py`, `tests/validation/test_mogg_rules.py`

**Interfaces:**
- Consumes: `Issue`, `TargetProfile` e `midi_track_names` (Task 5); `create_unencrypted_mogg` (existente, para gerar os fixtures).
- Produces:
  - `parse_dta(text: str) -> List[Any]`: uma s-expression em que cada lista vira `list`, `"strings"` viram `str` e símbolos e números viram `str`/`int`/`float`. Ignora `;` até o fim da linha, aceita `'símbolo'` e trata `{ }` como lista. Lança `DtaSyntaxError(msg, line)` em caso de desbalanceamento;
  - `validate_dta(path: str, profile: TargetProfile, midi_tracks_by_song: Optional[Dict[str, Set[str]]] = None, mogg_channels_by_song: Optional[Dict[str, int]] = None) -> List[Issue]`, que valida **cada** entrada de topo (uma por música do pacote);
  - `@dataclass MoggInfo(version: int, ogg_offset: int, channels: Optional[int], sample_rate: Optional[int])`;
  - `read_mogg_info(path) -> Optional[MoggInfo]`;
  - `validate_mogg(path) -> List[Issue]`.

  Códigos de `validate_dta`:

  | código | nível | quando |
  |---|---|---|
  | `DTA_UNREADABLE` | error | o arquivo não abre ou o encoding é inválido (tente `utf-8` e depois `latin-1`) |
  | `DTA_SYNTAX` | error | `DtaSyntaxError`, com o número da linha |
  | `DTA_MISSING_FIELD` | error | falta `name`, `artist`, `song` (com `name`, `tracks`, `pans`, `vols` e `cores` dentro), `rank`, `song_id`, `game_origin` ou `vocal_parts` (que pode estar dentro de `song` ou no topo) |
  | `DTA_CHANNEL_MISMATCH` | error | a contagem de `pans`, `vols` e `cores` difere, ou um índice de `tracks` é maior ou igual a essa contagem |
  | `DTA_MOGG_CHANNELS` | error | a contagem de `pans` é diferente de `mogg_channels_by_song[shortname]` (quando informado) |
  | `DTA_RANK_WITHOUT_TRACK` | warning | `rank` > 0 para um instrumento cuja trilha não está em `midi_tracks_by_song[shortname]` (mapa: `guitar→PART GUITAR`, `bass→PART BASS`, `drum→PART DRUMS`, `keys→PART KEYS`, `vocals→PART VOCALS`, `real_guitar→PART REAL_GUITAR`, `real_bass→PART REAL_BASS`, `real_keys→PART REAL_KEYS_X`) |
  | `DTA_VOCAL_PARTS` | error | `vocal_parts` > 0 sem `PART VOCALS`, ou `PART VOCALS` com `vocal_parts 0` (quando as trilhas forem informadas) |

  Códigos de `validate_mogg`:

  | código | nível | quando |
  |---|---|---|
  | `MOGG_UNREADABLE` | error | arquivo ausente ou com menos de 20 bytes |
  | `MOGG_ENCRYPTED` | warning | a versão não é `0x0A`, ou seja, está criptografado (válido para o jogo, mas sem leitura dos canais) |
  | `MOGG_BAD_OFFSET` | error | os bytes no `ogg_offset` não são `OggS` |
  | `MOGG_BAD_OGG` | error | o `soundfile` não abre o trecho OGG (copiado para um arquivo temporário) |

- [ ] **Step 1: Escreva os testes que devem falhar**

```python
def test_parse_pack_with_two_songs_comments_and_parens_in_strings():
    text = '; pack\n(song_a (name "Song (Live)") (artist "X"))\n(song_b (name "B") (artist "Y"))\n'
    tree = parse_dta(text)
    assert [e[0] for e in tree] == ["song_a", "song_b"]
    assert tree[0][1] == ["name", "Song (Live)"]

def test_unbalanced_reports_line():
    with pytest.raises(DtaSyntaxError) as e:
        parse_dta('(a\n(b "x")\n')
    assert e.value.line >= 1

def test_midguitar_generated_dta_passes(tmp_path):
    s = ChartSong(title="T", artist="A"); s.guitar_notes = [NoteEvent(1000, "green")]
    p = tmp_path / "songs.dta"; p.write_text(generate_songs_dta_content(s, "ta"), encoding="utf-8")
    errs = [i for i in validate_dta(str(p), PROFILES["rb3_ps3"], {"ta": {"PART GUITAR"}}) if i.level == "error"]
    assert errs == []

def test_channel_mismatch(tmp_path): ...        # pans com 2 valores e vols com 3 -> DTA_CHANNEL_MISMATCH
def test_mogg_channels_mismatch(tmp_path): ...  # pans 2, mogg_channels_by_song={"ta": 8} -> DTA_MOGG_CHANNELS
def test_rank_without_track_warns(tmp_path): ...
def test_vocal_parts_without_vocals(tmp_path): ...

def test_generated_mogg_is_valid(tmp_path):
    wav = _write_sine_wav(tmp_path, seconds=2, channels=2)   # via soundfile
    mogg = tmp_path / "x.mogg"; assert create_unencrypted_mogg(str(wav), str(mogg))
    assert validate_mogg(str(mogg)) == []
    assert read_mogg_info(str(mogg)).channels == 2

def test_truncated_mogg_is_error(tmp_path):
    p = tmp_path / "t.mogg"; p.write_bytes(b"\x0a\x00\x00\x00")
    assert [i.code for i in validate_mogg(str(p))] == ["MOGG_UNREADABLE"]

def test_bad_offset(tmp_path): ...              # cabeçalho 0x0A com offset apontando para lixo -> MOGG_BAD_OFFSET
```

Observação: se o `convert_audio_to_ogg` não conseguir gerar OGG a partir de WAV neste ambiente, `test_generated_mogg_is_valid` deve escrever o OGG direto com `soundfile.write(..., format="OGG", subtype="VORBIS")` e passar o `.ogg` ao `create_unencrypted_mogg`.

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/validation -v`. Esperado: FAIL nos testes novos.
- [ ] **Step 3:** Implemente o parser (um tokenizador simples que acompanha o número da linha), as regras e o leitor de `.mogg` (`struct.unpack("<II", ...)` nos 8 primeiros bytes).
- [ ] **Step 4:** Rode `venv\Scripts\python -m pytest -q`. Esperado: PASS.
- [ ] **Step 5:** Commit com a mensagem `feat: validador de songs.dta e .mogg`.

---

### Task 7: Perfis de destino e `validate_export`

**Files:**
- Create: `src/creator/validation/targets.py`
- Test: `tests/validation/test_targets.py`

**Interfaces:**
- Consumes: tudo das Tasks 5–6 e os exportadores existentes (`export_clone_hero_song`, `export_rb3_song_package`, `export_ps3_pkg_structure`, `export_rb2_song_package`, `export_xbox360_structure` e `export_ps4_structure`).
- Produces:
  - `validate_export(folder: str, target: str) -> List[Issue]`. Um `target` desconhecido devolve `[Issue("error", "TARGET_UNKNOWN", ...)]`, e qualquer exceção interna vira `Issue("error", "VALIDATOR_CRASH", ...)`;
  - `detect_target(folder: str) -> Optional[str]`:
    - `song.ini` ou `notes.mid`/`notes.chart` na pasta → `clonehero`;
    - existe `songs/songs.dta` (em qualquer nível abaixo da pasta) → `rb3_ps3`;
    - existe `*.songdta_ps4` → `ps4`;
    - existe um arquivo que começa com `b"CON "` ou `b"LIVE"` → `xbox360`;
    - senão, `None`. O `rb2` nunca é detectado automaticamente, porque usa a mesma estrutura do `rb3_ps3`.

  O que cada perfil exige (descreve **o jogo**, não o exportador atual):
  - **`clonehero`** (raiz = pasta da música):
    - `notes.mid` ou `notes.chart` (senão `LAYOUT_MISSING_CHART`, error);
    - `song.ini` com seção `[song]` e as chaves `name` e `artist` (senão `CH_INI_MISSING`/`CH_INI_FIELD`, error/warning);
    - ao menos um áudio com nome-base em `song, guitar, bass, rhythm, drums, drums_1..4, vocals, vocals_1, vocals_2, keys, crowd` e extensão `.ogg/.opus/.mp3/.wav` (senão `CH_NO_AUDIO`, error);
    - `validate_midi` no `notes.mid`.
  - **`rb3_ps3` e `rb2`** (procura `songs/songs.dta` a partir da raiz, inclusive em `USRDIR/songs`):
    - `validate_dta`;
    - para cada shortname: a pasta `songs/<s>/` (`LAYOUT_MISSING_SONG_DIR`, error), `<s>.mid.edat` (`PS3_MISSING_EDAT`, error);
    - se só houver `<s>.mid` solto, `validate_midi` nele e `PS3_PLAIN_MID`, error ("o PS3 exige .mid.edat");
    - `<s>.mogg` (`LAYOUT_MISSING_MOGG`, error) + `validate_mogg`;
    - `gen/<s>.milo_ps3` (`PS3_MISSING_MILO`, warning) e `gen/<s>_keep.png_ps3` (`PS3_MISSING_ART`, warning, só se `album_art` não for `FALSE` no DTA);
    - um `.mid.edat` que não começa com `b"NPD\x00"` gera `PS3_BAD_EDAT`, error;
    - os canais do `.mogg` e as trilhas do `.mid` (quando legível) alimentam `validate_dta`.
  - **`xbox360`:** ao menos um arquivo que começa com `b"CON "` ou `b"LIVE"` em qualquer nível (senão `XBOX_NO_CON_PACKAGE`, error, com a mensagem "o Xbox 360 exige um pacote CON/LIVE; pastas soltas só funcionam em Xenia/Aurora com plugins"). O conteúdo do pacote não é lido nesta fase.
  - **`ps4`:** para cada `*.songdta_ps4` encontrado, os irmãos `<s>.rbmid_ps4`, `<s>.mogg` e `<s>.moggsong` (cada um com error se ausente) e `<s>.png_ps4` (warning) + `validate_mogg`. Se não houver nenhum `.songdta_ps4`, gera `PS4_NO_SONGDTA` (error).
  - Quando `profile.verified_in_game` for `False`, acrescente um `Issue("warning", "PROFILE_UNVERIFIED", "Perfil <label> ainda não foi confirmado em jogo real")`.

- [ ] **Step 1: Escreva os testes que devem falhar**

```python
@pytest.fixture
def song():
    s = auto_generate_chart(ChartSong(title="Teste", artist="Banda", bpm=120.0), total_duration_ms=40000,
                            selected_instruments=["guitar", "bass", "drum"])
    s.audio_path = str(_write_ogg(...))  # OGG de 3 s gerado com soundfile
    return s

def test_clonehero_export_has_no_errors(song, tmp_path):
    d = export_clone_hero_song(song, str(tmp_path))
    assert [i for i in validate_export(d, "clonehero") if i.level == "error"] == []
    assert detect_target(d) == "clonehero"

def test_ps3_export_flags_missing_edat(song, tmp_path):
    d = export_ps3_pkg_structure(song, str(tmp_path))
    codes = {i.code for i in validate_export(d, "rb3_ps3")}
    assert "PS3_MISSING_EDAT" in codes and "PS3_PLAIN_MID" in codes

def test_xbox_export_flags_no_con(song, tmp_path):
    d = export_xbox360_structure(song, str(tmp_path))
    codes = {i.code for i in validate_export(d, "xbox360")}
    assert "XBOX_NO_CON_PACKAGE" in codes and "PROFILE_UNVERIFIED" in codes

def test_rb2_export_has_no_forbidden_tracks(song, tmp_path):
    song.keys_notes = [NoteEvent(1000, "green")]
    d = export_rb2_song_package(song, str(tmp_path))
    assert "MIDI_FORBIDDEN_TRACK" not in {i.code for i in validate_export(d, "rb2")}

def test_empty_folder_and_unknown_target_do_not_raise(tmp_path):
    assert validate_export(str(tmp_path), "clonehero")[0].code == "LAYOUT_MISSING_CHART"
    assert validate_export(str(tmp_path), "nintendo")[0].code == "TARGET_UNKNOWN"
```

Os testes que **esperam** erros (PS3/Xbox) documentam a lista de trabalho das Fases 3–4. Ponha neles o comentário `# Fase 3/4 vai inverter este teste`.

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/validation/test_targets.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implemente `targets.py` e reexporte `validate_export` e `detect_target` em `validation/__init__.py`.
- [ ] **Step 4:** Rode `venv\Scripts\python -m pytest -q`. Esperado: PASS. Se `test_clonehero_export_has_no_errors` falhar, registre o código no relatório da task: é trabalho da Fase 2. Troque o assert por um `xfail(strict=True, reason="<código> — Fase 2")` só depois de confirmar que a regra está certa.
- [ ] **Step 5:** Commit com a mensagem `feat: perfis de destino e validate_export`.

---

### Task 8: Testes com os customs de referência

**Files:**
- Create: `tests/test_reference_songs.py`, `tests/REFERENCIAS.md` (como montar a pasta `MIDGUITAR_REFS`)

**Interfaces:**
- Consumes: a fixture `refs_dir` (Task 0), `detect_target`/`validate_export` (Task 7), `import_song_from_folder` (existente) e `generate_rbn_midi`/`save_midi` (Task 4).

- [ ] **Step 1:** Escreva o `tests/REFERENCIAS.md` explicando, em poucas linhas:
  - `MIDGUITAR_REFS` aponta para uma pasta em que cada subpasta é um custom que **funciona no jogo**: uma pasta CH com `song.ini` e `notes.mid`/`.chart`, ou uma pasta RB3 com `songs/songs.dta`;
  - a pasta fica fora do Git;
  - o comando para rodar: `set MIDGUITAR_REFS=D:\RefCustoms` e `venv\Scripts\python -m pytest -m refs -v`.
- [ ] **Step 2:** Escreva os testes parametrizados por subpasta. Use `pytest_generate_tests` no próprio arquivo, lendo `MIDGUITAR_REFS`; se a variável não existir, gere um único caso que chama `pytest.skip`.

```python
@pytest.mark.refs
def test_reference_passes_validator(ref_folder):
    target = detect_target(str(ref_folder))
    assert target is not None, "não reconheci o formato desta pasta"
    errors = [i for i in validate_export(str(ref_folder), target) if i.level == "error"]
    assert errors == [], "custom que funciona no jogo foi acusado — a REGRA está errada:\n" + "\n".join(f"{i.code}: {i.message}" for i in errors)

@pytest.mark.refs
def test_reference_roundtrip_keeps_note_times(ref_folder, tmp_path):
    original = import_song_from_folder(str(ref_folder))
    if not _has_any_notes(original):
        pytest.skip("MIDI ilegível pelo importador (ex.: só .mid.edat)")
    out = tmp_path / "notes.mid"; save_midi(generate_rbn_midi(original), str(out))
    again = import_song_from_folder(str(tmp_path))
    for track in ["guitar", "bass", "drum", "keys", "pro_guitar", "pro_bass", "pro_keys", "vocal"]:
        for diff in ["Expert", "Hard", "Medium", "Easy"]:
            a, b = _times(original, track, diff), _times(again, track, diff)
            assert len(a) == len(b), f"{track}/{diff}: {len(a)} -> {len(b)} notas"
            assert all(abs(x - y) <= 2 for x, y in zip(a, b)), f"{track}/{diff}: dessincronizou"
```

  `_times(song, track, diff)` devolve a lista ordenada de `time_ms`. Para `vocal`, use `song.vocal_notes`, sem dificuldade (só para `diff == "Expert"`). Antes de chamar `import_song_from_folder(tmp_path)`, copie o `song.ini` original para `tmp_path` quando ele existir.

- [ ] **Step 3:** Rode `venv\Scripts\python -m pytest -m refs -v` **sem** `MIDGUITAR_REFS`. Esperado: `skipped`.
- [ ] **Step 4:** Peça ao dono o caminho da pasta de referências e rode `venv\Scripts\python -m pytest -m refs -v` com a variável definida.
  - Para cada falha em `test_reference_passes_validator`, **corrija a regra ou o perfil** (Tasks 5–7) e anote o motivo num comentário na regra.
  - Para cada falha de ida e volta, corrija o importador ou o gerador.
  - Repita até passar. Esperado: PASS em todos os casos (ou `skip` documentado).
- [ ] **Step 5:** Commit com a mensagem `test: validação e ida-e-volta contra customs de referência`.

---

### Task 9: Resultado da validação na UI de exportação

**Files:**
- Create: `src/creator/validation/report.py`
- Modify: `src/ui/creator_studio_dialog.py` (os handlers `_on_convert_to_rb3` ~2483, `_on_export_rb2` ~2496, `_on_export_ps3_pkg` ~2514, `_on_convert_to_clone_hero` ~2531, `_on_export_xbox360` ~2543 e `_on_export_ps4` ~2561)
- Test: `tests/validation/test_report.py`

**Interfaces:**
- Consumes: `validate_export` e `Issue`.
- Produces:
  - `format_issues_for_dialog(issues: List[Issue], limit: int = 10) -> str`:
    - devolve `""` se `issues` estiver vazio;
    - senão, começa com `"\n\n⚠️ Verificação de compatibilidade: X erro(s), Y aviso(s)"`;
    - depois vêm até `limit` linhas `"• ❌ <mensagem>"`/`"• ⚠️ <mensagem>"`, com os erros primeiro;
    - se sobrar algo, a última linha é `"• … e mais N item(ns)"`;
  - `CreatorStudioDialog._show_export_result(self, title: str, message: str, pkg_dir: str, target: str)`:
    - chama `validate_export` dentro de `try` (uma exceção vira o texto `"\n\n⚠️ Não foi possível verificar a compatibilidade: <erro>"`);
    - usa `messagebox.showwarning` se houver algum erro, senão `showinfo`;
    - mantém o título e a mensagem originais de cada handler.

  Destinos de cada handler: `_on_convert_to_rb3` → `rb3_ps3`, `_on_export_ps3_pkg` → `rb3_ps3`, `_on_export_rb2` → `rb2`, `_on_convert_to_clone_hero` → `clonehero`, `_on_export_xbox360` → `xbox360` e `_on_export_ps4` → `ps4`.

- [ ] **Step 1: Escreva os testes que devem falhar**

```python
def test_empty_issues_gives_empty_text():
    assert format_issues_for_dialog([]) == ""

def test_errors_first_and_limit():
    issues = [Issue("warning", "W", f"aviso {i}") for i in range(8)] + [Issue("error", "E", f"erro {i}") for i in range(5)]
    text = format_issues_for_dialog(issues, limit=10)
    lines = [l for l in text.splitlines() if l.startswith("• ")]
    assert lines[0].startswith("• ❌") and len(lines) == 11 and lines[-1] == "• … e mais 3 item(ns)"
    assert "5 erro(s), 8 aviso(s)" in text
```

- [ ] **Step 2:** Rode `venv\Scripts\python -m pytest tests/validation/test_report.py -v`. Esperado: FAIL.
- [ ] **Step 3:** Implemente o `report.py` e o `_show_export_result`, e troque o `messagebox.showinfo(...)` final de cada um dos 6 handlers por `self._show_export_result(<título>, <mensagem>, pkg_dir, "<destino>")`.
- [ ] **Step 4:** Rode `venv\Scripts\python -m pytest -q`. Esperado: PASS.
- [ ] **Step 5: Verificação manual.** Rode `venv\Scripts\python src/main.py`, abra o Estúdio, carregue um MP3 curto, gere tudo e exporte para Clone Hero e para PS3. Esperado:
  - no Clone Hero, a mensagem de sucesso sem bloco ⚠️, ou só com avisos;
  - no PS3, um `showwarning` com o bloco listando `PS3_MISSING_EDAT`/`PS3_PLAIN_MID`.

  Se a UI não puder ser aberta nesta sessão, diga isso no relatório. Não declare a verificação como feita.
- [ ] **Step 6:** Commit com a mensagem `feat: mostrar verificação de compatibilidade após exportar`.

---

### Task 10: Verificação final da fase

- [ ] **Step 1:** Rode `venv\Scripts\python -m pytest -v` sem `MIDGUITAR_REFS`. Esperado: tudo PASS, menos os testes `refs`, que ficam `skipped`.
- [ ] **Step 2:** Rode com `MIDGUITAR_REFS` definida. Esperado: PASS.
- [ ] **Step 3:** Confira os critérios de sucesso da spec:
  - (a) `test_generated_song_passes_rb3_profile` e `test_clonehero_export_has_no_errors` passam;
  - (b) `test_reference_passes_validator` passa para todos os customs;
  - (c) `test_reference_roundtrip_keeps_note_times` passa.
- [ ] **Step 4:** Escreva um resumo dos códigos de erro que os exportadores ainda geram (saída de `validate_export` para cada destino, com uma música de exemplo) em `docs/superpowers/specs/2026-10-27-fase1-pendencias-por-destino.md`. Essa é a entrada das Fases 2–5. Commit com a mensagem `docs: pendências de compatibilidade por destino`.
