"""
Script de geração de telas visuais do tutorial do MidGuitar.
Gera imagens ricas em alta definição (1280x760) simulando a interface real
com anotações passo a passo, badges numerados, setas e destaques explicativos.
"""

import os
from PIL import Image, ImageDraw, ImageFont

# Cores do tema escuro moderno do MidGuitar
BG_DARK = (18, 20, 32, 255)         # Fundo geral
BG_PANEL = (28, 31, 48, 255)        # Cards e painéis
BG_HEADER = (23, 25, 38, 255)       # Barra de título e cabeçalho
BORDER_COLOR = (45, 52, 80, 255)    # Bordas sutis
TEXT_WHITE = (248, 250, 252, 255)   # Texto principal
TEXT_MUTED = (148, 163, 184, 255)   # Texto secundário
CYAN_ACCENT = (56, 189, 248, 255)   # Acento ciano (#38bdf8)
GREEN_ACCENT = (34, 197, 94, 255)   # Botão positivo (#22c55e)
AMBER_ACCENT = (245, 158, 11, 255)  # Alertas e badges (#f59e0b)
PURPLE_ACCENT = (168, 85, 247, 255) # Destaques especiais (#a855f7)
RED_ACCENT = (239, 68, 68, 255)     # Vermelho (#ef4444)
BLUE_ACCENT = (59, 130, 246, 255)   # Azul (#3b82f6)
ORANGE_ACCENT = (249, 115, 22, 255) # Laranja (#f97316)

# Carregamento de fontes
try:
    FONT_TITLE = ImageFont.truetype("segoeuib.ttf", 24)
    FONT_SUBTITLE = ImageFont.truetype("segoeuib.ttf", 18)
    FONT_BOLD = ImageFont.truetype("segoeuib.ttf", 15)
    FONT_REGULAR = ImageFont.truetype("segoeui.ttf", 14)
    FONT_SMALL = ImageFont.truetype("segoeui.ttf", 12)
    FONT_BADGE = ImageFont.truetype("segoeuib.ttf", 16)
    FONT_CODE = ImageFont.truetype("consola.ttf", 13)
except Exception:
    FONT_TITLE = ImageFont.load_default()
    FONT_SUBTITLE = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()
    FONT_REGULAR = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_BADGE = ImageFont.load_default()
    FONT_CODE = ImageFont.load_default()


def create_base_canvas(width=1280, height=760):
    img = Image.new("RGBA", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)
    return img, draw


def draw_window_frame(draw, x, y, w, h, title="MidGuitar"):
    # Fundo da janela com borda
    draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=12, fill=BG_PANEL, outline=BORDER_COLOR, width=2)
    # Barra de título
    draw.rounded_rectangle([(x, y), (x + w, y + 42)], radius=12, fill=BG_HEADER)
    draw.rectangle([(x, y + 25), (x + w, y + 42)], fill=BG_HEADER)
    draw.line([(x, y + 42), (x + w, y + 42)], fill=BORDER_COLOR, width=1)
    
    # Botões de fechar/minimizar
    draw.ellipse([(x + 16, y + 14), (x + 28, y + 26)], fill=(239, 68, 68, 255))
    draw.ellipse([(x + 36, y + 14), (x + 48, y + 26)], fill=(245, 158, 11, 255))
    draw.ellipse([(x + 56, y + 14), (x + 68, y + 26)], fill=(34, 197, 94, 255))
    
    # Título da janela
    draw.text((x + 80, y + 12), title, font=FONT_BOLD, fill=TEXT_WHITE)


def draw_badge(draw, cx, cy, number, bg_color=AMBER_ACCENT, text_color=(0, 0, 0, 255), radius=15):
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill=bg_color, outline=(255, 255, 255, 240), width=2)
    t = str(number)
    bbox = FONT_BADGE.getbbox(t)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2 - 2), t, font=FONT_BADGE, fill=text_color)


def draw_callout_box(draw, x, y, w, h, badge_num, title, description, badge_color=AMBER_ACCENT):
    draw.rounded_rectangle([(x, y), (x + w, y + h)], radius=8, fill=(20, 24, 38, 240), outline=badge_color, width=2)
    draw_badge(draw, x + 24, y + 24, badge_num, bg_color=badge_color)
    draw.text((x + 50, y + 14), title, font=FONT_BOLD, fill=TEXT_WHITE)
    
    # Quebra de linha de texto
    lines = []
    words = description.split(" ")
    curr = ""
    for w_word in words:
        if len(curr + " " + w_word) > 42:
            lines.append(curr)
            curr = w_word
        else:
            curr = curr + (" " if curr else "") + w_word
    if curr:
        lines.append(curr)
        
    line_y = y + 38
    for line in lines:
        draw.text((x + 50, line_y), line, font=FONT_SMALL, fill=TEXT_MUTED)
        line_y += 18


# ==============================================================================
# 1. TELA PRINCIPAL (Visão Geral e Acesso ao Estúdio)
# ==============================================================================
def generate_01_tela_principal(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 01 • TELA PRINCIPAL DO MIDGUITAR", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "Visão geral da interface, painel de conexão de instrumentos e acesso ao Estúdio de Criação", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "MidGuitar - MIDI Instrument Controller & Song Creator v2.5")
    
    # Barra Superior do App
    draw.rounded_rectangle([(wx + 20, wy + 60), (wx + ww - 20, wy + 115)], radius=8, fill=(35, 40, 62, 255), outline=BORDER_COLOR)
    draw.text((wx + 35, wy + 72), "[MIDGUITAR 2.5]", font=FONT_SUBTITLE, fill=CYAN_ACCENT)
    draw.text((wx + 35, wy + 93), "Status: Pronto • Audio Ativo • SoundFont Integrada", font=FONT_SMALL, fill=GREEN_ACCENT)
    
    # Botão de Abertura do Estúdio (Destaque Principal)
    studio_btn_rect = [(wx + ww - 310, wy + 68), (wx + ww - 30, wy + 107)]
    draw.rounded_rectangle(studio_btn_rect, radius=6, fill=CYAN_ACCENT)
    draw.text((wx + ww - 280, wy + 78), "ESTUDIO DE CRIACAO", font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    # Área Central - Conexões e Dispositivos
    draw.rounded_rectangle([(wx + 20, wy + 130), (wx + ww - 20, wy + 260)], radius=8, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 35, wy + 142), "Conexao de Dispositivos e Controles:", font=FONT_BOLD, fill=TEXT_WHITE)
    
    labels = ["Dispositivo MIDI Entrada:", "Joystick / Guitarra USB:", "Saida de Audio / MIDI:"]
    vals = ["Nenhum (Usando Teclado PC)", "Guitarra PS3/PC Detectada", "Sintetizador Integrado MidGuitar"]
    for i, (lbl, val) in enumerate(zip(labels, vals)):
        bx = wx + 35 + i * 255
        by = wy + 175
        draw.text((bx, by), lbl, font=FONT_SMALL, fill=TEXT_MUTED)
        draw.rounded_rectangle([(bx, by + 20), (bx + 235, by + 52)], radius=5, fill=(35, 40, 62, 255), outline=BORDER_COLOR)
        draw.text((bx + 10, by + 28), val, font=FONT_SMALL, fill=TEXT_WHITE)
    
    # Área de Teclado / Fretboard Virtual
    draw.rounded_rectangle([(wx + 20, wy + 275), (wx + ww - 20, wy + 480)], radius=8, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 35, wy + 288), "Braco Virtual da Guitarra (5 Cores & Palheta)", font=FONT_BOLD, fill=TEXT_WHITE)
    draw.text((wx + 35, wy + 310), "Voce pode tocar ao vivo usando seu teclado de computador ou joystick/guitarra USB:", font=FONT_SMALL, fill=TEXT_MUTED)
    
    fret_colors = [
        ("Verde (1 / F1)", GREEN_ACCENT),
        ("Vermelho (2 / F2)", RED_ACCENT),
        ("Amarelo (3 / F3)", AMBER_ACCENT),
        ("Azul (4 / F4)", BLUE_ACCENT),
        ("Laranja (5 / F5)", ORANGE_ACCENT),
    ]
    for i, (name, col) in enumerate(fret_colors):
        fx = wx + 35 + i * 150
        fy = wy + 340
        draw.rounded_rectangle([(fx, fy), (fx + 135, fy + 70)], radius=10, fill=col)
        draw.text((fx + 12, fy + 26), name, font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    # Barra de Palhetada
    draw.rounded_rectangle([(wx + 35, wy + 425), (wx + ww - 35, wy + 465)], radius=8, fill=(50, 58, 85, 255), outline=CYAN_ACCENT)
    draw.text((wx + 220, wy + 437), "BARRA DE PALHETADA (Strum: Tecla ESPACO ou Enter)", font=FONT_BOLD, fill=TEXT_WHITE)
    
    # Rodapé da janela
    draw.rounded_rectangle([(wx + 20, wy + 495), (wx + ww - 20, wy + 610)], radius=8, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 35, wy + 510), "Dicas Rapidas:", font=FONT_BOLD, fill=CYAN_ACCENT)
    draw.text((wx + 35, wy + 535), "- Clique em 'ESTUDIO DE CRIACAO' para criar musicas a partir de MP3 ou converter pacotes.", font=FONT_REGULAR, fill=TEXT_WHITE)
    draw.text((wx + 35, wy + 560), "- Conecte guitarras de PS3, Xbox ou genericas no USB; elas sao reconhecidas automaticamente.", font=FONT_REGULAR, fill=TEXT_MUTED)
    draw.text((wx + 35, wy + 582), "- Escolha presets prontos ou personalize qualquer tecla nas configuracoes.", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    # Painel Lateral de Explicações
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Abrir o Estudio de Criacao",
                     "Clique neste botao para abrir o estudio completo de autoria, importacao de MP3 e conversao de pacotes.", CYAN_ACCENT)
    
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "Dispositivos & Instrumentos",
                     "Escolha se quer tocar pelo teclado de digitacao, guitarra do Rock Band / Guitar Hero USB ou teclado MIDI.", AMBER_ACCENT)
    
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Tocar ao Vivo e Testar",
                     "As 5 cores funcionam como trastes e a barra de espaco atua como a palheta da guitarra.", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "Zero Instalacao Externa",
                     "Nao precisa de Reaper, nem Magma, nem Python extra. Tudo funciona dentro deste unico executavel.", PURPLE_ACCENT)

    # Badges indicadores
    draw_badge(draw, wx + ww - 325, wy + 88, 1, CYAN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + ww - 40, wy + 145, 2, AMBER_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + ww - 40, wy + 290, 3, GREEN_ACCENT, (0, 0, 0, 255))
    
    img.save(output_path)
    print(f"Gerado: {output_path}")


# ==============================================================================
# 2. ESTÚDIO DE CRIAÇÃO - VISÃO GERAL DAS ABAS
# ==============================================================================
def generate_02_estudio_navegacao_geral(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 02 • ESTUDIO DE CRIACAO - AS 6 ETAPAS", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "O fluxo intuitivo passo a passo projetado para qualquer pessoa leiga criar musicas em minutos", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "Estudio de Criacao e Conversor All-In-One")
    
    # Barra de Abas
    tabs = [
        ("1. Importar", True),
        ("2. Mini-Reaper", False),
        ("3. Auto-Chart", False),
        ("4. Metadados", False),
        ("5. Exportar", False),
        ("6. Ajuda", False)
    ]
    tab_x = wx + 15
    for title, is_active in tabs:
        tw = 125
        fill_col = CYAN_ACCENT if is_active else (35, 40, 60, 255)
        text_col = (10, 15, 30, 255) if is_active else TEXT_MUTED
        draw.rounded_rectangle([(tab_x, wy + 55), (tab_x + tw, wy + 90)], radius=6, fill=fill_col)
        draw.text((tab_x + 15, wy + 65), title, font=FONT_BOLD, fill=text_col)
        tab_x += tw + 8
        
    # Conteúdo Visual das 6 Etapas
    step_cards = [
        ("1. Importar Musica / Audio", "Arraste qualquer MP3, WAV, OGG do seu computador, ou adicione Stems de instrumentos.", CYAN_ACCENT),
        ("2. Mini-Reaper Integrado", "Edite notas na linha do tempo com visual profissional estilo DAW sem complicacao.", AMBER_ACCENT),
        ("3. Gerador Automatico & Letras", "Gere notas de Guitarra, Baixo, Bateria, Teclado e sincronize letras .txt/.lrc com 1 clique.", GREEN_ACCENT),
        ("4. Metadados & Capa", "Defina nome da musica, artista, ano, dificuldade e anexe a capa do album.", BLUE_ACCENT),
        ("5. Exportar para Jogos", "Escolha PS3 PKG, Clone Hero, YARG ou Rock Band 3 e clique em Exportar.", PURPLE_ACCENT),
        ("6. Aba de Ajuda e Explicacoes", "Guia completo com perguntas frequentes, tutoriais de pendrive e dicas.", ORANGE_ACCENT),
    ]
    
    for i, (title, desc, color) in enumerate(step_cards):
        col_idx = i % 2
        row_idx = i // 2
        cx = wx + 25 + col_idx * 385
        cy = wy + 110 + row_idx * 165
        cw = 370
        ch = 145
        
        draw.rounded_rectangle([(cx, cy), (cx + cw, cy + ch)], radius=10, fill=BG_DARK, outline=color, width=2)
        draw.rounded_rectangle([(cx, cy), (cx + cw, cy + 38)], radius=10, fill=(35, 40, 65, 255))
        draw.rectangle([(cx, cy + 25), (cx + cw, cy + 38)], fill=(35, 40, 65, 255))
        
        draw_badge(draw, cx + 24, cy + 20, str(i + 1), bg_color=color, text_color=(0, 0, 0, 255), radius=12)
        draw.text((cx + 45, cy + 10), title, font=FONT_BOLD, fill=TEXT_WHITE)
        
        # Descrição
        lines = []
        words = desc.split(" ")
        curr = ""
        for w_word in words:
            if len(curr + " " + w_word) > 40:
                lines.append(curr)
                curr = w_word
            else:
                curr = curr + (" " if curr else "") + w_word
        if curr:
            lines.append(curr)
        for l_idx, line in enumerate(lines):
            draw.text((cx + 18, cy + 50 + l_idx * 20), line, font=FONT_REGULAR, fill=TEXT_MUTED)
            
    # Painel Lateral
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Navegacao por Abas",
                     "Siga as abas da esquerda para a direita (1 a 5) para criar sua musica completa do inicio ao fim.", CYAN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "Liberdade de Edicao",
                     "Voce pode ir e voltar entre as abas a qualquer momento sem perder o progresso das suas edicoes.", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Para Todos os Publicos",
                     "Se voce for leigo, apenas use a Aba 1 e Aba 3 para fazer tudo automatico. Se for avancado, use a Aba 2 para detalhar.", AMBER_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "Aba 6 com Manual",
                     "Sempre que tiver duvidas, a Aba 6 tem um guia completo embutido explicando cada formato de jogo.", PURPLE_ACCENT)
                     
    img.save(output_path)
    print(f"Gerado: {output_path}")


# ==============================================================================
# 3. ABA 1 - IMPORTAÇÃO DE ÁUDIO, STEMS E PACOTES
# ==============================================================================
def generate_03_importacao_audio(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 03 • IMPORTAR AUDIO, STEMS OU PACOTES", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "Aba 1: Como subir musicas do YouTube/MP3 ou carregar pacotes prontos de fas", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "Estudio de Criacao • Aba 1: Importar Musica")
    
    # Aba ativa
    draw.rounded_rectangle([(wx + 15, wy + 55), (wx + 150, wy + 90)], radius=6, fill=CYAN_ACCENT)
    draw.text((wx + 30, wy + 65), "1. Importar", font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    # Área de Drag & Drop
    drop_rect = [(wx + 30, wy + 110), (wx + ww - 30, wy + 260)]
    draw.rounded_rectangle(drop_rect, radius=12, fill=BG_DARK, outline=CYAN_ACCENT, width=2)
    draw.text((wx + 220, wy + 140), "[+] ARRASTE E SOLTE SEU ARQUIVO AQUI", font=FONT_SUBTITLE, fill=CYAN_ACCENT)
    draw.text((wx + 180, wy + 175), "Formatos de Audio: .MP3, .WAV, .OGG, .FLAC", font=FONT_REGULAR, fill=TEXT_WHITE)
    draw.text((wx + 150, wy + 200), "Formatos de Pacote: .CON, .PKG, .SNG, song.ini ou pastas do Clone Hero", font=FONT_SMALL, fill=TEXT_MUTED)
    
    # Botão de Selecionar Arquivo
    btn_audio = [(wx + 270, wy + 215), (wx + 530, wy + 250)]
    draw.rounded_rectangle(btn_audio, radius=6, fill=(45, 55, 85, 255), outline=CYAN_ACCENT)
    draw.text((wx + 300, wy + 225), "Procurar no Computador...", font=FONT_BOLD, fill=TEXT_WHITE)
    
    # Botões Adicionais de Stems e Pacotes
    bx1 = [(wx + 30, wy + 280), (wx + 395, wy + 350)]
    draw.rounded_rectangle(bx1, radius=8, fill=BG_DARK, outline=AMBER_ACCENT)
    draw.text((wx + 45, wy + 295), "Configurar Stems Individuais", font=FONT_BOLD, fill=AMBER_ACCENT)
    draw.text((wx + 45, wy + 320), "Adicione faixas separadas de Voz, Bateria,", font=FONT_SMALL, fill=TEXT_MUTED)
    draw.text((wx + 45, wy + 335), "Baixo, Guitarra e Backing Track se tiver.", font=FONT_SMALL, fill=TEXT_MUTED)
    
    bx2 = [(wx + 425, wy + 280), (wx + ww - 30, wy + 350)]
    draw.rounded_rectangle(bx2, radius=8, fill=BG_DARK, outline=GREEN_ACCENT)
    draw.text((wx + 440, wy + 295), "Importar Pacote Existente de Fa", font=FONT_BOLD, fill=GREEN_ACCENT)
    draw.text((wx + 440, wy + 320), "Carregue musicas do C3 Universe, Chorus,", font=FONT_SMALL, fill=TEXT_MUTED)
    draw.text((wx + 440, wy + 335), "consolide em lote ou converta para PS3.", font=FONT_SMALL, fill=TEXT_MUTED)
    
    # Painel de Status de Áudio Detectado
    draw.rounded_rectangle([(wx + 30, wy + 370), (wx + ww - 30, wy + 600)], radius=8, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 45, wy + 385), "Informacoes do Arquivo Carregado:", font=FONT_BOLD, fill=TEXT_WHITE)
    
    stats = [
        ("Musica Detectada:", "Exemplo_Rock_Track.mp3"),
        ("Duracao Total:", "03:45 (225 segundos)"),
        ("Taxa de Amostragem:", "44100 Hz (Estereo - 2 Canais)"),
        ("BPM Estimado:", "128 BPM (Compasso 4/4)"),
        ("Trilha de Vocais:", "Aguardando sincronizacao de letra na Aba 3"),
        ("Proximo Passo Recomendado:", "Ir para Aba 3 para gerar as notas automaticamente!")
    ]
    for i, (k, v) in enumerate(stats):
        draw.text((wx + 45, wy + 420 + i * 28), k, font=FONT_BOLD, fill=TEXT_MUTED)
        draw.text((wx + 260, wy + 420 + i * 28), v, font=FONT_REGULAR, fill=CYAN_ACCENT if i == 5 else TEXT_WHITE)

    # Callouts
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Arraste Qualquer MP3",
                     "Basta arrastar o arquivo de audio da musica que voce baixou. O app ja calcula o tempo e a duracao.", CYAN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "Stems Opcionais",
                     "Se tiver faixas separadas (Vocal, Bateria, etc.), clique em Stems para ter volumes separados no jogo.", AMBER_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Importacao de Musicas de Fas",
                     "Baixou do C3 Universe ou Chorus? Suba o arquivo aqui para converter para PS3 PKG direto!", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "Zero Complicacao",
                     "Nenhum conhecimento tecnico necessario. Uma vez carregado o audio, va direto para a Aba 3.", PURPLE_ACCENT)

    draw_badge(draw, wx + ww - 60, wy + 130, 1, CYAN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + 365, wy + 300, 2, AMBER_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + ww - 60, wy + 300, 3, GREEN_ACCENT, (0, 0, 0, 255))

    img.save(output_path)
    print(f"Gerado: {output_path}")


# ==============================================================================
# 4. ABA 3 - GERADOR AUTOMÁTICO E SINCRONIZADOR DE LETRAS
# ==============================================================================
def generate_04_auto_chart_e_letras(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 04 • AUTO-CHART E SINCRONIZADOR DE LETRAS", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "Gere todas as notas de todos os instrumentos e sincronize as letras para o vocal com 1 clique", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "Estudio de Criacao • Aba 3: Gerador Automatico de Notas & Letras")
    
    # Aba ativa
    draw.rounded_rectangle([(wx + 285, wy + 55), (wx + 430, wy + 90)], radius=6, fill=CYAN_ACCENT)
    draw.text((wx + 305, wy + 65), "3. Auto-Chart", font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    # Painel de Instrumentos
    draw.rounded_rectangle([(wx + 30, wy + 105), (wx + ww - 30, wy + 225)], radius=8, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 45, wy + 115), "Instrumentos a Gerar Automaticamente:", font=FONT_BOLD, fill=TEXT_WHITE)
    
    instruments = [
        ("[x] Guitarra Principal", GREEN_ACCENT),
        ("[x] Baixo Eletrico", RED_ACCENT),
        ("[x] Bateria (Drums)", AMBER_ACCENT),
        ("[x] Teclado / Keys", BLUE_ACCENT),
        ("[x] Vocais (Canto)", PURPLE_ACCENT),
    ]
    for i, (inst, col) in enumerate(instruments):
        ix = wx + 45 + (i % 3) * 240
        iy = wy + 145 + (i // 3) * 40
        draw.text((ix, iy), inst, font=FONT_BOLD, fill=col)
        
    # Painel do Sincronizador de Letras
    modal_rect = [(wx + 30, wy + 240), (wx + ww - 30, wy + 520)]
    draw.rounded_rectangle(modal_rect, radius=10, fill=(24, 28, 44, 255), outline=PURPLE_ACCENT, width=2)
    
    draw.rounded_rectangle([(wx + 30, wy + 240), (wx + ww - 30, wy + 280)], radius=10, fill=(38, 44, 70, 255))
    draw.rectangle([(wx + 30, wy + 265), (wx + ww - 30, wy + 280)], fill=(38, 44, 70, 255))
    draw.text((wx + 45, wy + 250), "Sincronizador de Letras e Vocais (Novo!)", font=FONT_BOLD, fill=TEXT_WHITE)
    
    # Botão de Carregar Arquivo de Letra
    btn_lrc = [(wx + 45, wy + 295), (wx + 260, wy + 330)]
    draw.rounded_rectangle(btn_lrc, radius=6, fill=PURPLE_ACCENT)
    draw.text((wx + 60, wy + 305), "Carregar .TXT ou .LRC...", font=FONT_BOLD, fill=TEXT_WHITE)
    
    draw.text((wx + 280, wy + 305), "ou cole o texto da musica diretamente abaixo:", font=FONT_SMALL, fill=TEXT_MUTED)
    
    # Caixa de texto simulada com letra
    draw.rounded_rectangle([(wx + 45, wy + 340), (wx + ww - 45, wy + 450)], radius=6, fill=(15, 17, 26, 255), outline=BORDER_COLOR)
    sample_lyrics = [
        "[00:15.20] Nesta noite sem fim eu procurei",
        "[00:19.80] O caminho que me leva ate voce",
        "[00:24.50] E as guitarras comecam a soar bem alto...",
        "-> O motor silabifica automaticamente: 'Nes-ta noi-te sem fim eu pro-cu-rei'"
    ]
    for idx, line in enumerate(sample_lyrics):
        col = GREEN_ACCENT if idx == 3 else TEXT_MUTED
        draw.text((wx + 55, wy + 350 + idx * 22), line, font=FONT_CODE, fill=col)
        
    draw.text((wx + 45, wy + 465), "- Separacao silabica no padrao oficial RBN (com hifen nas silabas intermediarias)", font=FONT_SMALL, fill=GREEN_ACCENT)
    draw.text((wx + 45, wy + 488), "- Geracao automatica de Frases Vocais (Note 105) e Overdrive (Note 106)", font=FONT_SMALL, fill=GREEN_ACCENT)
    
    # Botão Master de Geração
    btn_master = [(wx + 30, wy + 540), (wx + ww - 30, wy + 605)]
    draw.rounded_rectangle(btn_master, radius=8, fill=GREEN_ACCENT)
    draw.text((wx + 150, wy + 560), "GERAR TODAS AS NOTAS E VOCAIS COM 1 CLIQUE!", font=FONT_SUBTITLE, fill=(10, 15, 30, 255))

    # Callouts
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Escolha os Instrumentos",
                     "Marque os instrumentos desejados. Mesmo que a musica nao tenha teclado original, ele pode ser gerado!", CYAN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "Cole a Letra ou Suba .LRC",
                     "Basta colar a letra ou carregar um arquivo .txt / .lrc. O sistema alinha as palavras nas notas vocais.", PURPLE_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Padrao Oficial RBN",
                     "As silabas recebem hifen automaticamente para a bolinha do jogo rolar perfeitamente no videogame.", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "1 Clique e Pronto",
                     "Ao clicar no botao verde, o algoritmo cria as 4 dificuldades (Expert, Hard, Medium, Easy) na hora.", AMBER_ACCENT)

    draw_badge(draw, wx + ww - 60, wy + 135, 1, CYAN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + ww - 60, wy + 265, 2, PURPLE_ACCENT, (255, 255, 255, 255))
    draw_badge(draw, wx + ww - 60, wy + 565, 4, GREEN_ACCENT, (0, 0, 0, 255))

    img.save(output_path)
    print(f"Gerado: {output_path}")


# ==============================================================================
# 5. ABA 2 - MINI-REAPER DAW E EDIÇÃO MANUAL
# ==============================================================================
def generate_05_mini_reaper_edicao(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 05 • MINI-REAPER DAW (VISUALIZACAO E EDICAO)", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "Interface estilo Reaper para ver as notas geradas, editar manualmente ou tocar para testar", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "Estudio de Criacao • Aba 2: Mini-Reaper Canvas DAW")
    
    # Aba ativa
    draw.rounded_rectangle([(wx + 150, wy + 55), (wx + 295, wy + 90)], radius=6, fill=CYAN_ACCENT)
    draw.text((wx + 165, wy + 65), "2. Mini-Reaper", font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    # Controles do Mini-Reaper
    draw.rounded_rectangle([(wx + 20, wy + 100), (wx + ww - 20, wy + 145)], radius=6, fill=BG_DARK, outline=BORDER_COLOR)
    
    # Botão Play / Stop
    draw.rounded_rectangle([(wx + 30, wy + 107), (wx + 110, wy + 138)], radius=5, fill=GREEN_ACCENT)
    draw.text((wx + 45, wy + 114), "PLAY", font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    # Seletor de Trilha
    draw.text((wx + 130, wy + 116), "Trilha Ativa:", font=FONT_BOLD, fill=TEXT_MUTED)
    draw.rounded_rectangle([(wx + 220, wy + 107), (wx + 380, wy + 138)], radius=5, fill=(35, 40, 65, 255), outline=CYAN_ACCENT)
    draw.text((wx + 235, wy + 114), "Guitarra Principal", font=FONT_BOLD, fill=CYAN_ACCENT)
    
    # Dificuldade
    draw.text((wx + 400, wy + 116), "Dificuldade:", font=FONT_BOLD, fill=TEXT_MUTED)
    draw.rounded_rectangle([(wx + 490, wy + 107), (wx + 590, wy + 138)], radius=5, fill=(35, 40, 65, 255), outline=BORDER_COLOR)
    draw.text((wx + 505, wy + 114), "Expert (V)", font=FONT_BOLD, fill=TEXT_WHITE)
    
    # Zoom
    draw.text((wx + 610, wy + 116), "Zoom: 100%", font=FONT_SMALL, fill=TEXT_MUTED)
    draw.rounded_rectangle([(wx + 690, wy + 107), (wx + 740, wy + 138)], radius=5, fill=(45, 55, 80, 255))
    draw.text((wx + 705, wy + 114), "+ / -", font=FONT_BOLD, fill=TEXT_WHITE)
    
    # Canvas da Timeline / Mini-Reaper
    canvas_rect = [(wx + 20, wy + 155), (wx + ww - 20, wy + 480)]
    draw.rounded_rectangle(canvas_rect, radius=8, fill=(12, 14, 22, 255), outline=CYAN_ACCENT, width=2)
    
    # Régua de tempo superior
    draw.rectangle([(wx + 20, wy + 155), (wx + ww - 20, wy + 185)], fill=(20, 24, 38, 255))
    draw.line([(wx + 20, wy + 185), (wx + ww - 20, wy + 185)], fill=BORDER_COLOR, width=1)
    
    for m in range(1, 9):
        mx = wx + 110 + (m - 1) * 85
        draw.line([(mx, wy + 155), (mx, wy + 480)], fill=(35, 40, 60, 255), width=1)
        draw.text((mx + 4, wy + 162), f"Bar {m} (00:0{m * 2})", font=FONT_SMALL, fill=CYAN_ACCENT)
        
    lane_colors = [GREEN_ACCENT, RED_ACCENT, AMBER_ACCENT, BLUE_ACCENT, ORANGE_ACCENT]
    lane_names = ["G (Verde)", "R (Vermelho)", "Y (Amarelo)", "B (Azul)", "O (Laranja)"]
    
    for i in range(5):
        ly = wy + 205 + i * 50
        draw.line([(wx + 20, ly), (wx + ww - 20, ly)], fill=(28, 32, 50, 255), width=1)
        draw.text((wx + 24, ly - 10), lane_names[i], font=FONT_SMALL, fill=lane_colors[i])
        
    note_samples = [
        (1, 0, 40), (1, 1, 40),   # Acorde Verde + Vermelho
        (2, 2, 60),               # Sustentação Amarela
        (3, 3, 30), (3, 4, 30),   # Acorde Azul + Laranja
        (4, 0, 30), (4.5, 1, 30), (5, 2, 30), (5.5, 3, 30), (6, 4, 50), # Escada
        (7, 0, 35), (7, 2, 35), (7, 4, 35) # Tríade G-Y-O
    ]
    for bar, lane, length in note_samples:
        nx = wx + 110 + int((bar - 1) * 85)
        ny = wy + 205 + lane * 50 - 10
        col = lane_colors[lane]
        draw.rounded_rectangle([(nx, ny), (nx + length, ny + 20)], radius=4, fill=col, outline=(255, 255, 255, 200), width=1)
        
    # Cursor de Reprodução
    playhead_x = wx + 310
    draw.line([(playhead_x, wy + 155), (playhead_x, wy + 480)], fill=(239, 68, 68, 255), width=3)
    draw.polygon([(playhead_x - 8, wy + 155), (playhead_x + 8, wy + 155), (playhead_x, wy + 168)], fill=(239, 68, 68, 255))
    
    # Barra de Dicas de Edição Manual
    draw.rounded_rectangle([(wx + 20, wy + 495), (wx + ww - 20, wy + 610)], radius=8, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 35, wy + 508), "Como Adicionar / Remover Notas Manualmente:", font=FONT_BOLD, fill=TEXT_WHITE)
    draw.text((wx + 35, wy + 533), "- Clique com o Botao Esquerdo na linha desejada para criar uma nova nota.", font=FONT_REGULAR, fill=TEXT_MUTED)
    draw.text((wx + 35, wy + 555), "- Clique com o Botao Direito sobre qualquer nota existente para exclui-la.", font=FONT_REGULAR, fill=TEXT_MUTED)
    draw.text((wx + 35, wy + 578), "- Pressione Barra de Espaco para dar Play / Pause e ouvir a musica sincronizada.", font=FONT_REGULAR, fill=CYAN_ACCENT)

    # Callouts
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Regua e Cursor de Tempo",
                     "A agulha vermelha acompanha a musica em tempo real quando voce da Play para conferir a sincronia.", CYAN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "As 5 Pistas de Cores",
                     "Exatamente como no Reaper ou no jogo: Verde, Vermelho, Amarelo, Azul e Laranja com acordes e sustentacoes.", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Trilha de Vocal com Letra",
                     "Selecione 'Vocais' no seletor para ver as palavras da letra escritas sob cada nota afinada.", PURPLE_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "Edicao Facil com o Mouse",
                     "Clique esquerdo cria nota, clique direito apaga. Sem menus complicados nem atalhos dificeis de memorizar.", AMBER_ACCENT)

    draw_badge(draw, playhead_x, wy + 140, 1, CYAN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + ww - 50, wy + 250, 2, GREEN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + 395, wy + 120, 3, PURPLE_ACCENT, (255, 255, 255, 255))

    img.save(output_path)
    print(f"Gerado: {output_path}")


# ==============================================================================
# 6. ABA 4 - METADADOS E CAPA DO ÁLBUM
# ==============================================================================
def generate_06_metadados_e_capa(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 06 • METADADOS, CAPA DO ALBUM E DIFICULDADES", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "Aba 4: Personalize como a musica aparecera na tela de selecao do jogo e no menu", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "Estudio de Criacao • Aba 4: Metadados & Capa")
    
    # Aba ativa
    draw.rounded_rectangle([(wx + 430, wy + 55), (wx + 580, wy + 90)], radius=6, fill=CYAN_ACCENT)
    draw.text((wx + 445, wy + 65), "4. Metadados", font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    # Coluna Esquerda - Campos de Texto
    col_w = 460
    fields = [
        ("Titulo da Musica:", "Sweet Child O' Mine"),
        ("Artista / Banda:", "Guns N' Roses"),
        ("Album:", "Appetite for Destruction"),
        ("Ano de Lancamento:", "1987"),
        ("Genero Musical:", "Classic Rock"),
    ]
    for i, (lbl, val) in enumerate(fields):
        fy = wy + 110 + i * 65
        draw.text((wx + 35, fy), lbl, font=FONT_BOLD, fill=TEXT_WHITE)
        draw.rounded_rectangle([(wx + 35, fy + 22), (wx + 35 + col_w, fy + 54)], radius=5, fill=BG_DARK, outline=BORDER_COLOR)
        draw.text((wx + 45, fy + 30), val, font=FONT_REGULAR, fill=CYAN_ACCENT)
        
    draw.text((wx + 35, wy + 440), "Dificuldades no Menu do Jogo (1 a 6 Pontos):", font=FONT_BOLD, fill=TEXT_WHITE)
    diffs = [("Guitarra:", "[5/6] Muito Dificil"), ("Baixo:", "[3/6] Medio"), ("Bateria:", "[4/6] Dificil"), ("Vocal:", "[4/6] Dificil")]
    for i, (inst, stars) in enumerate(diffs):
        dx = wx + 35 + (i % 2) * 230
        dy = wy + 470 + (i // 2) * 35
        draw.text((dx, dy), f"{inst} {stars}", font=FONT_REGULAR, fill=AMBER_ACCENT)
        
    draw.rounded_rectangle([(wx + 35, wy + 550), (wx + 35 + col_w, wy + 605)], radius=6, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 45, wy + 560), "ID do Rock Band (Song ID Automatico):", font=FONT_SMALL, fill=TEXT_MUTED)
    draw.text((wx + 45, wy + 580), "ID Unico Gerado: 13374289 (Evita conflitos no jogo)", font=FONT_BOLD, fill=GREEN_ACCENT)
    
    # Coluna Direita - Capa do Álbum
    art_x = wx + 520
    art_y = wy + 110
    draw.text((art_x, art_y), "Capa do Album:", font=FONT_BOLD, fill=TEXT_WHITE)
    
    art_box = [(art_x, art_y + 30), (art_x + 240, art_y + 270)]
    draw.rounded_rectangle(art_box, radius=10, fill=(15, 18, 28, 255), outline=CYAN_ACCENT, width=2)
    
    draw.ellipse([(art_x + 40, art_y + 70), (art_x + 200, art_y + 230)], fill=(30, 35, 55, 255), outline=AMBER_ACCENT, width=3)
    draw.ellipse([(art_x + 95, art_y + 125), (art_x + 145, art_y + 175)], fill=(15, 18, 28, 255), outline=BORDER_COLOR, width=2)
    draw.text((art_x + 65, art_y + 145), "MIDGUITAR", font=FONT_BOLD, fill=TEXT_WHITE)
    
    btn_capa = [(art_x, art_y + 290), (art_x + 240, art_y + 330)]
    draw.rounded_rectangle(btn_capa, radius=6, fill=(45, 55, 85, 255), outline=CYAN_ACCENT)
    draw.text((art_x + 35, art_y + 302), "Escolher Imagem...", font=FONT_BOLD, fill=TEXT_WHITE)
    draw.text((art_x, art_y + 345), "Formatos: .JPG, .PNG\nRedimensionado para 512x512", font=FONT_SMALL, fill=TEXT_MUTED)

    # Callouts
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Informacoes da Musica",
                     "Nome, Artista e Ano aparecem exatamente assim na tela do videogame e no menu de escolha.", CYAN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "Capa do Album",
                     "Suba qualquer imagem quadrada. Ela e convertida automaticamente no formato correto que o jogo le.", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Dificuldade em Estrelas",
                     "Define os pontinhos de dificuldade que aparecem ao lado de cada instrumento na tela de selecao.", AMBER_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "Song ID Automatico",
                     "O MidGuitar cria um ID numerico unico para que sua musica nunca sobrescreva outras musicas do jogo.", PURPLE_ACCENT)

    draw_badge(draw, wx + col_w + 10, wy + 160, 1, CYAN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, art_x + 220, art_y + 20, 2, GREEN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + col_w + 10, wy + 460, 3, AMBER_ACCENT, (0, 0, 0, 255))

    img.save(output_path)
    print(f"Gerado: {output_path}")


# ==============================================================================
# 7. ABA 5 - EXPORTAÇÃO PARA JOGOS
# ==============================================================================
def generate_07_exportacao_jogos(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 07 • EXPORTACAO DIRETA PARA OS VIDEOGAMES", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "Aba 5: Escolha o jogo de destino e gere o pacote final sem precisar de nenhum outro programa", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "Estudio de Criacao • Aba 5: Exportar Pacotes")
    
    # Aba ativa
    draw.rounded_rectangle([(wx + 580, wy + 55), (wx + 720, wy + 90)], radius=6, fill=CYAN_ACCENT)
    draw.text((wx + 605, wy + 65), "5. Exportar", font=FONT_BOLD, fill=(10, 15, 30, 255))
    
    platforms = [
        ("PlayStation 3 (Pacote PKG / RPCS3)",
         "Gera o arquivo instalavel .PKG e pasta NPEB... pronta.\n"
         "Basta colocar na raiz do pendrive FAT32 e instalar no PS3 (CFW/HEN)\n"
         "ou arrastar direto para dentro do emulador RPCS3 no PC!",
         CYAN_ACCENT, True),
        ("Clone Hero / YARG (Pasta de Musica)",
         "Gera a pasta pronta contendo notes.chart, song.ini e audio.\n"
         "Basta copiar ou mover para a pasta 'Songs' do seu Clone Hero\n"
         "e clicar em 'Scan Songs' no jogo para tocar imediatamente!",
         GREEN_ACCENT, False),
        ("Rock Band 3 (Formato CON / Xbox 360)",
         "Gera a estrutura oficial com songs.dta multitrack, MIDI e audio.\n"
         "Compativel com pendrive de Xbox 360 e emulador Xenia\n"
         "ou para bibliotecas personalizadas de Rock Band 3.",
         AMBER_ACCENT, False)
    ]
    
    for i, (title, desc, color, selected) in enumerate(platforms):
        py = wy + 110 + i * 135
        pw = ww - 60
        ph = 120
        draw.rounded_rectangle([(wx + 30, py), (wx + 30 + pw, py + ph)], radius=10, fill=BG_DARK, outline=color, width=2 if selected else 1)
        
        rx, ry = wx + 55, py + 25
        draw.ellipse([(rx - 10, ry - 10), (rx + 10, ry + 10)], outline=color, width=2)
        if selected:
            draw.ellipse([(rx - 5, ry - 5), (rx + 5, ry + 5)], fill=color)
            
        draw.text((rx + 20, ry - 10), title, font=FONT_BOLD, fill=TEXT_WHITE)
        
        for l_idx, line in enumerate(desc.split("\n")):
            draw.text((rx + 20, ry + 18 + l_idx * 18), line, font=FONT_SMALL, fill=TEXT_MUTED)
            
    # Seletor de Pasta de Saída
    draw.rounded_rectangle([(wx + 30, wy + 525), (wx + ww - 30, wy + 565)], radius=6, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 45, wy + 535), "Pasta de Destino: C:/MidGuitar/MinhasMusicasExportadas/", font=FONT_REGULAR, fill=TEXT_WHITE)
    draw.rounded_rectangle([(wx + ww - 180, wy + 529), (wx + ww - 35, wy + 561)], radius=5, fill=(45, 55, 80, 255))
    draw.text((wx + ww - 165, wy + 536), "Alterar Pasta...", font=FONT_SMALL, fill=CYAN_ACCENT)
    
    # Botão Final de Exportar
    btn_export = [(wx + 30, wy + 575), (wx + ww - 30, wy + 620)]
    draw.rounded_rectangle(btn_export, radius=8, fill=CYAN_ACCENT)
    draw.text((wx + 200, wy + 586), "EXPORTAR PACOTE FINAL COM 1 CLIQUE!", font=FONT_SUBTITLE, fill=(10, 15, 30, 255))

    # Callouts
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Escolha Seu Jogo",
                     "Selecione PlayStation 3 para jogar no console ou emulador, ou Clone Hero para tocar no PC.", CYAN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "Sem Programas Extras",
                     "Antes voce precisava do Magma v2, C3 CON Tools e Onyx. Agora o MidGuitar faz tudo direto!", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Para o Pendrive do PS3",
                     "O arquivo PKG sai pronto. Copie para a raiz de um pendrive FAT32, espete no PS3 e instale em 'Package Manager'.", AMBER_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "Exportacao Rapida",
                     "Leva menos de 10 segundos para gerar todos os arquivos sincronizados e compilados.", PURPLE_ACCENT)

    draw_badge(draw, wx + ww - 60, wy + 130, 1, CYAN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + ww - 60, wy + 595, 4, CYAN_ACCENT, (0, 0, 0, 255))

    img.save(output_path)
    print(f"Gerado: {output_path}")


# ==============================================================================
# 8. MODO AO VIVO - TOCAR COM TECLADO, GUITARRA E VOCAL
# ==============================================================================
def generate_08_modo_ao_vivo(output_path):
    img, draw = create_base_canvas()
    
    draw.text((40, 20), "TUTORIAL 08 • TOCAR AO VIVO E TESTAR A MUSICA", font=FONT_TITLE, fill=CYAN_ACCENT)
    draw.text((40, 52), "Como testar e se divertir tocando pelo teclado do PC ou conectando qualquer instrumento USB", font=FONT_REGULAR, fill=TEXT_MUTED)
    
    wx, wy, ww, wh = 40, 90, 820, 630
    draw_window_frame(draw, wx, wy, ww, wh, "MidGuitar • Modo Performance ao Vivo & Mapeamento de Teclas")
    
    card_w = (ww - 70) // 2
    
    # Card 1: Teclado de Digitação
    c1_rect = [(wx + 25, wy + 60), (wx + 25 + card_w, wy + 350)]
    draw.rounded_rectangle(c1_rect, radius=10, fill=BG_DARK, outline=CYAN_ACCENT, width=2)
    draw.text((wx + 45, wy + 75), "Tocar pelo Teclado do Computador", font=FONT_BOLD, fill=CYAN_ACCENT)
    draw.text((wx + 45, wy + 100), "Mapeamento padrao personalizavel:", font=FONT_SMALL, fill=TEXT_MUTED)
    
    keys_map = [
        ("Verde (Traste 1):", "Tecla 1  ou  F1  ou  A"),
        ("Vermelho (Traste 2):", "Tecla 2  ou  F2  ou  S"),
        ("Amarelo (Traste 3):", "Tecla 3  ou  F3  ou  J"),
        ("Azul (Traste 4):", "Tecla 4  ou  F4  ou  K"),
        ("Laranja (Traste 5):", "Tecla 5  ou  F5  ou  L"),
        ("Palheta (Strum):", "Barra de ESPACO ou Enter"),
        ("Overdrive / Whammy:", "Tecla SHIFT ou PageUp")
    ]
    for i, (traste, tecla) in enumerate(keys_map):
        ky = wy + 130 + i * 30
        draw.text((wx + 45, ky), traste, font=FONT_REGULAR, fill=TEXT_WHITE)
        draw.text((wx + 200, ky), tecla, font=FONT_BOLD, fill=AMBER_ACCENT if i == 5 else GREEN_ACCENT)
        
    # Card 2: Guitarra / Instrumento USB
    c2_rect = [(wx + 45 + card_w, wy + 60), (wx + 45 + card_w * 2, wy + 350)]
    draw.rounded_rectangle(c2_rect, radius=10, fill=BG_DARK, outline=PURPLE_ACCENT, width=2)
    draw.text((wx + 65 + card_w, wy + 75), "Tocar com Guitarra ou Joystick USB", font=FONT_BOLD, fill=PURPLE_ACCENT)
    draw.text((wx + 65 + card_w, wy + 100), "Conecte e toque imediatamente:", font=FONT_SMALL, fill=TEXT_MUTED)
    
    usb_features = [
        ("- Guitarras de PS3 / PS4:", "Plug & Play automatico sem driver"),
        ("- Guitarras de Xbox 360 / One:", "Suporte nativo XInput"),
        ("- Guitarras de Wii (com adaptador):", "Mapeamento automatico de botoes"),
        ("- Teclado Musical MIDI USB:", "Toca notas reais no canal Piano/Keys"),
        ("- Microfone USB:", "Captacao de tom e afinacao para o vocal"),
        ("- Baixa Latencia:", "Sintetizador de audio ultra-rapido")
    ]
    for i, (feat, desc) in enumerate(usb_features):
        fy = wy + 135 + i * 32
        draw.text((wx + 65 + card_w, fy), feat, font=FONT_BOLD, fill=TEXT_WHITE)
        draw.text((wx + 65 + card_w, fy + 16), desc, font=FONT_SMALL, fill=TEXT_MUTED)
        
    # Painel Inferior: Highway / Teste ao Vivo
    draw.rounded_rectangle([(wx + 25, wy + 370), (wx + ww - 25, wy + 610)], radius=10, fill=BG_DARK, outline=BORDER_COLOR)
    draw.text((wx + 45, wy + 385), "Feedback Visual em Tempo Real:", font=FONT_BOLD, fill=TEXT_WHITE)
    draw.text((wx + 45, wy + 408), "Pressione as teclas para ver as luzes acenderem e ouvir o som exato da nota:", font=FONT_SMALL, fill=TEXT_MUTED)
    
    fret_feedback = [
        ("VERDE", GREEN_ACCENT, True),
        ("VERMELHO", RED_ACCENT, False),
        ("AMARELO", AMBER_ACCENT, True),
        ("AZUL", BLUE_ACCENT, False),
        ("LARANJA", ORANGE_ACCENT, False),
    ]
    for i, (name, col, active) in enumerate(fret_feedback):
        fx = wx + 55 + i * 145
        fy = wy + 440
        draw.rounded_rectangle([(fx, fy), (fx + 125, fy + 80)], radius=10, fill=col if active else (25, 30, 45, 255), outline=col, width=3)
        status = "ACESO!" if active else "Pronto"
        text_c = (10, 15, 30, 255) if active else TEXT_MUTED
        draw.text((fx + 25, fy + 20), name, font=FONT_BOLD, fill=text_c)
        draw.text((fx + 35, fy + 48), status, font=FONT_SMALL, fill=text_c)
        
    draw.rounded_rectangle([(wx + 55, wy + 540), (wx + ww - 55, wy + 590)], radius=8, fill=(35, 45, 75, 255), outline=CYAN_ACCENT)
    draw.text((wx + 180, wy + 555), "PALHETADA DETECTADA • NOTA TOCADA COM SUCESSO!", font=FONT_BOLD, fill=CYAN_ACCENT)

    # Callouts
    cx, cy, cw = 880, 90, 360
    draw_callout_box(draw, cx, cy, cw, 120, 1, "Voce Escolhe Como Tocar",
                     "Nao tem instrumento? Use as teclas do teclado do computador. Se tiver guitarra USB, ela funciona direto!", CYAN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 135, cw, 120, 2, "Palheta Realista",
                     "Voce pode segurar o traste (1, 2, 3...) e bater o espaco para simular a palhetada exata de uma guitarra.", GREEN_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 270, cw, 120, 3, "Teste Imediato",
                     "Depois de criar a musica, toque-a aqui mesmo para sentir se o ritmo e as notas ficaram divertidos.", AMBER_ACCENT)
                     
    draw_callout_box(draw, cx, cy + 405, cw, 120, 4, "Configuracao Total",
                     "Quer mudar as teclas para outras letras? Voce pode remapear 100% dos botoes nas configuracoes.", PURPLE_ACCENT)

    draw_badge(draw, wx + card_w, wy + 70, 1, CYAN_ACCENT, (0, 0, 0, 255))
    draw_badge(draw, wx + ww - 40, wy + 70, 2, PURPLE_ACCENT, (255, 255, 255, 255))
    draw_badge(draw, wx + ww - 40, wy + 385, 3, GREEN_ACCENT, (0, 0, 0, 255))

    img.save(output_path)
    print(f"Gerado: {output_path}")


def main():
    out_dir = os.path.join("assets", "tutorial")
    os.makedirs(out_dir, exist_ok=True)
    
    generate_01_tela_principal(os.path.join(out_dir, "01_tela_principal.png"))
    generate_02_estudio_navegacao_geral(os.path.join(out_dir, "02_estudio_navegacao_geral.png"))
    generate_03_importacao_audio(os.path.join(out_dir, "03_importacao_audio.png"))
    generate_04_auto_chart_e_letras(os.path.join(out_dir, "04_auto_chart_e_letras.png"))
    generate_05_mini_reaper_edicao(os.path.join(out_dir, "05_mini_reaper_edicao.png"))
    generate_06_metadados_e_capa(os.path.join(out_dir, "06_metadados_e_capa.png"))
    generate_07_exportacao_jogos(os.path.join(out_dir, "07_exportacao_jogos.png"))
    generate_08_modo_ao_vivo(os.path.join(out_dir, "08_modo_ao_vivo.png"))
    print("\nTodas as 8 telas visuais do tutorial foram geradas com sucesso em assets/tutorial/!")

if __name__ == "__main__":
    main()
