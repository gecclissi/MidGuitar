# Teste no jogo e no aparelho: checklists do MidGuitar

Este guia é para conferir, com as próprias mãos, o que os testes automáticos não conseguem
ver: se a música toca no jogo, se o áudio está no tempo e se os instrumentos de verdade
acendem a tela e fazem som.

Como usar:

- Faça uma seção por vez. Marque `[x]` em cada item que deu certo.
- Quando um item falhar, pare naquele item e me mande o que está escrito em
  **"Se falhar, me mande"**. Uma foto da tela (tecla `PrtScn` ou `Win + Shift + S`) ajuda muito.
- Use sempre as músicas de exemplo da pasta `music\`:
  - **Joe Dassin - Salut les amoureux**: pasta do Clone Hero (`music\_refs\Joe Dassin - Salut les amoureux`)
    e pacote do Xbox 360 (`music\Joe Dassin - Salut les amoureux_rb3con`).
  - **Gorillaz - Andromeda**: pacote de PS3 (`music\Gorillaz - Andromeda.pkg`).
  - **5 Seconds Of Summer - Ghost Of You**: pacote de PS3 (`music\5 Seconds Of Summer - Ghost Of YouXB.pkg`).
  - **PAVLO - Mediterranean Eyes** (`music\PAVLO - Mediterranean Eyes.zip`): é um mod do GHWT:DE.
    O MidGuitar ainda **não** importa esse formato; ele deve mostrar uma mensagem dizendo isso.
- Antes de levar qualquer música para o jogo, exporte-a com o MidGuitar e leia a janela de
  **verificação de compatibilidade** que aparece no fim da exportação. Se ela listar **erros**
  (não só avisos), me mande o texto dela antes de testar no jogo.

Onde ficam os registros (logs) que eu posso pedir:

| Programa | Arquivo de log |
|---|---|
| MidGuitar (.exe) | `%TEMP%\midguitar_selftest.txt` (só do autoteste) e a janela "Monitor" da tela principal |
| RPCS3 | `RPCS3.log` na pasta onde o RPCS3 está instalado (ex.: `C:\RPCS3\RPCS3.log`) |
| Xenia | `xenia.log` na pasta do Xenia |
| Clone Hero | `%USERPROFILE%\Documents\Clone Hero\player.log` (ou `badsongs.txt` na mesma pasta) |
| YARG | menu Configurações > "Abrir pasta de dados" > `Player.log` |

> Dica para colar o caminho: aperte `Win + R`, cole o caminho (ex.: `%TEMP%`) e dê Enter.

---

## 1. Rock Band 3 no RPCS3 (PC)

Pressuposto: você já tem o **Rock Band 3 (BLUS30463)** instalado e funcionando no RPCS3, com a
atualização do jogo (versão 1.05) e, de preferência, o patch "RB3 Deluxe".

Se ainda não tem o RPCS3: baixe em <https://rpcs3.net/download>, descompacte numa pasta simples
(ex.: `C:\RPCS3`), abra o `rpcs3.exe` e instale o firmware do PS3 pelo menu
**File > Install Firmware** (o arquivo `PS3UPDAT.PUP` vem do site oficial da PlayStation).

### 1.1 Exportar a música

- [ ] Abra o MidGuitar, clique em **🎵 Criar & Converter (RB3 / CH)**.
- [ ] Na aba **⚡ Criação & Conversão 1 Clique**, clique em **📦 Abrir pacote** e escolha
      `music\Gorillaz - Andromeda.pkg`. Aparece a janelinha "Abrindo a música…" (pode levar até
      30 s na primeira vez) e depois os dados da música.
- [ ] No menu de jogo escolha **🎸 Rock Band 3 (PS3 HEN/CFW & Emulador RPCS3)** e clique em
      **⚡ EXPORTAR AGORA**. Escolha uma pasta vazia (ex.: `Documentos\Exportados`).
- [ ] Aparece a janelinha **"Exportando…"** com a barra andando (1 a 2 minutos) e a janela do
      MidGuitar **não** fica "Não está respondendo".
- [ ] No fim aparece "Sucesso PS3 / RPCS3!" com o nome do `.pkg` e a verificação de compatibilidade
      sem erros.
  - Se falhar, me mande: o texto inteiro da janela de resultado (foto) e a lista de arquivos da pasta exportada.

### 1.2 Instalar o .pkg

- [ ] No RPCS3: menu **File > Install Packages/Raps/Edats**, escolha o `.pkg` que o MidGuitar gerou.
- [ ] O RPCS3 mostra uma barra de instalação e termina sem erro.
- [ ] Confira que a pasta da música apareceu em
      `C:\RPCS3\dev_hdd0\game\BLUS30463\USRDIR\<pasta da música>\` e que dentro dela existe
      `songs\songs.dta` e `songs\<nome>\<nome>.mid.edat` e `<nome>.mogg`.
  - Se falhar, me mande: o final do `RPCS3.log` (as últimas 100 linhas) e uma foto da pasta `USRDIR`.

### 1.3 Testar no jogo

- [ ] Abra o Rock Band 3. Em **Play a Show > Quickplay**, a música aparece na lista (procure
      pelo nome ou pelo artista).
- [ ] A capa do álbum aparece na lista/na tela de carregamento.
- [ ] A música começa, o **áudio toca** e as notas chegam **no tempo** da música
      (teste os primeiros 30 s e um trecho do meio).
- [ ] Teste **cada instrumento** que a música tem: Guitarra, Baixo, Bateria, Teclado, Vocal,
      e se houver, Pro Guitar, Pro Bass, Pro Keys e Pro Drums.
- [ ] Teste as **4 dificuldades** (Easy, Medium, Hard, Expert) em pelo menos um instrumento.
- [ ] **Vocal**: a letra aparece na tela e as frases fazem sentido; se a música tem harmonias,
      teste no modo **Harmonies** (3 microfones).
- [ ] **Star Power / Overdrive**: as frases brancas aparecem e acionar o Overdrive funciona.
- [ ] Quando um instrumento erra, só a trilha dele some (o áudio está separado por instrumento).
- [ ] Repita o teste com `music\5 Seconds Of Summer - Ghost Of YouXB.pkg` e com a pasta do
      Clone Hero do **Joe Dassin** (importada pela **Buscar Pasta...**) exportada para RB3.
  - Se falhar, me mande: o nome da música, o instrumento e a dificuldade, o minuto em que deu
    problema, uma foto da tela e as últimas 100 linhas do `RPCS3.log`.
  - Se a música **não aparece na lista**: me mande o `songs.dta` da pasta instalada.
  - Se o jogo **trava** ao carregar: me mande o `RPCS3.log` inteiro.

---

## 2. Rock Band 3 no PS3 de verdade (HEN ou CFW)

- [ ] Formate um pendrive em **FAT32** e copie o `.pkg` exportado para a raiz do pendrive
      (ou para uma pasta `PKG` na raiz, se o seu HEN/CFW procurar lá).
- [ ] Coloque o pendrive na porta USB mais à direita do PS3 e (no HEN) ative o HEN.
- [ ] No menu do PS3: **Package Manager > Install Package Files > Standard**
      (no HEN: **★ Install Package Files**), escolha o `.pkg` e confirme.
- [ ] A instalação termina sem erro.
- [ ] Abra o Rock Band 3 e repita os testes da seção **1.3**.
  - Se falhar, me mande: a mensagem de erro do PS3 (foto, com o código de erro, ex.: `8001003E`),
    qual HEN/CFW você usa e a versão.

---

## 3. Clone Hero e YARG (PC)

- [ ] No MidGuitar, abra a música (ex.: **Buscar Pasta...** com
      `music\_refs\Joe Dassin - Salut les amoureux`).
- [ ] Escolha **🎮 Clone Hero / YARG (PC)** e clique em **⚡ EXPORTAR AGORA**. Como pasta de
      destino escolha a pasta `Songs` do jogo (Clone Hero: `Documentos\Clone Hero\Songs`).
- [ ] A pasta exportada tem `notes.mid`, `song.ini`, `album.png` e os áudios
      (`guitar.ogg`, `bass.ogg`, `drums_1.ogg`... ou `song.ogg` se a música tem só uma faixa).
- [ ] No Clone Hero: **Settings > Scan Songs**. No YARG: **Settings > Songs > Scan Songs**.
- [ ] A música aparece na lista com título, artista, capa e as dificuldades certas.
- [ ] Toca com áudio no tempo; a guitarra **não** soa dobrada (duas vezes por cima).
- [ ] Star Power aparece; na bateria, os pratos e tons aparecem (Pro Drums).
- [ ] Vocal (no YARG) mostra a letra.
  - Se falhar, me mande: o `badsongs.txt` / `player.log` do Clone Hero (ou `Player.log` do YARG),
    o `song.ini` exportado e uma foto da tela.

---

## 4. Xbox 360 (RGH/JTAG) e Xenia — **não verificado**

> Ainda ninguém testou um pacote do MidGuitar num Xbox real ou no Xenia. O pacote CON é criado
> e conferido por dentro pelo MidGuitar, mas pode não abrir no jogo. Teste com calma.

- [ ] No MidGuitar, abra `music\Joe Dassin - Salut les amoureux_rb3con` com **📦 Abrir pacote**
      e exporte com **🟢 Xbox 360 - Rock Band 3**.
- [ ] A pasta exportada tem um arquivo terminado em `_rb3con` e o
      `COMO_INSTALAR_NO_XBOX360.txt`.
- [ ] **Console RGH/JTAG**: copie o arquivo `_rb3con` para
      `Hdd1:\Content\0000000000000000\45410914\00000001\` (com Horizon, FATXplorer ou FTP).
- [ ] **Xenia**: abra o Xenia, menu **File > Install Content** e escolha o arquivo `_rb3con`.
- [ ] Abra o Rock Band 3 e repita os testes da seção **1.3**.
  - Se falhar, me mande: a mensagem do jogo (foto), o `xenia.log` (no Xenia) e se você usou
    console ou Xenia.

---

## 5. Palco ao vivo (instrumentos MIDI de verdade)

Antes de começar: abra o MidGuitar, ligue o instrumento e clique em **🔄** ao lado de
**🔌 Entrada:** para atualizar a lista. Escolha a porta do instrumento e clique em **Conectar**.
Deixe o **📡 Monitor [ON]** ligado: cada nota recebida aparece lá com o canal e o número.

### 5.1 Guitarra Pro (Squier Stratocaster ou Mustang)

- [ ] Coloque a guitarra no modo MIDI (chave no corpo da Squier / botão na Mustang) e conecte
      o cabo MIDI (ou o MIDI Pro Adapter no modo Pro Guitar).
- [ ] Em **🎮 Instrumento:** escolha **🎸 Pro (6 Cordas)**.
- [ ] Toque cada corda solta: a corda certa acende no braço desenhado e ouve-se a nota.
- [ ] Aperte a casa 3 na corda Mi grave: aparece "Traste 3" no monitor, e a casa 3 acende.
- [ ] Na Squier, teste uma casa alta (casa 17 ou mais): não pode aparecer casa negativa.
- [ ] A alavanca (whammy) mexe no som / no medidor.
  - Se falhar, me mande: foto do Monitor com as linhas que apareceram ao tocar, e qual guitarra é.

### 5.2 Teclado do Rock Band 3

- [ ] Conecte o teclado pelo MIDI OUT (ou pelo MIDI Pro Adapter no modo teclado).
- [ ] Escolha **🎹 Teclado**. Toque do Dó mais grave ao mais agudo: cada tecla acende e soa.
- [ ] A fita (touch strip) mexe o medidor vertical.
  - Se falhar, me mande: foto do Monitor ao tocar 3 teclas diferentes.

### 5.3 Bateria (canal 10)

- [ ] Conecte a bateria (Rock Band / Guitar Hero / Band Hero) pelo MIDI.
- [ ] Escolha **🥁 Bateria**. Cada pad e o pedal acendem o desenho certo e tocam o som de bateria.
- [ ] Batidas fortes e fracas mudam o medidor de força.
  - Se falhar, me mande: foto do Monitor ao bater em cada pad (ele mostra a nota de cada um).

### 5.4 Guitarra de 5 botões pelo MIDI Pro Adapter

- [ ] Coloque o MIDI Pro Adapter no modo guitarra e escolha **🎸 5 Botões**.
- [ ] Segurar o botão verde e palhetar toca um acorde; cada cor toca um acorde diferente.
- [ ] A palheta para cima e para baixo aparece no desenho.
  - Se falhar, me mande: foto do Monitor ao apertar o verde e palhetar.

### 5.5 Teclado do PC e controle (gamepad) USB

- [ ] Ligue uma guitarra USB / controle no PC e veja se ele aparece na lista de entrada.
- [ ] Os botões A, B, Y, X, LB acendem verde, vermelho, amarelo, azul, laranja; o direcional
      para cima/baixo é a palhetada.
- [ ] No estúdio (**🎛️ Editor Visual de Notas**), as teclas do PC configuradas tocam as casas e a
      palhetada (o botão de configuração de teclas mostra quais são).
  - Se falhar, me mande: o nome do controle que aparece no Windows (Painel de Controle >
    Dispositivos) e foto do Monitor.

### 5.6 Modo ⚡ Auto (troca sozinho de instrumento)

- [ ] Escolha **⚡ Auto**.
- [ ] Bata na bateria: a tela muda para a bateria.
- [ ] Toque a Pro Guitar em cordas diferentes: muda para a Pro Guitar.
- [ ] Toque uma tecla grave do teclado do RB3 (abaixo do Mi do meio): muda para o teclado e
      continua no teclado mesmo tocando teclas agudas.
- [ ] Use a guitarra de 5 botões pelo MIDI Pro Adapter: verde + palhetada tocam o acorde
      (a palhetada é reconhecida).
- [ ] Ao trocar de volta para outro instrumento, a tela acompanha.
  - Se falhar, me mande: foto do Monitor com as últimas linhas antes da troca errada.

### 5.7 Levar o som para um programa de música (DAW) com loopMIDI

- [ ] Instale o **loopMIDI** (<https://www.tobias-erichsen.de/software/loopmidi.html>) e crie uma
      porta chamada `MidGuitar Port`.
- [ ] No MidGuitar, em **🔊 Saída:**, escolha `MidGuitar Port`.
- [ ] No seu programa (Reaper, FL Studio, Ableton, Amplitube...), escolha `MidGuitar Port` como
      entrada MIDI de uma trilha com um instrumento virtual.
- [ ] Ao tocar o instrumento, o programa recebe as notas e faz som.
  - Se falhar, me mande: foto da tela de configuração MIDI do programa e do MidGuitar.

---

## 6. Passeio pela interface do estúdio (as 5 abas)

Faça este passeio uma vez com cada música de exemplo:

| Música | Como abrir |
|---|---|
| Joe Dassin - Salut les amoureux (Clone Hero) | **Buscar Pasta...** → `music\_refs\Joe Dassin - Salut les amoureux` |
| Gorillaz - Andromeda (PS3) | **📦 Abrir pacote** → `music\Gorillaz - Andromeda.pkg` |
| Joe Dassin - Salut les amoureux (Xbox 360) | **📦 Abrir pacote** → `music\Joe Dassin - Salut les amoureux_rb3con` |

- [ ] **⚡ Criação & Conversão 1 Clique**: a música abre (com a janelinha "Abrindo a música…"
      no caso dos pacotes), o cartão mostra título, artista e as contagens de notas.
- [ ] Arrastar o `.pkg` ou a pasta direto para a janela também abre a música.
- [ ] Abrir `music\PAVLO - Mediterranean Eyes` (depois de descompactar o `.zip`) mostra
      "Formato não suportado" com explicação, sem travar.
- [ ] **🎛️ Editor Visual de Notas (Mini-REAPER)**: as notas aparecem na trilha e dificuldade
      escolhidas; tocar (play) mostra as notas andando junto com o áudio.
- [ ] Edite uma nota: clique para adicionar uma nota nova e clique numa nota para apagar.
      Troque a dificuldade para Easy e confira que a edição não mexeu no Expert.
- [ ] **🖼️ Metadados, Capa & Exportação**: título, artista, álbum, ano, gênero e os rankings
      estão preenchidos; a capa aparece.
- [ ] **💾 Salvar Projeto**: salve como `.mgproj`. Feche o estúdio, abra de novo e use
      **📂 Abrir Projeto**: a música volta igual (notas, letra, capa, rankings).
- [ ] Exporte para **cada destino** do menu (RB3 PS3, RB2 PS3, Xbox 360 RB3, Xbox 360 RB2,
      PS4, Clone Hero). Em cada um: aparece a janelinha "Exportando…", a janela principal não
      congela e no fim aparece a verificação de compatibilidade.
- [ ] O PS4 avisa que é **experimental / não verificado**.
- [ ] **📦 Compilador de Pacotes**: adicione as 3 músicas, compile um pacote PS3 e um Clone Hero;
      aparece a janelinha "Compilando o pacote…" e depois a mensagem de sucesso.
- [ ] **📖 Guia Passo a Passo**: o botão **🖼️ Abrir Tutorial Visual Ilustrado** abre o tutorial
      com as imagens.
  - Se falhar, me mande: em qual aba e botão, a mensagem de erro (foto) e, se a janela
    travou, quanto tempo ficou travada.

---

## 7. O programa instalado (.exe)

- [ ] Abra `dist\MidGuitar\MidGuitar.exe` com dois cliques (não precisa do Python instalado).
- [ ] Teste rápido sem janela: abra o Prompt de Comando na pasta `dist\MidGuitar` e rode
      `MidGuitar.exe --selftest`. Depois abra `%TEMP%\midguitar_selftest.txt`: a última linha
      deve ser **OK**.
- [ ] Copie a pasta `dist\MidGuitar` inteira para outro lugar (ex.: `C:\Programas\MidGuitar`)
      e abra de lá: o programa abre normalmente.
- [ ] Mude o volume ou a porta MIDI, feche e abra de novo: a configuração foi lembrada
      (ela fica em `%APPDATA%\MidGuitar\config.json`).
- [ ] Repita de forma resumida o passeio da seção **6** (abrir o `.pkg` do Gorillaz, editar uma
      nota, salvar o projeto, exportar para Clone Hero e para RB3 PS3).
- [ ] O botão do **Tutorial Visual** abre o tutorial.
  - Se falhar, me mande: o arquivo `%TEMP%\midguitar_selftest.txt`, uma foto do erro e o
    caminho da pasta onde o `.exe` está.
