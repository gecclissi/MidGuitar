# 🎸 MidGuitar - Rock Band MIDI Controller & Studio

<div align="center">

![MidGuitar Icon](assets/icon.ico)

**Transforme qualquer guitarra de Rock Band (via MIDI Pro Adapter ou USB) em um poderoso controlador MIDI e estúdio de instrumentos para PC.**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com)
[![MIDI Standard](https://img.shields.io/badge/Standard-MIDI%201.0-FF6F00?style=for-the-badge)](https://www.midi.org/)
[![UI CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-1E293B?style=for-the-badge)](https://github.com/TomSchimansky/CustomTkinter)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

</div>

---

## 🎯 Sobre o Projeto

O **MidGuitar** foi desenvolvido para solucionar a limitação de compatibilidade entre guitarras de jogos musicais (Rock Band 3, Guitar Hero) e o ecossistema de produção musical no computador. 

Ele detecta automaticamente adaptadores MIDI (como o **Mad Catz Rock Band 3 MIDI Pro-Adapter**) ou conexões USB diretas, mapeia os sinais das casas (fretboard), palheta (strum bar) e alavanca (whammy bar), e gera som em tempo real tanto via **sintetizador integrado de baixa latência** quanto roteando eventos MIDI para softwares profissionais (DAWs como Reaper, FL Studio, Ableton, Amplitube e Guitar Rig).

---

## ✨ Principais Funcionalidades

- 🔌 **Detecção Automática Plug & Play**:
  - Varredura instantânea de portas de entrada MIDI (`MIDI Pro Adapter`, interfaces USB-MIDI).
  - Suporte adicional a guitarras USB diretas / receptores wireless reconhecidos como Gamepad pelo Windows.
  - Botão de atualização sem precisar reiniciar o aplicativo.

- 🔊 **Motor de Som Nativo Sem Instalação de DLLs**:
  - Usa o **Microsoft GS Wavetable Synthesizer** nativo do Windows com suporte a todos os **128 instrumentos General MIDI** (Guitarras Distorcidas, Overdrive, Limpa, Baixo, Pianos, Sintetizadores, etc.).
  - Funciona imediatamente após o download, sem necessidade de baixar pacotes SoundFont pesados ou compilar bibliotecas C.

- 🎛️ **Roteamento MIDI para DAWs e Plugins VST**:
  - Encaminha mensagens em tempo real para portas virtuais (como [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)), permitindo tocar guitarras virtuais realistas no **Amplitube, Neural DSP, Kontakt, Guitar Pro ou Reaper**.

- 🎨 **Interface Gráfica Moderna e Interativa**:
  - **Fretboard Visual**: os 5 botões de casas (Verde, Vermelho, Amarelo, Azul, Laranja) acendem em tempo real quando pressionados.
  - **Indicador de Palheta**: visualização de palhetada para cima e para baixo.
  - **Medidor de Alavanca (Whammy Bar)**: barra de progresso em tempo real que reflete o Pitch Bend físico.
  - **Monitor de Eventos MIDI**: log em tempo real com timestamp, tipo de mensagem, canal, nota e visualização hexadecimal.

- 📂 **Sistema de Presets Customizáveis (JSON)**:
  - `Rock Power Chords`: acordes de quinta em cada casa (E5, A5, D5, G5, C5) disparados pela palheta.
  - `Pentatonic Solo`: escala pentatônica em Mi menor para solos rápidos.
  - `Bass Groove`: mapeamento otimizado para linhas de contrabaixo elétrico.
  - `Pro Guitar (Direct)`: modo direto para instrumentos Pro Guitar (Mustang / Squier Stratocaster) e DAWs.

- ⚡ **Controles de Performance**:
  - Mudança de oitava em tempo real (-2 a +2 oitavas).
  - Slider de volume master (0% a 100%).
  - **Botão de Pânico (Panic)**: interrompe imediatamente todas as notas soando caso haja notas presas.

---

## 🛠️ Tecnologias Utilizadas

| Componente | Tecnologia | Finalidade |
|---|---|---|
| **Linguagem** | Python 3.9+ | Núcleo do sistema |
| **Comunicação MIDI** | `python-rtmidi` + `mido` | Leitura e envio de mensagens MIDI de altíssima velocidade e baixa latência |
| **Áudio Integrado** | `pygame.midi` (MMSystem) | Síntese de áudio nativa no Windows |
| **Interface de Usuário** | `customtkinter` | Interface escura, responsiva e moderna |
| **Empacotamento** | `pyinstaller` | Geração do executável `.exe` independente |

---

## 🚀 Como Usar o Executável (.exe)

1. Baixe ou gere a pasta do executável em `dist/MidGuitar/`.
2. Conecte o seu **MIDI Pro Adapter** ou guitarra na porta USB do computador.
3. Execute `MidGuitar.exe`.
4. O aplicativo detectará sua porta de entrada automaticamente. Clique em **Conectar**.
5. Toque a guitarra e ouça o som instantaneamente!

---

## 💻 Como Rodar via Código Fonte (Desenvolvimento)

### 1. Clonar o repositório
```bash
git clone https://github.com/gecclissi/MidGuitar.git
cd MidGuitar
```

### 2. Criar e ativar o ambiente virtual (recomendado)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instalar as dependências
```powershell
pip install -r requirements.txt
```

### 4. Executar o aplicativo
```powershell
python src/main.py
```

---

## 📦 Como Compilar o Executável (.exe)

O projeto inclui um script automatizado de compilação:

```powershell
python build_exe.py
```

O executável completo e todos os recursos serão gerados na pasta:
```
dist/MidGuitar/MidGuitar.exe
```

---

## 🎹 Mapeamento Padrão de Sinais MIDI

Ao utilizar o **Rock Band 3 MIDI Pro Adapter** em modo guitarra (chave na posição **G**):

| Controle da Guitarra | Sinal MIDI Enviado | Ação no MidGuitar |
|---|---|---|
| **Casa Verde** | Note On/Off (Nota 60 / C4) | Seleciona Nota/Acorde Verde |
| **Casa Vermelha** | Note On/Off (Nota 62 / D4) | Seleciona Nota/Acorde Vermelho |
| **Casa Amarela** | Note On/Off (Nota 64 / E4) | Seleciona Nota/Acorde Amarelo |
| **Casa Azul** | Note On/Off (Nota 65 / F4) | Seleciona Nota/Acorde Azul |
| **Casa Laranja** | Note On/Off (Nota 67 / G4) | Seleciona Nota/Acorde Laranja |
| **Palheta (Strum Down/Up)** | Note On (69 ou 71) / D-pad | Dispara o ataque do acorde/nota atual |
| **Alavanca (Whammy)** | Pitch Bend (0xE0) ou CC #1 | Modulação de afinação (-1.0 a +1.0) |
| **Botão Overdrive** | Note On (72) / Botão Select | Acentuação ou boost de oitava |

---

## 🎛️ Integração com DAWs (Reaper, FL Studio, Amplitube)

Para tocar usando instrumentos virtuais profissionais (VSTs):

1. Instale o driver gratuito **[loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)**.
2. No loopMIDI, crie uma porta virtual chamada `MidGuitar Port`.
3. Abra o **MidGuitar**, clique em **🔄 Atualizar** e selecione na **Saída de Áudio**: `[MIDI OUT] MidGuitar Port`.
4. Abra sua DAW favorita (ex: Reaper), ative `MidGuitar Port` nas opções de entrada MIDI e arme a faixa com seu plugin de guitarra preferido!

---

## 📁 Estrutura do Projeto

```
MidGuitar/
├── README.md                      # Documentação completa
├── requirements.txt               # Dependências do projeto
├── config.json                    # Configurações do usuário salvas
├── build_exe.py                   # Script de compilação PyInstaller
├── assets/
│   ├── icon.ico                   # Ícone do aplicativo
│   └── generate_icon.py           # Gerador do ícone
├── presets/                       # Presets de afinação e instrumentos
│   ├── rock_power_chords.json     # Acordes de força Rock
│   ├── pentatonic_solo.json       # Escala pentatônica para solos
│   ├── bass_groove.json           # Mapeamento para contrabaixo
│   └── pro_guitar_chromatic.json  # Modo direto para Pro Guitar
└── src/
    ├── main.py                    # Ponto de entrada
    ├── midi/
    │   ├── detector.py            # Varredura de hardware e portas
    │   ├── mapper.py              # Motor de acordes e casas
    │   └── reader.py              # Leitor assíncrono de eventos MIDI/USB
    ├── audio/
    │   └── engine.py              # Sintetizador nativo e saída MIDI
    ├── ui/
    │   ├── app.py                 # Janela principal (CustomTkinter)
    │   ├── fretboard_view.py      # Braço interativo da guitarra
    │   └── monitor_view.py        # Console de eventos em tempo real
    └── utils/
        ├── config_manager.py      # Gerenciador de configurações e presets
        └── instruments.py         # Mapeamento de 128 instrumentos General MIDI
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte `LICENSE` para mais informações.
