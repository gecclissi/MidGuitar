# Diagnóstico completo de funcionalidades (2026-11-16)

Passo 1 do programa de testes. Só diagnóstico: nenhum código do produto foi alterado.
Testes de aceitação novos em `tests/acceptance/test_diagnostico.py` (13 passam, 24 `xfail(strict=True)`
descrevem os bugs abaixo; quando um bug for corrigido o teste vira XPASS e acusa: tire o xfail).
`pytest -q`: **115 passed, 2 skipped, 24 xfailed**.

Legenda: ✅ funciona · ⚠️ parcial · ❌ quebrado/inexistente · 🖐 manual (precisa de hardware, jogo ou olho humano).
Severidade: **C** crítica (resultado inutilizável no jogo) · **A** alta · **M** média · **B** baixa.

Referências usadas (cópias em scratch, originais intocados): Joe Dassin (pasta Clone Hero, 154 mudanças de
tempo), CON do Xbox (Joe Dassin), PS3 extraídos (Gorillaz `.mogg` v13, 5SOS `.mogg` v11, `.mid.edat` NPD),
`Gorillaz - Andromeda.pkg`, mod GHWT:DE (PAVLO). Não existe `.chart` real: usei um `.chart` sintético.

## 1. Importação

| Funcionalidade | Status | Evidência | Código | Sev |
|---|---|---|---|---|
| Pasta Clone Hero (`notes.mid`) | ⚠️ | Notas por trilha/dificuldade batem 100% com a fonte (ex.: guitarra X/H/M/E 1468/1266/1262/528; Pro Guitar 3037/2030/636/159; Pro Keys 727/610/463/347), 154 tempos, 14 eventos, 409 sílabas. **Perde**: overdrive 116 (15→0), marcadores de tom 110-112 (15→0), fills 120-124 (190→0), frases vocais 105 (35→1 ao exportar), canais de Pro Guitar (ghost/abafada), HARM1-3, PART RHYTHM/GHL/ELITE_DRUMS/REAL_GUITAR_22/VENUE. HOPO forçado (101) vira "nota" com lane `force_hopo`. | `chart_importer._parse_midi_into_song` | A |
| `song.ini` | ⚠️ | Lê nome/artista/álbum/ano/gênero/charter/diff_guitar/bass/drums/keys/band. Ignora `preview_start_time` (72497→30000), `diff_vocals`, `diff_*_real`, `pro_drums`, `delay`, `song_length`, `hopo_frequency`. | `chart_importer.import_song_from_folder` | M |
| Pasta com `notes.chart` | ⚠️ | Notas, sustain e mapa de tempo/compasso corretos. Ignora artista (compara com "Artista Desconhecido", padrão real é "Artista"), `[Events]`, star power `S 2`, forçadas/open `N 5/6/7`. Bateria vira lanes `orange`/`red` (ver bateria abaixo). | `_parse_chart_file_into_song` | M |
| Pasta RB3 solta (`songs/<x>/x.mid`) | ⚠️ | Só funciona apontando para `songs/<x>/`. Na raiz do pacote ou em `songs/` carrega 0 notas. `songs.dta` só é lido no formato de 1 linha que o próprio app gera. | `import_song_from_folder` | M |
| Pasta PS3 extraída (`.mid.edat` + `.mogg` criptografado) | ❌ | 0 notas (`.mid.edat` não é lido), título "Nova Música" (`songs.dta` real com chaves entre aspas e quebras de linha não casa a regex), `audio_path` aponta para `*_extracted.ogg` **que não existe**: exportações saem sem áudio, sem aviso. | `import_song_from_folder` | A |
| Pacote CON do Xbox 360 (arquivo) | ❌ | `NotADirectoryError`; a UI só aceita pastas. Não há leitor STFS. | — | A |
| `.pkg` do PS3 direto | ❌ | `NotADirectoryError`; não há leitor de PKG (só o script descartável `music/_tools/pkg_debug_extract.py`). | — | A |
| Mod GHWT:DE (`.pak.xen`/`.fsb.xen`) | ❌ | Lê só o título ([ModInfo]/[SongInfo] por acaso); 0 notas, sem áudio. | — | M |
| `.mid` solto | ⚠️ | Funciona se estiver sozinho numa pasta (qualquer nome). Soltar um `.mid` na janela é ignorado (drop aceita só pasta/áudio/letra). | `_on_files_dropped` | B |
| `.mogg` solto | ⚠️ | Não criptografado (0x0A): extrai OGG ✅. Criptografado (0x0B/0x0D): devolve o próprio `.mogg`, nada é gravado; quem chama trata como sucesso. Grava `*_extracted.ogg` **ao lado da origem**. | `_load_audio_file_smart`, `extract_ogg_from_mogg` | M |

## 2. Áudio

| Funcionalidade | Status | Evidência | Código | Sev |
|---|---|---|---|---|
| `analyze_audio_file` | ⚠️ | Duração/início/fim corretos (opus 245,5 s). BPM com resolução de 50 ms: clique 128→133, 145→150, 166→171; stem de guitarra do Joe (166 BPM)→80. `.mogg` criptografado → devolve padrões silenciosamente (180 s, 120 BPM). | `mogg_generator.analyze_audio_file` | M |
| `convert_audio_to_ogg` wav/mp3 | ✅ | WAV e MP3 → OGG Vorbis. | `convert_audio_to_ogg` | — |
| `convert_audio_to_ogg` opus | ❌ | `.opus` começa com `OggS` e é só **copiado**: sai `.ogg` com Opus dentro. | `convert_audio_to_ogg` | C |
| `create_unencrypted_mogg` | ⚠️ | Cabeçalho 0x0A + tabela correta a partir de WAV/OGG Vorbis; ida e volta OK. A partir de `.opus` o `.mogg` leva Opus (RB3 não toca). Sempre 2 canais (só o 1º áudio). | `create_unencrypted_mogg` | C |
| `extract_ogg_from_mogg` | ✅ | Não gera lixo em `.mogg` criptografado (devolve a origem). Problema está em quem chama (importador). | `extract_ogg_from_mogg` | — |
| Stems multitrack | ❌ | DTA declara 8 canais fixos (`guitar 0 1, bass 2, drum 3 4, keys 5 6, vocals 7`) quando há >1 stem, mas o `.mogg` tem 2 canais (validador: `DTA_MOGG_CHANNELS`). Stems `.opus` copiados soltos para a pasta da música. No Clone Hero, `song.ogg` = cópia do `guitar.opus` + todos os stems → guitarra dobrada. | exportadores, `rb3_dta_exporter.generate_songs_dta_content` | A |

## 3. Letras e vocais

| Funcionalidade | Status | Evidência | Código | Sev |
|---|---|---|---|---|
| `.txt` / `.lrc` / `.srt` | ✅ | txt a partir de 4 s no BPM; lrc/srt nos tempos marcados; nenhuma sílaba com timestamp ou índice. | `lyric_processor.align_lyrics_to_song` | — |
| Divisão silábica | ⚠️ | Boa em PT/FR (`a-mou-reux`, `can-tan-do`); erra inglês (`lo-ve`). | `syllabify_word` | B |
| Geração de vocal | ✅ | 13 notas para 2 versos, fim de frase marcado. Altura é um ciclo fixo (60..72). | `auto_generate_chart` | B |
| Sem letra = sem microfone | ✅ | 0 notas vocais, `(vocal_parts 0)`. Obs.: `tracks` do DTA ainda lista `vocals`. | `auto_generate_chart`, DTA | B |

## 4. Auto-chart e edição

| Funcionalidade | Status | Evidência | Código | Sev |
|---|---|---|---|---|
| Banda Completa / Kit RB2-GH / Só Guitarra, Baixo, Teclado, Pro Guitar, Pro Bass, Pro Keys, Vocal | ✅ | Áudio real (60 s do stem de guitarra): todos geram só os instrumentos pedidos, nas 4 dificuldades (ex.: guitarra 147/140/89/40), em <1 s. "Só Vocal" sem letra gera nada (correto). Sem áudio: 180 s a 120 BPM. | `auto_charter.auto_generate_chart` | — |
| Só Bateria (e bateria em qualquer modo) | ❌ | Gera lanes `orange` (bumbo) e `red` (caixa), que não existem em `DRUM_NOTES` (`kick`/`snare`): **bumbo e caixa somem no MIDI** (756→507 notas). Mesmo problema no editor (Mini-REAPER) e no `.chart`; e o bumbo/caixa importados de um `.mid` (lanes `kick`/`snare`) ficam invisíveis no editor. | `auto_charter`, `mini_reaper_canvas.LANE_NAMES_DRUMS`, `rbn_specs.DRUM_NOTES` | C |
| Gerar só faltantes | ⚠️ | Preserva trilhas existentes, mas gera na grade de BPM constante (166) ignorando o mapa de 154 tempos do Joe → fora do tempo. | `generate_missing_instruments_only` | M |
| Ranking 0-6 automático (botão da Aba 4) | ⚠️ | Conta notas de todas as dificuldades + marcadores: Joe dá 6 em tudo. O ranking definido pelo próprio auto-charter é razoável. Fórmula DTA `val*60+50` não segue os tiers Harmonix. | `_on_auto_calc_rankings_clicked`, `rank_to_dta` | M |
| Modelo: adicionar/remover nota | ⚠️ | Inserção ordenada ✅. `remove_note_near` e o clique-toggle do editor ignoram a dificuldade (remove a nota Expert ao editar Easy). | `ChartSong.remove_note_near`, `MiniReaperCanvas._on_canvas_click` | M |
| Salvar/abrir projeto | ❌ | A UI **não tem** salvar/abrir projeto. `to_dict/from_dict` existem mas perdem `vocal_notes`, `lyrics_raw`, `diff_vocals`, `audio_stems`, `duration_ms`, `audio_offset_ms`. | `ChartSong.to_dict` | A |

## 5. Exportação (a: auto-chart; b: Joe importado) + validador + reimportação

| Destino | Status | Validador (a / b) | Reimportação | Código | Sev |
|---|---|---|---|---|---|
| Clone Hero | ⚠️ | 0 erros / 0 erros | (a) idêntica exceto bateria (bumbo/caixa perdidos); (b) contagens idênticas, tempo ≤1 ms. Perdas da seção 1 (OD, frases, tom markers…) e `song.ini` regravado (preview 30000, `icon = midguitar`, sem `pro_drums`). | `clonehero_exporter.export_clone_hero_song` | A |
| RB3 (pasta `songs/`) | ❌ | `PS3_MISSING_EDAT`, `PS3_PLAIN_MID` (+`DTA_MOGG_CHANNELS` em b) | contagens OK a partir de `songs/<x>/` | `rb3_dta_exporter.export_rb3_song_package` | C |
| PS3 / RPCS3 | ❌ | idem | idem | `ps3_pkg_exporter.export_ps3_pkg_structure` | C |
| RB2 | ❌ | idem + `PROFILE_UNVERIFIED` | perde Keys/Pro (esperado no RB2) | `rb2_exporter.export_rb2_song_package` | C |
| Xbox 360 | ❌ | `XBOX_NO_CON_PACKAGE` | contagens OK | `xbox360_exporter.export_xbox360_structure` | C |
| PS4 | ❌ | `PS4_NO_SONGDTA` | contagens OK | `ps4_exporter.export_ps4_structure` | C |
| Aviso do validador na UI | ✅ | Os 6 botões rodam e mostram "Sucesso" + lista de erros como aviso. | `_show_export_result` | — |

Problemas comuns RB3/PS3/RB2/Xbox/PS4: `.mid` solto (sem `.mid.edat`), sem `gen/*.milo_ps3` e `*_keep.png_ps3`,
nenhum `.pkg`/CON é gerado (só `package.conf` / `project.gp4`), `.mogg` com Opus quando a origem é `.opus`.
PS3: layout `USRDIR/songs/` (os pacotes reais usam `USRDIR/<pasta>/songs/`) e o `.bat` copia para
`BLUS30463/USRDIR/songs`, então cada música instalada **sobrescreve o `songs.dta` da anterior**.
DTA RB3: `(drum_solo (seq 96 …))` (real: `(seqs (kick.cue …))`), `tracks` lista instrumentos sem notas,
sem `song_length`/`vocal_gender`/`tracks_count`/`encoding` (acentos), aspas do título não escapadas.
RB2: `decade the10s` e `vocal_gender male` fixos. Xbox: arquivos duplicados em `songs/` e `Content/`.

## 6. Pacotes

| Funcionalidade | Status | Evidência | Código | Sev |
|---|---|---|---|---|
| Escanear pasta | ✅ | Achou 3 músicas (CH .mid, CH auto, .chart). | `pack_compiler.scan_folder_for_songs` | — |
| Pacote PS3 (4 músicas) | ⚠️ | `songs.dta` unificado com 4 entradas, nomes curtos sem colisão. Herda todos os erros PS3; música sem áudio sai sem `.mogg` sem aviso (`LAYOUT_MISSING_MOGG`). `song_id` = `1010000000 + idx*100 + hash%90` → colide entre pacotes diferentes. | `compile_ps3_song_pack` | A |
| Pacote Clone Hero | ✅ | Uma pasta por música, validador sem erros. Duas músicas com mesmo artista/título se sobrescrevem. | `compile_clone_hero_pack` | B |

## 7. Palco ao vivo / MIDI

| Funcionalidade | Status | Evidência | Código | Sev |
|---|---|---|---|---|
| Listar portas / gamepads | ✅ | Entradas: nenhuma nesta máquina; saída: GS Wavetable. `find_rockband_midi_input` cai em "qualquer porta" se não achar Rock Band. | `midi/detector.py` | B |
| Presets (4) | ✅ | Carregam; modos `strum_required`/`instant_or_strum`/`passthrough`. | `config_manager.load_preset` | — |
| Mapper (casas + palhetada + oitava) | ✅ | Verde+palhetada → [52,59,64]; laranja → [48,55,60]; oitava +1 soma 12. | `midi/mapper.GuitarMapper` | — |
| Leitor: bateria canal 10 | ✅ | Kick 36 → evento de bateria + som no canal 9. | `MIDIReader._midi_callback` | — |
| Leitor: Pro Guitar canais 1-6 | ✅ | Ch1 nota 67 → corda 1 casa 3. | idem | — |
| Leitor: modo AUTO teclado | ❌ | Teclado no canal 1 (README: "C3..C5 no canal 1 → Teclado") vira Pro Guitar com casa negativa (-4, -16). Em outros canais, notas 48-55/60-67 viram casas da guitarra 5 botões. | idem | M |
| Leitor: palhetada MIDI em AUTO | ❌ | Notas 69/71/72 só são vistas se estiverem em `DEFAULT_RB_MIDI_NOTES` (não estão) → vira tecla. Guitarra 5 botões via MIDI fica muda em AUTO (`strum_required`). | idem | M |
| Motor de áudio | ✅ / 🖐 | Inicia (synth nativo ID 0), carrega samples wav/opus, fecha limpo. Som real: manual. | `audio/engine.AudioEngine` | — |
| Gamepad, visualizadores, whammy, ribbon | 🖐 | Precisa de hardware. | `reader.start_gamepad_listener`, `ui/*_view.py` | — |

## 8. Interface e build

| Funcionalidade | Status | Evidência | Código | Sev |
|---|---|---|---|---|
| Janela principal | ✅ | `MidGuitarApp()` constrói e fecha. | `ui/app.py` | — |
| Estúdio (5 abas) | ✅ | Constrói; importar pasta, ranking, sincronizar campos, 6 exportações, "Gerar tudo" com áudio, play/stop, diálogo de letras, redraw — sem exceção. | `ui/creator_studio_dialog.py` | — |
| Arrastar e soltar | ✅ / 🖐 | `tkinterdnd2` registra o alvo no Toplevel; o drop real é manual. | `_setup_drag_and_drop` | — |
| Botão "Tutorial Visual" | ⚠️ | Abre `TUTORIAL_VISUAL.md` relativo ao diretório atual; o arquivo não vai no build → não faz nada no `.exe`. | `_build_guide_tab` | B |
| Texto da UI "Clone Hero / YARG / GHWT" | ❌ | Promete pasta "DATA/MODS do GHWT Definitive Edition"; o GHWT:DE não lê `song.ini`+`notes.mid`. | `_update_target_game_desc` | M |
| `build_exe.py` (só revisado) | ⚠️ | Sem `--paths=.` (depende do diretório atual para achar `src`), `TUTORIAL_VISUAL.md` fora do `--add-data`, `config.json` gravado ao lado do `.exe` (falha em `Program Files`). Coleta customtkinter/rtmidi/pygame/PIL/soundfile/tkinterdnd2 ✅. | `build_exe.py`, `config_manager.get_user_dir` | B |

## Contagem

| Status | Itens |
|---|---|
| ✅ funciona | 16 (+2 ✅ com parte manual) |
| ⚠️ parcial | 16 |
| ❌ quebrado / inexistente | 16 |
| 🖐 manual | 1 (+ as 2 partes manuais acima) |
| **Total de linhas avaliadas** | **51** |

## Problemas priorizados por passo do programa

### (2) Ciclo Clone Hero
1. **C** Bateria: lanes `orange`/`red` (auto-charter, editor, `.chart`) vs `kick`/`snare` (`DRUM_NOTES`, importador `.mid`) → bumbo e caixa somem no MIDI; bumbo/caixa importados ficam invisíveis no editor. Unificar o nome das lanes.
2. **A** Importador `.mid` descarta overdrive, solo, frases vocais (105), marcadores de tom, fills, HARM1-3 e canais Pro Guitar → qualquer custom importado e reexportado perde Star Power, frases e pro drums. Preservar (ou repassar intactas) as trilhas/marcadores não editados.
3. **A** Áudio CH: `.opus` copiado como `song.ogg` + stems copiados → guitarra dobrada. Não gerar `song.ogg` quando há stems; manter extensão real.
4. **A** Não há salvar/abrir projeto; `to_dict` perde vocais, letra, stems, duração.
5. **M** `song.ini`: importar/preservar `preview_start_time`, `delay`, `pro_drums`, `diff_*_real`, `diff_vocals`, `song_length`.
6. **M** `.chart`: artista, `[Events]`, star power, forçadas/open.
7. **M** Ranking 0-6 da UI conta todas as dificuldades (sempre 6).
8. **M** BPM com resolução de 50 ms; "gerar faltantes" ignora o mapa de tempos.

### (3) Exportação PS3 no formato real
1. **C** `.mid` em vez de `.mid.edat`; sem `milo_ps3`/`png_ps3`; nenhum `.pkg` gerado.
2. **C** `.mogg` com Opus quando a origem é `.opus` (converter para Vorbis de verdade).
3. **C** Layout `USRDIR/songs/` + `.bat` copiando para `BLUS30463/USRDIR/songs` → cada instalação sobrescreve o `songs.dta` anterior. Usar `USRDIR/<pasta única>/songs/`.
4. **A** Multitrack: DTA com 8 canais fixos x `.mogg` de 2 canais; stems soltos copiados. Montar o `.mogg` multicanal a partir dos stems e gerar `tracks`/`pans`/`vols` coerentes.
5. **M** DTA: `drum_solo` no formato errado, `tracks` com instrumentos vazios, sem `song_length`/`vocal_gender`/`encoding`, aspas não escapadas, fórmula de rank fora dos tiers, `song_id` colidindo entre pacotes.

### (3b) Importação PS3 (pkg / edat / mogg)
1. **A** Ler `.mid.edat` (NPD) e `.mogg` criptografado (v11/v13); hoje 0 notas e áudio inexistente sem aviso.
2. **A** `audio_path` apontando para `*_extracted.ogg` inexistente (usar o retorno de `extract_ogg_from_mogg` e avisar).
3. **A** Parser de `songs.dta` real (chaves com aspas, multi-linha) — já existe `validation.parse_dta`, reutilizar.
4. **A** Importar `.pkg` direto e aceitar a raiz do pacote / `songs/` (procurar `songs/*/`).
5. **M** Não gravar `*_extracted.ogg` ao lado da origem (usar pasta temporária/cache).

### (4) Xbox CON / RB2 / PS4 / GHWT:DE
1. **C** Xbox 360: gerar e ler pacote CON/STFS (export hoje é pasta solta; import inexistente).
2. **C** RB2: mesmos problemas do PS3 + `decade`/`vocal_gender` fixos; perfil não verificado.
3. **C** PS4: gerar `.songdta_ps4`, `.rbmid_ps4`, `.moggsong`.
4. **M** GHWT:DE: import inexistente; texto da UI promete compatibilidade que não existe.

### (5) Checklists manuais
- Conectar Mustang/Squier, teclado RB3, bateria e MIDI Pro Adapter: modo AUTO, visualizadores, som, whammy/ribbon.
- Gamepad USB (guitarra 5 botões) e teclas do PC na barra de toque do estúdio.
- Playtest do Mini-REAPER com áudio (sincronia visual/sonora) e arrastar-e-soltar real de MP3/letra/pasta.
- Clone Hero/YARG: abrir o export do Joe e de uma música auto-gerada (sem guitarra dobrada, Star Power, pro drums).
- RPCS3 (RB3/RB2), Xbox (Xenia/console) e PS4 (GoldHEN): só depois das fases 3-4; usar o validador antes.
- `.exe` gerado por `build_exe.py`: abrir de uma pasta qualquer, salvar config, botão do tutorial.

### Outros bugs
- **M** MIDI AUTO: canal 1 sempre vira Pro Guitar (teclado RB3 vira casa negativa); notas 48-55/60-67 viram guitarra 5 botões; palhetada 69/71/72 inalcançável.
- **M** `remove_note_near` e o clique do editor ignoram a dificuldade.
- **B** `generate_rbn_midi` altera a música (recalcula dificuldades) como efeito colateral.
- **B** Pro Guitar: exportador limita casa a 17 (importador aceita 22; Squier tem 22).
- **B** Botão do tutorial e `build_exe.py` (caminho relativo, `--paths`, config ao lado do `.exe`).
- **B** Pacote CH: músicas com mesmo artista/título se sobrescrevem; `detect_target` devolve `rb3_ps3` para exports Xbox/PS4 (pasta `songs/`).
- **B** Divisão silábica erra em inglês.

## Situação após o programa (2026-11)

O diagnóstico acima fica como histórico. Esta tabela mostra cada funcionalidade depois dos
passos 2 a 5, com o commit que corrigiu e o teste que garante. Todos os `xfail` de
`tests/acceptance/test_diagnostico.py` foram removidos (viraram testes normais que passam).
O que depende de jogo, console ou instrumento físico está marcado 🖐 e tem roteiro em
[`docs/TESTE_NO_JOGO.md`](../../TESTE_NO_JOGO.md).

Legenda igual à de cima: ✅ funciona · ⚠️ parcial · ❌ não suportado · 🖐 falta conferir à mão.

### Importação

| Funcionalidade | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| Pasta Clone Hero (`notes.mid`) | ⚠️ | ✅ sem perdas; overdrive (116), solo (103) e frases vocais (105/106) viram dados editáveis, o resto (tom markers, fills, HARM, canais Pro) segue no passthrough | fbdcac4, 2d24e08 (notas abertas), 1f5954c | `test_ch_fidelity.py`, `test_ch_roundtrip_keeps_*`, `test_editable_markers.py` |
| `song.ini` | ⚠️ | ✅ prévia, rankings Pro e chaves desconhecidas preservadas | 79f0aa9 | `test_song_ini.py`, `test_ch_import_reads_preview_and_pro_ranks` |
| Pasta com `notes.chart` | ⚠️ | ✅ artista, `[Events]`, star power, forçadas/open, bateria kick/snare | 370d396 | `test_chart_import.py`, `test_chart_import_reads_*` |
| Pasta RB3 solta / raiz do pacote | ⚠️ | ✅ procura `songs/*/` e lê o `songs.dta` real | c5fe817 | `test_ps3_import_export.py` |
| Pasta PS3 extraída (`.mid.edat` + `.mogg` criptografado) | ❌ | ✅ | c5fe817, deda3b9, 61747a8, 2637c9d | `test_ps3_extracted_folder_imports_notes`, `test_ps3_import_audio_path_exists` |
| Pacote CON do Xbox 360 | ❌ | ✅ (botão **Abrir pacote** e arrastar) | 26d4f35, 93c7a28, e6675b0 | `test_xbox_con_import`, `test_xbox_import_export.py` |
| `.pkg` do PS3 direto | ❌ | ✅ | 1d73f9a, c5fe817 | `test_ps3_pkg_file_import`, `test_ps3_pkg.py` |
| Mod GHWT:DE | ❌ | ❌ não suportado, mas recusado com mensagem clara | 385fd18 | `test_ghwtde_import_is_refused_with_clear_message` |
| `.mid` solto | ⚠️ | ⚠️ funciona numa pasta; soltar um `.mid` sozinho na janela ainda é ignorado | — | — |
| `.mogg` solto | ⚠️ | ✅ criptografado é decifrado; extração vai para cache temporário | 61747a8, 2637c9d, 6f7411a | `test_encrypted_mogg_is_decrypted_not_garbage`, `test_mogg_crypt.py` |
| Abrir pacote sem travar a janela (~25 s na 1ª vez) | — | ✅ thread + janela de progresso | c1e2b86 | `test_background_tasks.py` |
| `.pkg` / `.mogg` truncado ou corrompido | ⚠️ | ✅ `PkgError` / `MoggCryptError` com mensagem clara, sem arquivo pela metade na extração | 80b9f4e | `test_io_robustness.py` |
| Cache `%TEMP%\midguitar_cache` | ⚠️ crescia sem limite | ✅ limpo ao abrir o app e ao importar (mantém os mais novos até ~2 GB) | 64f315e | `test_cache_and_close.py` |
| Abrir projeto cujo áudio sumiu (cache limpo/arquivo movido) | ❌ abria mudo, sem aviso | ✅ avisa quais áudios faltam e oferece escolher o áudio de novo | 64f315e | `test_open_project_with_missing_audio_warns`, `test_open_project_relink_audio` |

### Áudio

| Funcionalidade | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| `analyze_audio_file` (BPM) | ⚠️ | ✅ envelope de 10 ms + interpolação parabólica | e8359c7 | `test_bpm_detection_click_128` |
| `convert_audio_to_ogg` wav/mp3 | ✅ | ✅ | — | `test_audio_ch_cycle.py` |
| `convert_audio_to_ogg` opus | ❌ | ✅ vira Vorbis de verdade | e8359c7 | `test_opus_becomes_vorbis_inside_mogg` |
| `create_unencrypted_mogg` | ⚠️ | ✅ Vorbis, 44100 Hz, multicanal | e8359c7, 98ef303, c75a7d7 | `test_unencrypted_mogg_roundtrip`, `test_audio_resample.py` |
| `extract_ogg_from_mogg` | ✅ | ✅ | — | — |
| Stems multitrack | ❌ | ✅ `.mogg` multicanal coerente com o DTA; CH sem guitarra dobrada | c75a7d7, ddea0c8, 6f7411a | `test_rb3_multistem_mogg_channels_match_dta`, `test_audio_ch_cycle.py` |

### Letras e vocais

| Funcionalidade | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| `.txt` / `.lrc` / `.srt` | ✅ | ✅ | — | `test_lyrics_txt_lrc_srt` |
| Divisão silábica | ⚠️ | ⚠️ inglês ainda erra (`lo-ve`) | — | — |
| Geração de vocal | ✅ | ✅ segue o mapa de tempo (mudanças de BPM) | 0d3846f | `test_generated_lyrics_fall_on_map_beats` |
| Sem letra = sem microfone | ✅ | ✅ | — | `test_no_lyrics_means_no_vocals` |

### Auto-chart e edição

| Funcionalidade | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| Modos do auto-chart | ✅ | ✅ | — | `test_auto_chart_all_modes_generate_four_difficulties` |
| Só Bateria (bumbo/caixa) | ❌ | ✅ lanes `kick`/`snare` em todo lugar | 370d396 | `test_drum_kick_snare_*`, `test_chart_drums_export_kick_and_snare` |
| Gerar só faltantes | ⚠️ | ✅ notas nas batidas reais do mapa de tempo (auto-chart idem) | 0d3846f | `test_generated_missing_instrument_falls_on_map_beats` |
| Grade e snap do editor | ⚠️ BPM constante | ✅ compassos/batidas pelo mapa de tempo e fórmula de compasso | 0d3846f | `test_editor_snap_uses_tempo_map`, `test_editor_grid_lines_use_tempo_map` |
| Overdrive / solo / frases vocais de música importada | ❌ invisíveis no editor; edições sumiam | ✅ aparecem nas lanes; adicionar/apagar chega à exportação | 1f5954c | `test_editable_markers.py` |
| Lane "solo" do editor/auto-chart | ❌ nunca exportada | ✅ vira frase de solo (nota 103), importada de volta na mesma lane | 1f5954c | `test_new_song_solo_lane_exports_merged_103`, `test_solo_roundtrip_through_import` |
| Ranking 0-6 automático | ⚠️ | ✅ por densidade de notas Expert | bbecb75 | `test_audio_ch_cycle.py` |
| Adicionar/remover nota | ⚠️ | ✅ editor e `remove_note_near` respeitam a dificuldade | b07987e | `test_editor_difficulty.py` |
| Salvar/abrir projeto | ❌ | ✅ `.mgproj` com vocais, letra, stems, duração | 52dced6 | `test_project_file.py`, `test_project_roundtrip_*` |

### Exportação

| Destino | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| Clone Hero / YARG | ⚠️ | ✅ validador sem erros, sem perdas · 🖐 no jogo | fbdcac4, 6f7411a, 79f0aa9 | `test_ch_export_roundtrip_keeps_counts_and_validates`, `test_clonehero_export_from_scratch_validates` |
| RB3 (pasta `songs/`) | ❌ | ✅ `.mid.edat`, MIDI só com trilhas RB · 🖐 no jogo | 4e824ce, a68ed0c | `test_rb_export_ps3.py` |
| PS3 / RPCS3 (`.pkg`) | ❌ | ✅ layout `USRDIR/<pasta>/songs`, `.mid.edat`, `png_ps3`, `.pkg` instalável · 🖐 no RPCS3/PS3 | ddea0c8, deda3b9, 1d73f9a, 49a8f9f, dc0d7a1 | `test_ps3_export_passes_validator`, `test_ps3_import_export.py` |
| RB2 | ❌ | ⚠️ gerador de DTA compartilhado, `.mid.edat`; perfil RB2 não verificado · 🖐 | d7471df, 4e824ce | `test_rb2_dta.py` |
| Xbox 360 | ❌ | ⚠️ pacote CON assinado e conferido por dentro; não verificado em console/Xenia · 🖐 | 26d4f35, 33dd69d, 0e0a3c3 | `test_xbox360_export_passes_validator`, `test_xbox_stfs.py` |
| PS4 | ❌ | ❌ experimental, avisa que não toca no RB4 | 385fd18 | `test_ps4_export_is_honest_about_being_unverified` |
| Aviso do validador na UI | ✅ | ✅ | — | `test_export_dialog.py` |
| Exportar sem travar a janela (~1,5 min no PS3/Xbox) | ❌ (novo) | ✅ thread + janela "Exportando…", botões desligados, erro sempre mostrado; fechar o app ou o estúdio no meio pergunta antes | c1e2b86, 64f315e | `test_background_tasks.py`, `test_cache_and_close.py` |
| Gravação de CON / `.pkg` / `.mogg` | ⚠️ erro deixava arquivo corrompido | ✅ grava em `.tmp` e troca no fim; leitura curta vira erro | 80b9f4e, 64f315e | `test_io_robustness.py` |
| Instaladores `.bat` (RB3, RB2, pacote) | ❌ título com `&`/`%` quebrava o script (injeção de comandos) | ✅ texto do usuário higienizado; pasta e title id validados | cbdd691 | `test_bat_safety.py` |
| DTA RB3 (`drum_solo`, `tracks`, `song_length`, `encoding`, aspas, rank, `song_id`) | ❌ | ✅ formato Magma C3, `song_id` estável | ddea0c8 | `test_rb3_dta_drum_solo_format`, `test_rb_export_ps3.py` |

### Pacotes

| Funcionalidade | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| Escanear pasta | ✅ | ✅ | — | — |
| Pacote PS3 | ⚠️ | ✅ layout real, `song_id` estável sem colisão · 🖐 no jogo | ddea0c8 | `test_pack_compilers_two_songs` |
| Pacote Clone Hero | ✅ | ⚠️ duas músicas com mesmo artista/título ainda se sobrescrevem | — | `test_pack_compilers_two_songs` |
| Compilar sem travar a janela | — | ✅ | c1e2b86 | `test_background_tasks.py` |

### Palco ao vivo / MIDI

| Funcionalidade | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| Listar portas / gamepads | ✅ | ✅ | — | — |
| Presets | ✅ | ✅ | — | — |
| Mapper | ✅ | ✅ | — | — |
| Bateria canal 10 | ✅ | ✅ · 🖐 | — | `test_midi_drums_channel_10` |
| Pro Guitar canais 1-6 | ✅ | ✅ casas 0 a 22 · 🖐 | 3413ab9 | `test_midi_auto_mode.py` |
| AUTO: teclado no canal 1 | ❌ | ✅ nota sem casa válida vira teclado e o app lembra do último instrumento · 🖐 | 3413ab9 | `test_midi_auto_keyboard_on_channel_1`, `test_midi_auto_mode.py` |
| AUTO: palhetada 69/71/72 | ❌ | ✅ · 🖐 | 3413ab9 | `test_midi_auto_strum_note`, `test_midi_auto_mode.py` |
| Motor de áudio | ✅ / 🖐 | ✅ / 🖐 | — | — |
| Gamepad, visualizadores, whammy, ribbon | 🖐 | 🖐 | — | roteiro em `TESTE_NO_JOGO.md` §5 |

### Interface e build

| Funcionalidade | Antes | Agora | Commit(s) | Teste(s) |
|---|---|---|---|---|
| Janela principal | ✅ | ✅ | — | — |
| Estúdio (5 abas) | ✅ | ✅ · 🖐 passeio | — | roteiro em `TESTE_NO_JOGO.md` §6 |
| Arrastar e soltar | ✅ / 🖐 | ✅ (inclui `.pkg` e CON) / 🖐 | e6675b0 | `test_drop_con_without_extension_imports` |
| Botão "Tutorial Visual" | ⚠️ | ✅ acha o tutorial no `.exe` e avisa se faltar | 528d018 | `test_selftest_passes_from_source` |
| Texto da UI "GHWT" | ❌ | ✅ não promete mais GHWT:DE | 385fd18 | — |
| README / tutorial | ⚠️ prometiam "substitui 100%" e RB2/Xbox prontos | ✅ status por destino (formato verificado x testado no jogo) com link para `TESTE_NO_JOGO.md` | b475a11 | — |
| `build_exe.py` | ⚠️ | ✅ `--paths=.`, tutorial e imagens no build, pycryptodome/soundfile/tkinterdnd2/mido, `--selftest`, config em `%APPDATA%\MidGuitar` com migração · 🖐 abrir o `.exe` | 528d018 | `test_config_paths.py`, `test_selftest_passes_from_source` |

### Ainda abertos (conhecidos)

- **B** Pro Guitar: o exportador ainda limita a casa a 17 (a Squier tem 22).
- **B** `generate_rbn_midi` recalcula dificuldades como efeito colateral.
- **B** Pacote Clone Hero: músicas com mesmo artista/título se sobrescrevem.
- **B** Divisão silábica erra em inglês; soltar um `.mid` sozinho na janela é ignorado.
- **B** Overdrive do Pro Guitar/Pro Keys e frases vocais não representáveis (vazias, encostadas,
  canal ≠ 0) continuam só no passthrough; o overdrive vocal de customs reais (nota 116 na
  `PART VOCALS`) também, enquanto o gerador usa 106 para o overdrive vocal novo.
- **B** O auto-chart gera compassos de 4 tempos; em trechos 3/4 as notas caem nas batidas do mapa,
  mas o padrão rítmico não acompanha o compasso.
- **🖐** Nada foi tocado ainda num jogo de verdade (RPCS3, PS3, Xbox/Xenia, Clone Hero/YARG) nem com
  instrumentos físicos: seguir `docs/TESTE_NO_JOGO.md`. Xbox 360 e RB2 continuam "não verificados";
  PS4 continua experimental.
