"""
Gerador e Leitor Nativo de Arquivos .MOGG (Multitrack Ogg Harmonix) e Analisador de Áudio.
Implementa a especificação binária oficial do ogg2mogg (cabeçalho 0x0A + Seek Table de 20.000 samples)
para que o Rock Band 3 (PS3, RPCS3 e Xbox 360) reproduza qualquer MP3, WAV, FLAC ou OGG perfeitamente!
Também extrai áudio de arquivos .mogg importados de pacotes de fãs e analisa BPM e energia real do áudio.
"""

import os
import struct
import shutil
import tempfile
import numpy as np

SEEK_INCREMENT = 0x8000      # 32768 bytes por bloco de busca
FRAME_INCREMENT = 20000      # 20000 samples por entrada na tabela MOGG


def is_mogg_file(filepath: str) -> bool:
    """Verifica se o arquivo possui o cabeçalho binário 0x0A de um MOGG não criptografado."""
    if not filepath or not os.path.exists(filepath):
        return False
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
            if len(header) < 8:
                return False
            magic, offset = struct.unpack("<II", header)
            return magic == 0x0A and 20 <= offset < os.path.getsize(filepath)
    except Exception:
        return False


def extraction_cache_dir(source_dir: str) -> str:
    """Pasta temporária (uma por pasta de origem) para áudios extraídos de .mogg.
    Evita gravar arquivos *_extracted.ogg ao lado dos originais do usuário."""
    import hashlib
    key = hashlib.md5(os.path.abspath(source_dir).encode("utf-8")).hexdigest()[:12]
    cache = os.path.join(tempfile.gettempdir(), "midguitar_cache", key)
    os.makedirs(cache, exist_ok=True)
    return cache


def extract_ogg_from_mogg(mogg_path: str, output_ogg_path: str = None) -> str:
    """
    Remove o cabeçalho Harmonix 0x0A de um arquivo .mogg e salva o stream .ogg puro
    para que o Pygame e o analisador de áudio possam reproduzi-lo no Mini-REAPER.
    """
    if not is_mogg_file(mogg_path):
        return mogg_path

    if output_ogg_path is None:
        base_dir = extraction_cache_dir(os.path.dirname(os.path.abspath(mogg_path)))
        base_name = os.path.splitext(os.path.basename(mogg_path))[0]
        output_ogg_path = os.path.join(base_dir, f"{base_name}_extracted.ogg")

    if os.path.exists(output_ogg_path) and os.path.getsize(output_ogg_path) > 1024:
        return output_ogg_path

    try:
        with open(mogg_path, "rb") as fin:
            header = fin.read(8)
            magic, ogg_offset = struct.unpack("<II", header)
            fin.seek(ogg_offset)
            with open(output_ogg_path, "wb") as fout:
                shutil.copyfileobj(fin, fout, length=65536)
        return output_ogg_path
    except Exception as e:
        print(f"[MoggGenerator] Erro ao extrair OGG de MOGG: {e}")
        return mogg_path


def get_ogg_codec(path: str) -> str:
    """
    Identifica o codec de um arquivo Ogg lendo a primeira página:
    "vorbis" (\x01vorbis), "opus" (OpusHead), "other" (flac/speex...) ou "" se não for Ogg.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(512)
    except Exception:
        return ""
    if head[:4] != b"OggS":
        return ""
    if b"vorbis" in head:
        return "vorbis"
    if b"OpusHead" in head:
        return "opus"
    return "other"


def is_vorbis_ogg(path: str) -> bool:
    """True se o arquivo é um Ogg Vorbis (o único formato Ogg que o Rock Band toca)."""
    return get_ogg_codec(path) == "vorbis"


def convert_audio_to_ogg(source_path: str, target_ogg_path: str) -> bool:
    """
    Converte qualquer arquivo de áudio (.mp3, .wav, .flac, .ogg, .mogg) para OGG Vorbis padrão.
    """
    if not source_path or not os.path.exists(source_path):
        return False

    # Se já for .mogg, extrai a parte .ogg
    if is_mogg_file(source_path):
        extracted = extract_ogg_from_mogg(source_path, target_ogg_path)
        return os.path.exists(extracted)

    # Já é Ogg Vorbis: só copia. Ogg com Opus (ou outro codec) é decodificado e regravado
    # como Vorbis abaixo, porque o Rock Band não toca Opus dentro do .mogg.
    try:
        if is_vorbis_ogg(source_path):
            if os.path.abspath(source_path) != os.path.abspath(target_ogg_path):
                shutil.copy2(source_path, target_ogg_path)
            return True
    except Exception:
        pass

    # Converte usando soundfile (libsndfile) em blocos de 65536 frames (evita crash do Vorbis em arquivos longos!)
    try:
        import soundfile as sf
        with sf.SoundFile(source_path, "r") as fin:
            samplerate = fin.samplerate
            with sf.SoundFile(target_ogg_path, "w", samplerate=samplerate, channels=2, format="OGG", subtype="VORBIS") as fout:
                while True:
                    chunk = fin.read(65536, dtype="float32", always_2d=True)
                    if len(chunk) == 0:
                        break
                    if chunk.shape[1] == 1:
                        chunk = np.repeat(chunk, 2, axis=1)
                    elif chunk.shape[1] > 2:
                        chunk = chunk[:, :2]
                    fout.write(chunk)
        return os.path.exists(target_ogg_path)
    except Exception as e:
        print(f"[MoggGenerator] Erro ao converter {source_path} para OGG via soundfile: {e}")
        return False


def _parse_ogg_pages(ogg_path: str):
    """
    Lê as páginas 'OggS' de um arquivo OGG Vorbis para obter (byte_offset, granule_sample_pos)
    e o total de samples e bytes do stream.
    """
    pages = []  # lista de (byte_offset, granule_position)
    total_bytes = os.path.getsize(ogg_path)
    max_samples = 0

    try:
        with open(ogg_path, "rb") as f:
            data = f.read()

        pos = 0
        data_len = len(data)
        while pos + 27 <= data_len:
            idx = data.find(b"OggS", pos)
            if idx == -1 or idx + 27 > data_len:
                break

            # Estrutura do cabeçalho OggS:
            # 0..4: "OggS"
            # 4: version (0)
            # 5: header_type
            # 6..14: granule_position (int64 LE)
            # 26: page_segments (uint8)
            granule_pos = struct.unpack_from("<q", data, idx + 6)[0]
            num_segments = data[idx + 26]
            seg_table_end = idx + 27 + num_segments
            if seg_table_end > data_len:
                break

            body_size = sum(data[idx + 27 : seg_table_end])
            if granule_pos >= 0:
                pages.append((idx, granule_pos))
                if granule_pos > max_samples:
                    max_samples = granule_pos

            pos = seg_table_end + body_size
    except Exception as e:
        print(f"[MoggGenerator] Aviso ao mapear páginas OggS: {e}")

    if max_samples <= 0:
        # Fallback aproximado (44100 Hz)
        max_samples = max(44100, int((total_bytes / 16000.0) * 44100))

    return pages, total_bytes, max_samples


def create_unencrypted_mogg(source_audio_path: str, target_mogg_path: str) -> bool:
    """
    Gera um arquivo .mogg oficial (cabeçalho 0x0A + Seek Table + stream Ogg Vorbis)
    a partir de qualquer arquivo de áudio (.mp3, .wav, .ogg, .flac, .mogg).
    Segue exatamente a implementação de referência do ogg2mogg (onyxite).
    """
    if not source_audio_path or not os.path.exists(source_audio_path):
        return False

    # Se a origem já for um .mogg válido, basta copiar
    if is_mogg_file(source_audio_path):
        if os.path.abspath(source_audio_path) != os.path.abspath(target_mogg_path):
            shutil.copy2(source_audio_path, target_mogg_path)
        return True

    temp_ogg = None
    try:
        # Só Ogg Vorbis é usado direto; Opus e demais formatos são convertidos para um OGG temporário
        is_ogg = is_vorbis_ogg(source_audio_path)

        if is_ogg:
            ogg_path = source_audio_path
        else:
            fd, temp_ogg = tempfile.mkstemp(suffix=".ogg")
            os.close(fd)
            if not convert_audio_to_ogg(source_audio_path, temp_ogg):
                return False
            ogg_path = temp_ogg

        pages, total_bytes, total_samples = _parse_ogg_pages(ogg_path)

        # 1. Para cada incremento de 0x8000 bytes no OGG, descobre a posição em samples
        seek_entries = (total_bytes + (SEEK_INCREMENT - 1)) // SEEK_INCREMENT
        seek_table = []
        page_idx = 0
        num_pages = len(pages)

        for i in range(seek_entries):
            target_byte = i * SEEK_INCREMENT
            while page_idx + 1 < num_pages and pages[page_idx + 1][0] <= target_byte:
                page_idx += 1
            sample_pos = pages[page_idx][1] if num_pages > 0 else 0
            seek_table.append(max(0, int(sample_pos)))

        # 2. Para cada bloco de 20.000 samples, mapeia (bytes_offset, sample_offset)
        mogg_entries = max(1, int((total_samples + (FRAME_INCREMENT - 1)) // FRAME_INCREMENT))
        mogg_table_bytes = []
        mogg_table_samples = []

        for i in range(mogg_entries):
            desired_pos = i * FRAME_INCREMENT
            curr_bytes = 0
            curr_samples = 0
            for j in range(seek_entries):
                if seek_table[j] <= desired_pos:
                    curr_bytes = j * SEEK_INCREMENT
                    curr_samples = seek_table[j]
                else:
                    break
            mogg_table_bytes.append(curr_bytes)
            mogg_table_samples.append(curr_samples)

        # 3. Escreve cabeçalho 0x0A + Seek Table + Stream OGG
        ogg_start_offset = 20 + 8 * mogg_entries
        with open(target_mogg_path, "wb") as mogg_out:
            mogg_out.write(struct.pack(
                "<IIIII",
                0x0A,               # Magic: unencrypted MOGG
                ogg_start_offset,   # Offset onde começa o OggS
                0x10,               # Versão da Seek Table
                FRAME_INCREMENT,    # 20000 samples por entrada
                mogg_entries        # Quantidade de entradas na tabela
            ))
            for b_off, s_off in zip(mogg_table_bytes, mogg_table_samples):
                mogg_out.write(struct.pack("<II", b_off, s_off))

            with open(ogg_path, "rb") as ogg_in:
                shutil.copyfileobj(ogg_in, mogg_out, length=65536)

        return os.path.exists(target_mogg_path)
    except Exception as e:
        print(f"[MoggGenerator] Erro ao gerar .mogg: {e}")
        return False
    finally:
        if temp_ogg and os.path.exists(temp_ogg):
            try:
                os.remove(temp_ogg)
            except Exception:
                pass


def analyze_audio_file(audio_path: str) -> dict:
    """
    Analisa a forma de onda real do arquivo de áudio (.mp3, .wav, .ogg, .flac, .mogg)
    e retorna:
    - duration_ms: duração exata em milissegundos
    - bpm: BPM estimado pelos transientes rítmicos (entre 75 e 175 BPM)
    - first_sound_ms: início real da música (ignorando silêncio inicial)
    - last_sound_ms: fim real da música (ignorando silêncio final)
    - energy_windows: lista de energias normalizadas (0.0 a 1.0) a cada 500ms
    """
    result = {
        "duration_ms": 180000,
        "bpm": 120.0,
        "first_sound_ms": 1000,
        "last_sound_ms": 176000,
        "energy_windows": []
    }
    if not audio_path or not os.path.exists(audio_path):
        return result

    play_path = extract_ogg_from_mogg(audio_path) if is_mogg_file(audio_path) else audio_path

    try:
        import soundfile as sf
        info = sf.info(play_path)
        sr = info.samplerate
        total_frames = info.frames
        duration_sec = total_frames / float(sr) if sr > 0 else 180.0
        result["duration_ms"] = max(5000, int(duration_sec * 1000))
        result["last_sound_ms"] = max(2000, result["duration_ms"] - 2000)

        # Envelope de energia RMS com passo de 10 ms (100 Hz). A resolução fina é o que
        # permite estimar o BPM com precisão (com 50 ms, 128 BPM virava 133).
        hop_ms = 10
        hop_frames = max(1, int(round(sr * hop_ms / 1000.0)))
        energies = []
        block_hops = 200  # lê 2 s por vez e reparte em passos de 10 ms
        with sf.SoundFile(play_path, "r") as f:
            while True:
                chunk = f.read(hop_frames * block_hops, dtype="float32", always_2d=True)
                if len(chunk) == 0:
                    break
                mono_sq = np.mean(chunk.astype(np.float64) ** 2, axis=1)
                full = (len(mono_sq) // hop_frames) * hop_frames
                if full:
                    energies.extend(np.sqrt(mono_sq[:full].reshape(-1, hop_frames).mean(axis=1)))
                if full < len(mono_sq):
                    energies.append(float(np.sqrt(mono_sq[full:].mean())))

        if not energies:
            return result

        env = np.array(energies, dtype=np.float32)
        max_rms = float(np.max(env)) if np.max(env) > 1e-6 else 1.0
        norm_env = env / max_rms

        # Detecta início e fim do som real (threshold de 4% da energia máxima)
        active_indices = np.where(norm_env > 0.04)[0]
        if len(active_indices) > 0:
            result["first_sound_ms"] = int(active_indices[0] * hop_ms)
            result["last_sound_ms"] = min(result["duration_ms"] - 500, int(active_indices[-1] * hop_ms))

        # Agrega em janelas de 500ms (50 blocos de 10ms) para perfil de energia da música
        win_size = 500 // hop_ms
        num_wins = len(norm_env) // win_size
        if num_wins > 0:
            reshaped = norm_env[:num_wins * win_size].reshape(num_wins, win_size)
            result["energy_windows"] = [float(np.mean(w)) for w in reshaped]

        # Estimativa de BPM por autocorrelação do envelope de ataque (onset strength)
        onset = np.maximum(0.0, np.diff(norm_env, prepend=norm_env[0]))
        if len(onset) > 500:
            # Usa trecho central da música (até 60 segundos) para estimar BPM
            mid_start = len(onset) // 4
            mid_slice = onset[mid_start : min(len(onset), mid_start + 6000)]
            mid_slice = mid_slice - np.mean(mid_slice)
            corr = np.correlate(mid_slice, mid_slice, mode="full")
            corr = corr[len(corr) // 2 :]

            # Lags em blocos de 10ms: 175 BPM = 0.343s ~ 35 blocos | 80 BPM = 0.75s = 75 blocos
            min_lag = 35
            max_lag = min(75, len(corr) - 2)
            if max_lag > min_lag:
                best_lag = min_lag + int(np.argmax(corr[min_lag : max_lag + 1]))
                # Interpolação parabólica em torno do pico (precisão sub-bloco)
                y0, y1, y2 = corr[best_lag - 1], corr[best_lag], corr[best_lag + 1]
                denom = y0 - 2.0 * y1 + y2
                shift = 0.5 * (y0 - y2) / denom if abs(denom) > 1e-12 else 0.0
                lag = best_lag + max(-1.0, min(1.0, float(shift)))
                est_bpm = 60.0 / (lag * hop_ms / 1000.0)
                # Arredonda para BPM musical inteiro próximo
                result["bpm"] = float(round(max(75.0, min(175.0, est_bpm))))
    except Exception as e:
        print(f"[MoggGenerator] Aviso ao analisar áudio {audio_path}: {e}")

    return result
