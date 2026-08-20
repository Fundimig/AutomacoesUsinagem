import ctypes
import time

# Biblioteca de joystick do Windows
winmm = ctypes.windll.winmm


class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_uint),
        ("dwFlags", ctypes.c_uint),
        ("dwXpos", ctypes.c_uint),
        ("dwYpos", ctypes.c_uint),
        ("dwZpos", ctypes.c_uint),
        ("dwRpos", ctypes.c_uint),
        ("dwUpos", ctypes.c_uint),
        ("dwVpos", ctypes.c_uint),
        ("dwButtons", ctypes.c_uint),
        ("dwButtonNumber", ctypes.c_uint),
        ("dwPOV", ctypes.c_uint),
        ("dwReserved1", ctypes.c_uint),
        ("dwReserved2", ctypes.c_uint),
    ]


JOY_RETURNBUTTONS = 0x00000080

info = JOYINFOEX()
info.dwSize = ctypes.sizeof(JOYINFOEX)
info.dwFlags = JOY_RETURNBUTTONS

ultimo_estado = 0

print("Aguardando botoes do ZL-9019...")
print("Ctrl+C para sair.\n")

while True:
    resultado = winmm.joyGetPosEx(0, ctypes.byref(info))

    if resultado == 0:

        estado = info.dwButtons

        if estado != ultimo_estado:

            for botao in range(32):

                mascara = 1 << botao

                antes = ultimo_estado & mascara
                agora = estado & mascara

                if agora and not antes:
                    print(f"Botao {botao + 1} PRESSIONADO")

                elif antes and not agora:
                    print(f"Botao {botao + 1} SOLTO")

            ultimo_estado = estado

    else:
        print("Controle nao encontrado.")
        time.sleep(1)

    time.sleep(0.01)