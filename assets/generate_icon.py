from PIL import Image, ImageDraw

def create_guitar_icon(output_path: str):
    # Cria uma imagem 256x256 com fundo escuro e detalhes de guitarra
    size = (256, 256)
    img = Image.new("RGBA", size, (15, 23, 42, 255)) # Slate 900
    draw = ImageDraw.Draw(img)

    # Borda externa azul ciano
    draw.rounded_rectangle([(8, 8), (248, 248)], radius=48, outline=(56, 189, 248, 255), width=8)

    # 5 linhas de cordas horizontais
    colors = [
        (34, 197, 94, 255),   # Verde
        (239, 68, 68, 255),   # Vermelho
        (234, 179, 8, 255),   # Amarelo
        (59, 130, 246, 255),  # Azul
        (249, 115, 22, 255),  # Laranja
    ]
    
    y_positions = [60, 95, 130, 165, 200]
    for i, (y, col) in enumerate(zip(y_positions, colors)):
        # Traste/linha
        draw.line([(40, y), (216, y)], fill=(71, 85, 105, 255), width=4)
        # Marcador circular de casa
        draw.ellipse([(108 + (i - 2) * 24, y - 10), (128 + (i - 2) * 24, y + 10)], fill=col)

    # Salva como .ico em múltiplos tamanhos
    img.save(output_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print(f"Icone gerado com sucesso em: {output_path}")

if __name__ == "__main__":
    create_guitar_icon("assets/icon.ico")
