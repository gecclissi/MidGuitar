# 🎸 MidGuitar - Universal Rock Band & MIDI Studio

<div align="center">

![MidGuitar Icon](assets/icon.ico)

**O estúdio MIDI definitivo para transformar qualquer instrumento musical de Rock Band e Guitar Hero em controladores MIDI profissionais para PC.**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com)
[![MIDI Standard](https://img.shields.io/badge/Standard-MIDI%201.0-FF6F00?style=for-the-badge)](https://www.midi.org/)
[![UI CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-1E293B?style=for-the-badge)](https://github.com/TomSchimansky/CustomTkinter)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

</div>

---

## 🎯 Sobre o Projeto

O **MidGuitar Studio** é uma central universal de instrumentos MIDI desenvolvida para conectar, mapear e executar em tempo real qualquer instrumento musical do ecossistema de jogos (com saídas MIDI físicas DIN de 5 pinos ou via USB/MIDI Pro Adapter):

1. 🎸 **Fender Squier Stratocaster (Rock Band 3 Pro Guitar)**: Guitarra real com cordas de verdade, captação e saída MIDI física de 5 pinos.
2. 🎸 **Fender Mustang PRO-Guitar (Rock Band 3)**: Guitarra com 102 botões clicáveis no braço (6 cordas x 17 trastes), 6 sensores de corda palhetáveis e saída MIDI de 5 pinos.
3. 🎹 **Rock Band 3 Wireless Keyboard**: Teclado/Keytar com 25 teclas sensíveis à velocidade (C3 a C5), fita touch ribbon (pitch bend/modulação) e saída MIDI física.
4. 🥁 **Baterias Eletrônicas Band Hero / Guitar Hero World Tour / 5 / Rock Band**: Baterias com saída MIDI física de 5 pinos transmitindo percussão com sensibilidade a força (Velocity) no **Canal MIDI 10**.
5. 🎮 **Guitarras Clássicas Rock Band / Guitar Hero (5 Botões)**: Conectadas via MIDI Pro Adapter (Mad Catz) ou receptores USB diretos.

---

## ✨ Principais Funcionalidades

- ⚡ **Detecção Automática de Instrumento (Auto Mode)**:
  - O aplicativo escuta as mensagens e comuta automaticamente o visualizador e a resposta sonora para o instrumento que estiver tocando:
    - Bateria no Canal 10 ➔ Ativa visualizador de Bateria e sintetizador de percussão GM.
    - Notas nos Canais 1 a 6 ➔ Ativa visualizador de Guitarra Pro (6 cordas polifônicas).
    - Teclas de C3 a C5 no Canal 1 ➔ Ativa visualizador de Teclado.
    - 5 Casas clássicas / Strum ➔ Ativa visualizador de 5 botões com sistema de acordes.

- 🎛️ **4 Visualizadores Gráficos Especializados em Tempo Real**:
  - **Guitarra Pro**: Desenho em alta precisão do braço com 6 cordas (E, A, D, G, B, E) e 17 trastes, indicando exatamente a corda tocada, a casa apertada e a nota resultante.
  - **Teclado (25 Teclas)**: Teclas brancas e pretas que acendem dinamicamente e medidor vertical da fita de toque (Touch Strip / Modulação).
  - **Bateria Eletrônica**: 6 pads (Bumbo Kick 36, Caixa Snare 38, Chimbal Hi-Hat 42/46, Tom 1 48, Surdo 41, Pratos Crash/Ride 49/55) com medidor de força (Velocity) e contador de toques.
  - **Guitarra 5 Botões**: Cores clássicas (Verde, Vermelho, Amarelo, Azul, Laranja), feedback de palhetada (Strum Up/Down) e alavanca (Whammy Bar).

- 🔊 **Motor de Áudio Híbrido e Flexível**:
  - **Síntese Nativa do Windows**: Toca imediatamente usando o Microsoft GS Wavetable Synth com 128 instrumentos General MIDI e o Kit de Bateria no Canal 10, sem necessidade de baixar pacotes externos.
  - **Roteamento para DAWs (Reaper, FL Studio, Amplitube, EZDrummer)**: Encaminha eventos em tempo real para portas virtuais (via [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)).

- 📂 **Presets de Afinação e Acordes Customizáveis**:
  - `Rock Power Chords`: Acordes de quinta prontos para tocar rock com a palheta.
  - `Pentatonic Solo`: Solos rápidos na escala pentatônica menor de Mi.
  - `Bass Groove`: Linhas de baixo elétrico com pegada encorpada.
  - `Pro Guitar Chromatic`: Transmissão direta sem quantização para DAWs e VSTs.

---

## 🛠️ Tecnologias Utilizadas

| Componente | Tecnologia | Finalidade |
|---|---|---|
| **Linguagem** | Python 3.9+ | Núcleo do sistema |
| **Comunicação MIDI** | `python-rtmidi` + `mido` | Leitura e envio de mensagens MIDI de altíssima velocidade e baixa latência |
| **Áudio Integrado** | `pygame.midi` (MMSystem) | Síntese de áudio nativa no Windows (Instrumentos + Percussão Canal 10) |
| **Interface de Usuário** | `customtkinter` | Interface escura, responsiva e moderna |
| **Empacotamento** | `pyinstaller` | Geração do executável `.exe` independente |

---

## 🚀 Como Usar o Executável (.exe)

1. Baixe ou acerte a pasta do executável em `dist/MidGuitar/`.
2. Conecte o cabo MIDI da sua guitarra, teclado ou bateria ao computador (usando interface USB-MIDI ou MIDI Pro Adapter).
3. Execute `MidGuitar.exe`.
4. Selecione a sua porta de entrada e clique em **Conectar**.
5. Toque qualquer instrumento! O aplicativo responderá visualmente e sonoramente na mesma hora.

---

## 💻 Como Rodar via Código Fonte (Desenvolvimento)

```powershell
# 1. Clonar o repositório
git clone https://github.com/gecclissi/MidGuitar.git
cd MidGuitar

# 2. Criar e ativar o ambiente virtual
python -m venv venv
.\venv\Scripts\activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Executar o estúdio
python src/main.py
```

---

## 📦 Como Compilar o Executável (.exe)

```powershell
python build_exe.py
```

O executável completo será gerado em:
```text
dist/MidGuitar/MidGuitar.exe
```

---

## 🎹 Especificações de Mapeamento MIDI dos Instrumentos

### 1. Guitarra Pro (Rock Band 3 Squier & Mustang)
A guitarra transmite em **um canal MIDI dedicado para cada corda**:
* **6ª Corda (Mi Grave / Low E):** Canal MIDI 6 (Nota base 40 / E2 + número do traste 0–17)
* **5ª Corda (Lá / A):** Canal MIDI 5 (Nota base 45 / A2 + número do traste 0–17)
* **4ª Corda (Ré / D):** Canal MIDI 4 (Nota base 50 / D3 + número do traste 0–17)
* **3ª Corda (Sol / G):** Canal MIDI 3 (Nota base 55 / G3 + número do traste 0–17)
* **2ª Corda (Si / B):** Canal MIDI 2 (Nota base 59 / B3 + número do traste 0–17)
* **1ª Corda (Mi Agudo / High E):** Canal MIDI 1 (Nota base 64 / E4 + número do traste 0–17)

### 2. Teclado Rock Band 3 (Keytar)
* **Teclas:** 25 teclas polifônicas sensíveis à velocidade transmitindo no **Canal MIDI 1** (C3 = Nota 48 até C5 = Nota 72).
* **Fita Touch Ribbon:** Control Change CC #1 (Modulação) e Pitch Bend.

### 3. Baterias (Band Hero / Guitar Hero / Rock Band Drums)
Transmitem exclusivamente no **Canal MIDI 10** (Percussão General MIDI):
* **Pedal de Bumbo (Kick):** Nota 36 (C1)
* **Pad Vermelho (Caixa / Snare):** Nota 38 (D1)
* **Pad Amarelo (Chimbal / Hi-Hat):** Nota 42 / 46 (F#1 / A#1)
* **Pad Azul (Tom 1 / Ride):** Nota 48 / 51
* **Pad Verde (Surdo / Crash 1):** Nota 41 / 49
* **Pad Laranja (Prato Splash / Crash 2):** Nota 55

---

## 🎛️ Integração com DAWs e VSTs Profissionais

1. Instale o driver virtual gratuito **[loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)**.
2. Crie uma porta virtual chamada `MidGuitar Port`.
3. No **MidGuitar Studio**, selecione na **Saída de Áudio**: `[MIDI OUT] MidGuitar Port`.
4. Abra seu DAW preferido (Reaper, Ableton, FL Studio, Amplitube, EZDrummer, Superior Drummer, Kontakt) e selecione `MidGuitar Port` como entrada MIDI!

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte `LICENSE` para mais informações.
