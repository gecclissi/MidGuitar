# Fase 1: pendências de compatibilidade por destino

Saída real de `validate_export` para uma música de exemplo (`Exemplo` / `MidGuitar`, 120 BPM, 40 s,
instrumentos: guitar, bass, drum, keys, pro_guitar, pro_bass, pro_keys, áudio OGG estéreo de 3 s),
exportada por cada exportador. Entrada das Fases 2 a 5.

## Verificação da fase

| Item | Resultado |
|---|---|
| `pytest -v` sem `MIDGUITAR_REFS` | 88 passed, 2 skipped (os 2 testes `refs`) |
| (a) `test_generated_song_passes_rb3_profile`, `test_clonehero_export_has_no_errors` | passam |
| (b) `test_reference_passes_validator` | pendente: aguarda pasta de referência |
| (c) `test_reference_roundtrip_keeps_note_times` | pendente: aguarda pasta de referência |
| Step 2 (rodar com `MIDGUITAR_REFS`) | adiado: a pasta ainda não existe |

## Resultado por destino

### Clone Hero (`export_clone_hero_song`, alvo `clonehero`)

Nenhum problema reportado.

### RB3 PS3 (`export_rb3_song_package` e `export_ps3_pkg_structure`, alvo `rb3_ps3`)

Os dois exportadores produzem o mesmo conjunto de problemas.

| Código | Nível | Mensagem |
|---|---|---|
| PS3_MISSING_EDAT | error | Faltando midguitarexemplo.mid.edat |
| PS3_PLAIN_MID | error | Só há midguitarexemplo.mid solto: o PS3 exige .mid.edat |
| PS3_MISSING_MILO | warning | Faltando gen/midguitarexemplo.milo_ps3 |
| PS3_MISSING_ART | warning | Faltando gen/midguitarexemplo_keep.png_ps3 |

### RB2 (`export_rb2_song_package`, alvo `rb2`)

| Código | Nível | Mensagem |
|---|---|---|
| PS3_MISSING_EDAT | error | Faltando midguitarexemplo.mid.edat |
| PS3_PLAIN_MID | error | Só há midguitarexemplo.mid solto: o PS3 exige .mid.edat |
| PS3_MISSING_MILO | warning | Faltando gen/midguitarexemplo.milo_ps3 |
| PS3_MISSING_ART | warning | Faltando gen/midguitarexemplo_keep.png_ps3 |
| PROFILE_UNVERIFIED | warning | Perfil Rock Band 2 ainda não foi confirmado em jogo real |

### Xbox 360 (`export_xbox360_structure`, alvo `xbox360`)

| Código | Nível | Mensagem |
|---|---|---|
| XBOX_NO_CON_PACKAGE | error | o Xbox 360 exige um pacote CON/LIVE; pastas soltas só funcionam em Xenia/Aurora com plugins |
| PROFILE_UNVERIFIED | warning | Perfil Rock Band 3 (Xbox 360) ainda não foi confirmado em jogo real |

### PS4 (`export_ps4_structure`, alvo `ps4`)

| Código | Nível | Mensagem |
|---|---|---|
| PS4_NO_SONGDTA | error | Nenhum arquivo *.songdta_ps4 encontrado |

## O que a próxima fase precisa fazer

| Fase | Destino | Trabalho |
|---|---|---|
| 2 | Clone Hero | Sem erros hoje; validar em jogo real e ampliar cobertura (extras, `song.ini`, áudio). |
| 3 | RB3 PS3 | Gerar `.mid.edat` (criptografia EDAT) no lugar do `.mid` solto; gerar `gen/*.milo_ps3` e `gen/*_keep.png_ps3`. |
| 4 | RB2 + Xbox 360 | Empacotar CON/STFS (Xbox) e aplicar o mesmo `.mid.edat`/milo/png_ps3 ao RB2; confirmar o perfil RB2 e o perfil Xbox em jogo real. |
| 5 | PS4 | Gerar `.songdta_ps4`, `.rbmid_ps4` e `.moggsong`. |

## Verificação manual pendente

- O diálogo de exportação da interface não foi aberto em uma tela real.
- A calibração contra os customs de referência (Task 8, step 4) está pendente: a pasta `MIDGUITAR_REFS` ainda não existe, então os testes `refs` ficam `skipped`.
