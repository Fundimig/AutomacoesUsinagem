import serial
import cv2
import numpy as np
from pathlib import Path

# ======================================
# CONFIG
# ======================================

PORTA = "COM4"
BAUD = 921600

# ======================================

dataset = Path("dataset")

classe_atual = "peca_a"

for pasta in [
    "peca_a",
    "peca_b",
    "peca_c",
    "peca_d"
]:
    (dataset / pasta).mkdir(
        parents=True,
        exist_ok=True
    )

# ======================================

ser = serial.Serial(
    PORTA,
    BAUD,
    timeout=15
)

print("Conectado.")

# ======================================

def proximo_nome():

    pasta = dataset / classe_atual

    arquivos = list(
        pasta.glob("foto*.jpg")
    )

    numero = len(arquivos) + 1

    return pasta / f"foto{numero:04d}.jpg"

# ======================================

while True:

    cmd = input(
        f"\n[{classe_atual}] A/B/C/D troca classe | ENTER fotografa | Q sai > "
    ).strip().upper()

    if cmd == "Q":
        break

    if cmd == "A":
        classe_atual = "peca_a"
        continue

    if cmd == "B":
        classe_atual = "peca_b"
        continue

    if cmd == "C":
        classe_atual = "peca_c"
        continue

    if cmd == "D":
        classe_atual = "peca_d"
        continue

    # limpa buffer antigo

    ser.reset_input_buffer()

    # pede foto ao ESP

    ser.write(b"F")

    print("Aguardando imagem...")

    tamanho = None

    while True:

        linha = ser.readline() \
            .decode(errors="ignore") \
            .strip()

        if linha.startswith("IMG:"):

            tamanho = int(
                linha.replace(
                    "IMG:",
                    ""
                )
            )

            break

    print(
        f"JPEG: {tamanho} bytes"
    )

    dados = bytearray()

    while len(dados) < tamanho:

        restante = tamanho - len(dados)

        bloco = ser.read(
            min(
                restante,
                4096
            )
        )

        if len(bloco) == 0:
            print("Timeout")
            break

        dados.extend(bloco)

        print(
            f"\rRecebido {len(dados)} / {tamanho}",
            end=""
        )

    print()

    if len(dados) != tamanho:
        print("Imagem incompleta")
        continue

    imagem = cv2.imdecode(
        np.frombuffer(
            dados,
            dtype=np.uint8
        ),
        cv2.IMREAD_COLOR
    )

    if imagem is None:
        print("Erro decodificando JPEG")
        continue

    nome = proximo_nome()

    cv2.imwrite(
        str(nome),
        imagem
    )

    cv2.imshow(
        "ESP32-CAM",
        imagem
    )

    cv2.waitKey(1)

    print(
        f"Salvo: {nome}"
    )

ser.close()

cv2.destroyAllWindows()