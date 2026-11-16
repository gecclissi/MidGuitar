# Créditos e licença

O MidGuitar é distribuído sob a **GNU General Public License v3** (arquivo `LICENSE`).

## Onyx Music Game Toolkit (GPL v3)

Os módulos abaixo foram portados ou se baseiam no código e nos formatos documentados do
[Onyx](https://github.com/mtolly/onyx), de Michael Tolly e colaboradores, também sob GPL v3.
Cada porte foi conferido contra pacotes reais de Rock Band (PS3 e Xbox 360).

| Módulo | Origem no Onyx |
|---|---|
| `src/creator/mogg_crypt.py` | `onyx-moggcrypt` (VorbisReader, ByteGrinder, keygen, chaves da Harmonix) |
| `src/creator/xbox_stfs.py` | `Onyx/Xbox/STFS.hs` e certificado de console (KV) usado para assinar CON |
| `src/creator/png_xbox.py` | `Onyx/Image/DXT.hs` (formato `png_xbox`) |
| `src/creator/edat.py` | estrutura NPD/EDAT (make_npdata / RPCS3) e fórmula da klicensee dos customs do RB |
| `src/creator/ps3_pkg.py` | formato de .pkg de debug do PS3 (make_package_npdrm) |
| `src/creator/png_ps3.py` | formato `png_ps3` (HMX bitmap), conferido com pacotes reais |

## Outros projetos

- **RPCS3** (EDAT.cpp): estrutura do formato NPD/EDAT.
- **Harmonix / Rock Band Network, C3 / Magma C3 Roks Edition**: especificações e convenções de MIDI, `songs.dta` e pacotes.
- Bibliotecas: CustomTkinter, mido, python-rtmidi, pygame, Pillow, NumPy, SoundFile, PyCryptodome,
  tkinterdnd2 e PyInstaller, cada uma sob a sua própria licença (todas compatíveis com a GPL v3).

Os nomes Rock Band, Guitar Hero, Clone Hero, PlayStation e Xbox pertencem aos seus donos; este projeto
não é afiliado a eles. Use apenas conteúdo que você tem direito de usar.
