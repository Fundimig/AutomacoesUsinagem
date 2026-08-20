import sys
import ctypes
import time
from threading import Thread
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import (
    Qt,
    QTimer,
    QRegularExpression,
    QSize,
    QObject,
    Signal,
)
from PySide6.QtGui import (
    QPixmap,
    QShortcut,
    QKeySequence,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QInputDialog,
    QSizePolicy,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QStyle,
)


# ============================================================
# CONFIGURAÇÕES / ARQUIVOS
# ============================================================

ARQUIVO_CODIGO = "codigo.txt"
ARQUIVO_CONTADOR_DIA = "contador_dia.txt"
ARQUIVO_CONTADOR_CODIGO = "contador_codigo.txt"
ARQUIVO_CONTADOR_BOSCH = "contador_bosch127.txt"

ARQUIVO_LOG = "historico.log"
ARQUIVO_DATA = "data_contador.txt"
ARQUIVO_HISTORICO_PRODUCAO = "producao_diaria.csv"
ARQUIVO_PROGRAMA_ATUAL = "programa_atual.txt"

PASTA_PROGRAMAS = r"C:\Programas marcação a laser"


# ============================================================
# PROGRAMAS COM CÓDIGO FIXO / AUTOMÁTICO
# ============================================================

PROGRAMAS_AUTOMATICOS = [
    "BOSCH127",
    "BOSCH127.EZD",
]


# ============================================================
# CORES
# ============================================================

LARANJA = "#FFA500"
PRETO = "#000000"
BRANCO = "#FFFFFF"

CINZA_ESCURO = "#2B2B2B"
CINZA_MEDIO = "#808080"
CINZA_CLARO = "#CCCCCC"

AZUL = "#00D4FF"
AZUL_ESCURO = "#003A75"

VERDE = "#28A745"
VERDE_CLARO = "#6CFF8B"

AMARELO = "#FFC107"
VERMELHO = "#AA0000"

CINZA_ESCURO_TELA = "#1f2937"


# ============================================================
# CONTROLADOR USB ZL-9019 / JOYSTICK HID (WINDOWS WINMM)
# ============================================================

# O Windows mostra os botões começando em 1.
# Internamente o WinMM usa bits começando em 0.
ZL_JOYSTICK_ID = 0

BOTAO_FIM_CURSO = 1
BOTAO_START = 2
BOTAO_STOP = 3

INTERVALO_LEITURA_ZL_MS = 10
DEBOUNCE_ZL_MS = 40

JOY_RETURNBUTTONS = 0x00000080
MMSYSERR_NOERROR = 0


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


class LeitorZL9019(QObject):
    """
    Lê o ZL-9019 diretamente pelo WinMM do Windows.

    Não precisa de pygame nem de outra biblioteca externa.
    Faz debounce em software antes de emitir os eventos.
    """

    botao_pressionado = Signal(int)
    botao_solto = Signal(int)
    conexao_alterada = Signal(bool)
    estado_atualizado = Signal(int)

    def __init__(
        self,
        joystick_id=ZL_JOYSTICK_ID,
        debounce_ms=DEBOUNCE_ZL_MS,
        parent=None,
    ):

        super().__init__(parent)

        self.joystick_id = joystick_id
        self.debounce_ms = debounce_ms

        self._conectado = False
        self._ultimo_raw = 0
        self._estado_estavel = 0
        self._mudanca_raw_em = {}

        self._info = JOYINFOEX()
        self._info.dwSize = ctypes.sizeof(JOYINFOEX)
        self._info.dwFlags = JOY_RETURNBUTTONS

        self._winmm = None

        if sys.platform == "win32":

            try:
                self._winmm = ctypes.windll.winmm
            except Exception:
                self._winmm = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._ler)

    def iniciar(self):

        self._timer.start(
            INTERVALO_LEITURA_ZL_MS
        )

    def parar(self):

        self._timer.stop()

    def _definir_conectado(self, conectado):

        if conectado == self._conectado:
            return

        self._conectado = conectado
        self.conexao_alterada.emit(
            conectado
        )

    def _ler(self):

        if self._winmm is None:
            self._definir_conectado(False)
            return

        self._info.dwSize = ctypes.sizeof(JOYINFOEX)
        self._info.dwFlags = JOY_RETURNBUTTONS

        resultado = self._winmm.joyGetPosEx(
            self.joystick_id,
            ctypes.byref(self._info),
        )

        if resultado != MMSYSERR_NOERROR:

            self._definir_conectado(False)

            self._ultimo_raw = 0
            self._estado_estavel = 0
            self._mudanca_raw_em.clear()

            return

        self._definir_conectado(True)

        agora = time.monotonic()
        raw = int(self._info.dwButtons)

        # O ZL-9019 normalmente expõe poucos botões,
        # mas o WinMM permite até 32 bits neste campo.
        for indice in range(32):

            mascara = 1 << indice

            raw_ativo = bool(
                raw & mascara
            )

            raw_anterior = bool(
                self._ultimo_raw & mascara
            )

            estavel_ativo = bool(
                self._estado_estavel & mascara
            )

            if raw_ativo != raw_anterior:

                self._mudanca_raw_em[indice] = agora

            if raw_ativo == estavel_ativo:
                continue

            inicio = self._mudanca_raw_em.get(
                indice,
                agora,
            )

            tempo_estavel_ms = (
                (agora - inicio) * 1000.0
            )

            if tempo_estavel_ms < self.debounce_ms:
                continue

            numero_botao = indice + 1

            if raw_ativo:

                self._estado_estavel |= mascara

                self.botao_pressionado.emit(
                    numero_botao
                )

            else:

                self._estado_estavel &= ~mascara

                self.botao_solto.emit(
                    numero_botao
                )

        self._ultimo_raw = raw

        # Envia continuamente para a IHM o estado ESTÁVEL
        # dos botões. Isso é especialmente importante para o
        # fim de curso, que é um estado mantido e não um pulso.
        self.estado_atualizado.emit(
            int(self._estado_estavel)
        )


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def codigo_valido(codigo):
    """
    Verifica se o código possui exatamente
    6 letras ASCII, sem números ou símbolos.
    """

    codigo = codigo.strip()

    return (
        len(codigo) == 6
        and codigo.isascii()
        and codigo.isalpha()
    )


def ler_inteiro_seguro(nome_arquivo, padrao=0):
    """
    Lê um contador inteiro.

    Caso o arquivo não exista, esteja vazio
    ou corrompido, retorna o valor padrão.
    """

    arquivo = Path(nome_arquivo)

    try:
        if not arquivo.exists():
            arquivo.write_text(
                str(padrao),
                encoding="utf-8",
            )
            return padrao

        texto = arquivo.read_text(
            encoding="utf-8"
        ).strip()

        if not texto:
            arquivo.write_text(
                str(padrao),
                encoding="utf-8",
            )
            return padrao

        return int(texto)

    except (ValueError, OSError):
        try:
            arquivo.write_text(
                str(padrao),
                encoding="utf-8",
            )
        except OSError:
            pass

        return padrao


# ============================================================
# ARQUIVOS
# ============================================================

def ler_codigo():
    arquivo = Path(ARQUIVO_CODIGO)

    if not arquivo.exists():
        arquivo.write_text(
            "",
            encoding="utf-8",
        )
        return ""

    try:
        return arquivo.read_text(
            encoding="utf-8"
        ).strip()

    except OSError:
        return ""


def salvar_codigo(codigo):
    Path(
        ARQUIVO_CODIGO
    ).write_text(
        codigo,
        encoding="utf-8",
    )


def ler_contador_dia():
    return ler_inteiro_seguro(
        ARQUIVO_CONTADOR_DIA
    )


def salvar_contador_dia(valor):
    Path(
        ARQUIVO_CONTADOR_DIA
    ).write_text(
        str(valor),
        encoding="utf-8",
    )


def ler_contador_codigo():
    return ler_inteiro_seguro(
        ARQUIVO_CONTADOR_CODIGO
    )


def salvar_contador_codigo(valor):
    Path(
        ARQUIVO_CONTADOR_CODIGO
    ).write_text(
        str(valor),
        encoding="utf-8",
    )


def ler_contador_bosch127():
    return ler_inteiro_seguro(
        ARQUIVO_CONTADOR_BOSCH
    )


def salvar_contador_bosch127(valor):
    Path(
        ARQUIVO_CONTADOR_BOSCH
    ).write_text(
        str(valor),
        encoding="utf-8",
    )


# ============================================================
# RESET DIÁRIO
# ============================================================

def verificar_reset_diario():
    """
    Verifica o reset diário durante a inicialização.

    A verificação contínua enquanto a IHM estiver
    aberta é feita dentro da JanelaPrincipal.
    """

    hoje = datetime.now().strftime(
        "%d/%m/%Y"
    )

    arquivo = Path(
        ARQUIVO_DATA
    )

    try:
        if not arquivo.exists():

            arquivo.write_text(
                hoje,
                encoding="utf-8",
            )

            return

        ultima_data = arquivo.read_text(
            encoding="utf-8"
        ).strip()

        if ultima_data != hoje:

            salvar_contador_dia(0)

            arquivo.write_text(
                hoje,
                encoding="utf-8",
            )

    except OSError:
        pass


# ============================================================
# HISTÓRICO DE PRODUÇÃO
# ============================================================

def incrementar_producao_codigo(
    codigo,
    incremento=1,
):
    """
    Incrementa a produção diária de um código.

    IMPORTANTE:
    Diferente da versão anterior, esta função
    NÃO substitui a quantidade anterior.

    Exemplo:

    AMNLOK já tinha 152 peças.

    Depois produz mais uma.

    Resultado:
    153

    e não:
    1
    """

    hoje = datetime.now().strftime(
        "%d/%m/%Y"
    )

    arquivo = Path(
        ARQUIVO_HISTORICO_PRODUCAO
    )

    registros = {}

    if arquivo.exists():

        try:

            with arquivo.open(
                "r",
                encoding="utf-8",
            ) as f:

                for linha in f:

                    linha = linha.strip()

                    if not linha:
                        continue

                    partes = linha.split(";")

                    if len(partes) != 3:
                        continue

                    data, cod, qtd = partes

                    try:
                        quantidade = int(qtd)
                    except ValueError:
                        quantidade = 0

                    registros[
                        (data, cod)
                    ] = quantidade

        except OSError:
            pass

    chave = (
        hoje,
        codigo,
    )

    quantidade_atual = registros.get(
        chave,
        0,
    )

    nova_quantidade = (
        quantidade_atual
        + incremento
    )

    registros[chave] = nova_quantidade

    with arquivo.open(
        "w",
        encoding="utf-8",
    ) as f:

        for (
            data,
            cod,
        ), quantidade in registros.items():

            f.write(
                f"{data};"
                f"{cod};"
                f"{quantidade}\n"
            )

    return nova_quantidade


# ============================================================
# PROGRAMAS
# ============================================================

def listar_programas_ezd():

    pasta = Path(
        PASTA_PROGRAMAS
    )

    if not pasta.exists():
        return []

    return sorted(
        [
            arquivo.name
            for arquivo in pasta.glob("*.ezd")
            if arquivo.is_file()
        ],
        key=str.casefold,
    )


def ler_programa_atual():

    arquivo = Path(
        ARQUIVO_PROGRAMA_ATUAL
    )

    if not arquivo.exists():

        arquivo.write_text(
            "",
            encoding="utf-8",
        )

        return ""

    try:

        return arquivo.read_text(
            encoding="utf-8"
        ).strip()

    except OSError:

        return ""


def salvar_programa_atual(nome):

    Path(
        ARQUIVO_PROGRAMA_ATUAL
    ).write_text(
        nome,
        encoding="utf-8",
    )


def obter_caminho_programa(nome):

    return (
        Path(PASTA_PROGRAMAS)
        / nome
    )


# ============================================================
# LOG
# ============================================================

def registrar_alteracao(
    antigo,
    novo,
):

    agora = datetime.now()

    texto = f"""

{agora.strftime('%d/%m/%Y %H:%M:%S')}

ANTIGO:
{antigo}

NOVO:
{novo}

------------------------------------

"""

    with open(
        ARQUIVO_LOG,
        "a",
        encoding="utf-8",
    ) as arquivo:

        arquivo.write(
            texto
        )


def registrar_troca_programa(
    antigo,
    novo,
):

    agora = datetime.now()

    texto = f"""

{agora.strftime('%d/%m/%Y %H:%M:%S')}

TROCA DE PROGRAMA

ANTIGO:
{antigo}

NOVO:
{novo}

------------------------------------

"""

    with open(
        ARQUIVO_LOG,
        "a",
        encoding="utf-8",
    ) as arquivo:

        arquivo.write(
            texto
        )


def registrar_erro_horus(
    programa,
    mensagem,
):

    agora = datetime.now()

    texto = f"""

{agora.strftime('%d/%m/%Y %H:%M:%S')}

ERRO AO TROCAR PROGRAMA NO HORUS

PROGRAMA:
{programa}

ERRO:
{mensagem}

------------------------------------

"""

    with open(
        ARQUIVO_LOG,
        "a",
        encoding="utf-8",
    ) as arquivo:

        arquivo.write(
            texto
        )


# ============================================================
# HORUS / PYWINAUTO
# ============================================================

def carregar_programa_ezd(
    nome_programa,
):

    log_path = Path(
        "debug_horus.log"
    )

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as log_fh:

        def log(msg):

            agora = datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            )

            mensagem = (
                f"[{agora}] {msg}"
            )

            print(
                mensagem
            )

            log_fh.write(
                mensagem + "\n"
            )

            log_fh.flush()

        try:

            log(
                "PASSO 1 - Importando pywinauto"
            )

            from pywinauto import Desktop

            log(
                "PASSO 2 - Procurando HORUS"
            )

            horus = Desktop(
                backend="win32"
            ).window(
                title_re=".*HORUS.*"
            )

            # Garante que a janela realmente existe.
            horus.wait(
                "exists",
                timeout=5,
            )

            log(
                "PASSO 3 - Janela encontrada: "
                f"{horus.window_text()}"
            )

            menu_items = (
                horus.menu_items()
            )

            programa_sem_extensao = (
                Path(nome_programa)
                .stem
                .upper()
            )

            log(
                "PASSO 4 - Procurando "
                f"{programa_sem_extensao}"
            )

            caminho_menu = None

            for item in menu_items:

                if item.get(
                    "text"
                ) != "Arquivo":

                    continue

                submenu = (
                    item.get(
                        "menu_items",
                        {},
                    )
                    .get(
                        "menu_items",
                        [],
                    )
                )

                for subitem in submenu:

                    texto = subitem.get(
                        "text",
                        "",
                    )

                    if (
                        programa_sem_extensao
                        in texto.upper()
                    ):

                        caminho_menu = (
                            f"Arquivo->{texto}"
                        )

                        break

                if caminho_menu:
                    break

            if not caminho_menu:

                log(
                    "PROGRAMA NÃO ESTÁ "
                    "NA LISTA DE RECENTES"
                )

                return (
                    False,
                    "PROGRAMA NÃO ENCONTRADO "
                    "NO MENU HORUS",
                )

            log(
                "PASSO 5 - Executando: "
                f"{caminho_menu}"
            )

            horus.menu_select(
                caminho_menu
            )

            log(
                "PASSO 6 - Comando enviado ao HORUS"
            )

            # Tenta devolver o foco para a IHM.
            try:

                janelas = Desktop(
                    backend="win32"
                ).windows()

                for janela in janelas:

                    try:

                        if (
                            janela.window_text()
                            == "Rastreabilidade Laser"
                        ):

                            janela.set_focus()

                            break

                    except Exception:
                        pass

            except Exception as e:

                log(
                    "Falha ao devolver foco: "
                    f"{e}"
                )

            log(
                "PASSO 7 - PROGRAMA CARREGADO"
            )

            return (
                True,
                "PROGRAMA CARREGADO",
            )

        except Exception as e:

            import traceback

            traceback.print_exc()

            log(
                f"ERRO HORUS: {e}"
            )

            return (
                False,
                f"ERRO: {e}",
            )


# ============================================================
# PONTE ENTRE THREAD DO HORUS E QT
# ============================================================

class PonteHorus(QObject):

    resultado_carregamento = Signal(
        bool,
        str,
        str,
    )


# ============================================================
# DIALOG - SELEÇÃO DE PROGRAMA
# ============================================================

class SeletorProgramaDialog(QDialog):

    def __init__(
        self,
        parent,
        programas,
        selecionado,
    ):

        super().__init__(
            parent
        )

        self.setWindowTitle(
            "Trocar Programa"
        )

        self.setModal(
            True
        )

        self.setMinimumSize(
            900,
            700,
        )

        self.setStyleSheet(
            f"""
            QDialog{{
                background:{CINZA_ESCURO_TELA};
                color:white;
            }}
            """
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            30,
            30,
            30,
        )

        layout.setSpacing(
            20
        )

        titulo = QLabel(
            "SELECIONE O PROGRAMA"
        )

        titulo.setAlignment(
            Qt.AlignCenter
        )

        titulo.setStyleSheet(
            f"""
            color:{BRANCO};
            font-size:32px;
            font-weight:bold;
            """
        )

        layout.addWidget(
            titulo
        )

        self.lista = QListWidget()

        self.lista.setStyleSheet(
            f"""
            QListWidget{{
                background:{CINZA_ESCURO};
                border:2px solid {CINZA_CLARO};
                border-radius:18px;
                color:{BRANCO};
                font-size:28px;
            }}

            QListWidget::item{{
                min-height:70px;
                padding:20px;
                text-align:center;
            }}

            QListWidget::item:selected{{
                background:{AZUL};
                color:{PRETO};
                border-radius:12px;
            }}
            """
        )

        self.lista.setUniformItemSizes(
            True
        )

        self.lista.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        self.lista.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        for programa in programas:

            item = QListWidgetItem(
                programa
            )

            item.setTextAlignment(
                Qt.AlignCenter
            )

            item.setSizeHint(
                QSize(
                    0,
                    80,
                )
            )

            self.lista.addItem(
                item
            )

        if selecionado in programas:

            self.lista.setCurrentRow(
                programas.index(
                    selecionado
                )
            )

        lista_container = (
            QHBoxLayout()
        )

        lista_container.addStretch(
            1
        )

        lista_container.addWidget(
            self.lista,
            2,
        )

        lista_container.addStretch(
            1
        )

        layout.addLayout(
            lista_container
        )

        botoes = QHBoxLayout()

        botoes.setSpacing(
            30
        )

        botoes.addStretch(
            1
        )

        self.btn_ok = QPushButton(
            "OK"
        )

        self.btn_ok.setFixedHeight(
            70
        )

        self.btn_ok.setStyleSheet(
            f"""
            QPushButton{{
                background:{VERDE};
                color:{PRETO};
                font-size:28px;
                font-weight:bold;
                border-radius:14px;
                padding:10px 30px;
            }}

            QPushButton:pressed{{
                background:{AZUL_ESCURO};
            }}
            """
        )

        self.btn_ok.clicked.connect(
            self._aceitar
        )

        botoes.addWidget(
            self.btn_ok
        )

        self.btn_cancelar = QPushButton(
            "CANCELAR"
        )

        self.btn_cancelar.setFixedHeight(
            70
        )

        self.btn_cancelar.setStyleSheet(
            f"""
            QPushButton{{
                background:{AMARELO};
                color:{PRETO};
                font-size:28px;
                font-weight:bold;
                border-radius:14px;
                padding:10px 30px;
            }}

            QPushButton:pressed{{
                background:{CINZA_MEDIO};
            }}
            """
        )

        self.btn_cancelar.clicked.connect(
            self.reject
        )

        botoes.addWidget(
            self.btn_cancelar
        )

        botoes.addStretch(
            1
        )

        layout.addLayout(
            botoes
        )

        QShortcut(
            QKeySequence("Return"),
            self,
            activated=self._aceitar,
        )

        QShortcut(
            QKeySequence("Enter"),
            self,
            activated=self._aceitar,
        )

    def _aceitar(self):

        if (
            self.lista.currentRow()
            >= 0
        ):

            self.accept()

    def selected_programa(self):

        item = (
            self.lista.currentItem()
        )

        return (
            item.text()
            if item
            else None
        )


# ============================================================
# DIALOG - AVISO DE FOCO
# ============================================================

class AvisoFocoDialog(QDialog):

    def __init__(
        self,
        parent,
    ):

        super().__init__(
            parent
        )

        self.setWindowTitle(
            "ATENÇÃO"
        )

        self.setModal(
            True
        )

        self.setMinimumSize(
            900,
            700,
        )

        self.setStyleSheet(
            f"""
            QDialog{{
                background:{CINZA_ESCURO};
                color:white;
            }}
            """
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            40,
            40,
            40,
            40,
        )

        layout.setSpacing(
            20
        )

        top = QHBoxLayout()

        top.setSpacing(
            20
        )

        top.addStretch(
            1
        )

        icone_label = QLabel()

        icone = self.style().standardIcon(
            QStyle.SP_MessageBoxWarning
        )

        icone_label.setPixmap(
            icone.pixmap(
                90,
                90,
            )
        )

        top.addWidget(
            icone_label,
            alignment=Qt.AlignCenter,
        )

        titulo = QLabel(
            "ATENÇÃO"
        )

        titulo.setAlignment(
            Qt.AlignCenter
        )

        titulo.setStyleSheet(
            f"""
            color:{AMARELO};
            font-size:48px;
            font-weight:bold;
            """
        )

        top.addWidget(
            titulo
        )

        top.addStretch(
            1
        )

        layout.addLayout(
            top
        )

        mensagem = QLabel(
            "PROGRAMA ALTERADO.\n\n"
            "ANTES DE INICIAR A MARCAÇÃO:\n\n"
            "🎯 CONFIRMAR O FOCO DO LASER\n"
            "🧩 CONFIRMAR O POSICIONAMENTO DA PEÇA\n"
            "💾 CONFIRMAR O PROGRAMA SELECIONADO\n\n"
            "Pressione ENTER para continuar."
        )

        mensagem.setAlignment(
            Qt.AlignCenter
        )

        mensagem.setWordWrap(
            True
        )

        mensagem.setStyleSheet(
            f"""
            color:{BRANCO};
            font-size:28px;
            """
        )

        layout.addWidget(
            mensagem,
            alignment=Qt.AlignCenter,
        )

        self.btn_continuar = QPushButton(
            "ENTER PARA CONTINUAR"
        )

        self.btn_continuar.setFixedHeight(
            80
        )

        self.btn_continuar.setStyleSheet(
            f"""
            QPushButton{{
                background:{AMARELO};
                color:{PRETO};
                font-size:30px;
                font-weight:bold;
                border-radius:16px;
                padding:12px 30px;
            }}

            QPushButton:pressed{{
                background:{VERDE};
            }}
            """
        )

        self.btn_continuar.clicked.connect(
            self.accept
        )

        botao_layout = QHBoxLayout()

        botao_layout.addStretch(
            1
        )

        botao_layout.addWidget(
            self.btn_continuar
        )

        botao_layout.addStretch(
            1
        )

        layout.addLayout(
            botao_layout
        )

        QShortcut(
            QKeySequence("Return"),
            self,
            activated=self.accept,
        )

        QShortcut(
            QKeySequence("Enter"),
            self,
            activated=self.accept,
        )


# ============================================================
# TELA PRINCIPAL
# ============================================================

class JanelaPrincipal(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint
        )

        self.setWindowTitle(
            "Rastreabilidade Laser"
        )

        # ----------------------------------------------------
        # RESET / CONTADORES
        # ----------------------------------------------------

        verificar_reset_diario()

        self.contador_dia = (
            ler_contador_dia()
        )

        self.contador_codigo = (
            ler_contador_codigo()
        )

        self.contador_bosch = (
            ler_contador_bosch127()
        )

        self.data_referencia = (
            datetime.now().date()
        )

        # ----------------------------------------------------
        # ESTADOS INTERNOS
        # ----------------------------------------------------

        self.modo_edicao = False

        self.ciclo_em_andamento = False

        self.troca_programa_em_andamento = False

        self.programa_pendente = ""

        self.preview_pixmap = None

        self.peca_pixmap = None

        # ----------------------------------------------------
        # ESTADOS DO ZL-9019 / INTERTRAVAMENTO
        # ----------------------------------------------------

        self.zl_conectado = False
        self.fim_curso_ativo = False
        self.stop_acionado = False

        # Depois de um ciclo aceito, uma nova marcação só é
        # liberada após o fim de curso abrir e fechar novamente.
        # Isso evita marcar a mesma peça duas vezes por engano.
        self.aguardando_retirada_peca = False

        # ----------------------------------------------------
        # HORUS - SIGNAL
        # ----------------------------------------------------

        self.ponte_horus = PonteHorus(
            self
        )

        self.ponte_horus.resultado_carregamento.connect(
            self.finalizar_troca_programa
        )

        # ----------------------------------------------------
        # PROGRAMAS
        # ----------------------------------------------------

        self.programas_ezd = (
            listar_programas_ezd()
        )

        self.programa_atual = (
            ler_programa_atual()
        )

        codigo_salvo = (
            ler_codigo()
        )

        if (
            codigo_salvo
            and not codigo_valido(
                codigo_salvo
            )
        ):

            codigo_salvo = ""

        self.codigo_inicial = (
            ""
            if (
                self.programa_atual.upper()
                in PROGRAMAS_AUTOMATICOS
            )
            else codigo_salvo
        )

        # ----------------------------------------------------
        # ESTILO GERAL
        # ----------------------------------------------------

        self.setStyleSheet(
            f"""
            QWidget{{
                background:{CINZA_ESCURO};
                color:white;
            }}
            """
        )

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        # ----------------------------------------------------
        # PULSO STATUS
        # ----------------------------------------------------

        self.pulso_status = True

        self.timer_pulso = QTimer(
            self
        )

        self.timer_pulso.timeout.connect(
            self.animar_status
        )

        self.timer_pulso.start(
            500
        )

        # ====================================================
        # LAYOUT PRINCIPAL
        # ====================================================

        layout = QVBoxLayout()

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(
            0
        )

        # ====================================================
        # CABEÇALHO
        # ====================================================

        cabecalho_widget = QWidget()

        cabecalho = QHBoxLayout(
            cabecalho_widget
        )

        cabecalho.setContentsMargins(
            20,
            10,
            20,
            10,
        )

        cabecalho.setSpacing(
            20
        )

        self.logo = QLabel()

        pixmap = QPixmap(
            "assets/logo-fundimig.png"
        )

        if not pixmap.isNull():

            self.logo.setPixmap(
                pixmap.scaled(
                    180,
                    70,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        titulo = QLabel(
            "SISTEMA DE RASTREABILIDADE"
        )

        titulo.setAlignment(
            Qt.AlignCenter
        )

        titulo.setStyleSheet(
            """
            font-size:40px;
            font-weight:bold;
            """
        )

        self.relogio = QLabel()

        self.relogio.setAlignment(
            Qt.AlignRight
        )

        self.relogio.setStyleSheet(
            """
            font-size:24px;
            font-weight:bold;
            """
        )

        cabecalho.addWidget(
            self.logo
        )

        cabecalho.addStretch(
            1
        )

        cabecalho.addWidget(
            titulo,
            alignment=Qt.AlignCenter,
        )

        cabecalho.addStretch(
            1
        )

        cabecalho.addWidget(
            self.relogio
        )

        layout.addWidget(
            cabecalho_widget
        )

        # ====================================================
        # CONTEÚDO PRINCIPAL
        # ====================================================

        conteudo_principal = (
            QHBoxLayout()
        )

        # ====================================================
        # LADO ESQUERDO
        # ====================================================

        lado_esquerdo = (
            QVBoxLayout()
        )

        self.lbl_codigo = QLabel(
            "CÓDIGO ATUAL"
        )

        self.lbl_codigo.setAlignment(
            Qt.AlignCenter
        )

        self.lbl_codigo.setStyleSheet(
            f"""
            color:{CINZA_CLARO};
            font-size:28px;
            """
        )

        lado_esquerdo.addWidget(
            self.lbl_codigo
        )

        # ----------------------------------------------------
        # CÓDIGO
        # ----------------------------------------------------

        self.codigo = QLineEdit(
            self.codigo_inicial
        )

        self.codigo.setAlignment(
            Qt.AlignCenter
        )

        self.codigo.setReadOnly(
            True
        )

        self.codigo.setMaxLength(
            6
        )

        regex = QRegularExpression(
            "[A-Za-z]{0,6}"
        )

        validador = (
            QRegularExpressionValidator(
                regex
            )
        )

        self.codigo.setValidator(
            validador
        )

        self.codigo.textChanged.connect(
            self.converter_maiusculo
        )

        self.codigo.setStyleSheet(
            f"""
            QLineEdit{{
                background:transparent;
                border:none;
                color:{AZUL};
                font-size:150px;
                font-weight:bold;
            }}
            """
        )

        self.codigo.setMaximumHeight(
            220
        )

        self.codigo.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        lado_esquerdo.addWidget(
            self.codigo
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        self.status = QLabel(
            "🟢 PRONTO PARA MARCAR"
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        self.status.setStyleSheet(
            f"""
            color:{VERDE};
            font-size:32px;
            font-weight:bold;
            """
        )

        self.status.setMaximumHeight(
            90
        )

        self.status.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        lado_esquerdo.addWidget(
            self.status
        )

        # ----------------------------------------------------
        # INDICADOR FÍSICO DO FIM DE CURSO
        # ----------------------------------------------------

        self.lbl_fim_curso = QLabel(
            "FIM DE CURSO: ABERTO"
        )

        self.lbl_fim_curso.setAlignment(
            Qt.AlignCenter
        )

        self.lbl_fim_curso.setStyleSheet(
            f"""
            QLabel{{
                background:{VERMELHO};
                color:{BRANCO};
                font-size:26px;
                font-weight:bold;
                border-radius:10px;
                padding:10px;
            }}
            """
        )

        self.lbl_fim_curso.setMaximumHeight(
            70
        )

        lado_esquerdo.addWidget(
            self.lbl_fim_curso
        )

        # ----------------------------------------------------
        # CONTADOR CÓDIGO
        # ----------------------------------------------------

        self.texto_contador = QLabel(
            "PEÇAS DESTE CÓDIGO"
        )

        self.texto_contador.setAlignment(
            Qt.AlignCenter
        )

        self.texto_contador.setStyleSheet(
            """
            font-size:24px;
            """
        )

        self.texto_contador.setMaximumHeight(
            50
        )

        self.texto_contador.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.lbl_contador = QLabel(
            str(
                self.contador_codigo
            )
        )

        self.lbl_contador.setAlignment(
            Qt.AlignCenter
        )

        self.lbl_contador.setStyleSheet(
            f"""
            color:{AZUL};
            font-size:60px;
            font-weight:bold;
            """
        )

        self.lbl_contador.setMaximumHeight(
            140
        )

        self.lbl_contador.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        lado_esquerdo.addWidget(
            self.texto_contador
        )

        lado_esquerdo.addWidget(
            self.lbl_contador
        )

        lado_esquerdo.addStretch()

        # ----------------------------------------------------
        # BOTÕES
        # ----------------------------------------------------

        botoes = QHBoxLayout()

        self.btn_confirmar = QPushButton(
            "CONFIRMAR(ENTER)"
        )

        self.btn_confirmar.clicked.connect(
            self.confirmar
        )

        self.btn_confirmar.setStyleSheet(
            f"""
            QPushButton{{
                background:{VERDE};
                color:white;
                font-size:32px;
                font-weight:bold;
                padding:20px;
                border-radius:10px;
            }}

            QPushButton:focus{{
                border:4px solid white;
            }}

            QPushButton:disabled{{
                background:{CINZA_MEDIO};
                color:{CINZA_CLARO};
            }}
            """
        )

        self.btn_alterar = QPushButton(
            "ALTERAR CÓDIGO(F2)"
        )

        self.btn_alterar.clicked.connect(
            self.entrar_modo_edicao
        )

        self.btn_alterar.setStyleSheet(
            f"""
            QPushButton{{
                background:{AMARELO};
                color:black;
                font-size:32px;
                font-weight:bold;
                padding:20px;
                border-radius:10px;
            }}

            QPushButton:disabled{{
                background:{CINZA_MEDIO};
                color:{CINZA_CLARO};
            }}
            """
        )

        botoes.addWidget(
            self.btn_confirmar
        )

        botoes.addWidget(
            self.btn_alterar
        )

        lado_esquerdo.addLayout(
            botoes
        )

        lado_esquerdo.addStretch()

        conteudo_principal.addLayout(
            lado_esquerdo,
            1,
        )

        # ====================================================
        # LADO DIREITO
        # ====================================================

        lado_direito = (
            QVBoxLayout()
        )

        # ----------------------------------------------------
        # PROGRAMA ATUAL
        # ----------------------------------------------------

        linha_programa = (
            QHBoxLayout()
        )

        programa = (
            self.programa_atual
            if self.programa_atual
            else "SEM PROGRAMA SELECIONADO"
        )

        html = (
            f'<span style="color:{CINZA_CLARO}; '
            f'font-size:28px;">'
            f'PROGRAMA ATUAL:</span> '
            f'<span style="color:{AZUL}; '
            f'font-weight:bold; font-size:28px;">'
            f'{programa}</span>'
        )

        self.lbl_programa_nome = QLabel(
            html
        )

        self.lbl_programa_nome.setTextFormat(
            Qt.RichText
        )

        self.lbl_programa_nome.setMaximumHeight(
            80
        )

        self.lbl_programa_nome.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        linha_programa.addStretch()

        linha_programa.addWidget(
            self.lbl_programa_nome
        )

        linha_programa.addStretch()

        lado_direito.addLayout(
            linha_programa
        )

        # ----------------------------------------------------
        # MODO AUTOMÁTICO
        # ----------------------------------------------------

        self.lbl_modo_automatico = QLabel(
            "MODO AUTOMÁTICO - CÓDIGO FIXO"
        )

        self.lbl_modo_automatico.setAlignment(
            Qt.AlignCenter
        )

        self.lbl_modo_automatico.setStyleSheet(
            f"""
            color:{VERDE};
            font-size:24px;
            font-weight:bold;
            """
        )

        self.lbl_modo_automatico.setMaximumHeight(
            70
        )

        self.lbl_modo_automatico.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.lbl_modo_automatico.hide()

        lado_direito.addWidget(
            self.lbl_modo_automatico
        )

        lado_direito.addSpacing(
            0
        )

        # ----------------------------------------------------
        # TROCA + PREVIEW
        # ----------------------------------------------------

        troca_preview_row = (
            QHBoxLayout()
        )

        troca_preview_row.setAlignment(
            Qt.AlignTop
        )

        button_box = (
            QVBoxLayout()
        )

        button_box.setAlignment(
            Qt.AlignVCenter
        )

        self.btn_trocar_programa = QPushButton(
            "TROCAR PROGRAMA (F3)"
        )

        self.btn_trocar_programa.clicked.connect(
            self.trocar_programa
        )

        self.btn_trocar_programa.setFixedSize(
            280,
            70,
        )

        self.btn_trocar_programa.setStyleSheet(
            f"""
            QPushButton{{
                background:{AZUL};
                color:black;
                font-size:22px;
                font-weight:bold;
                border-radius:10px;
            }}

            QPushButton:focus{{
                border:4px solid white;
            }}

            QPushButton:disabled{{
                background:{CINZA_MEDIO};
                color:{CINZA_CLARO};
            }}
            """
        )

        button_box.addWidget(
            self.btn_trocar_programa,
            alignment=Qt.AlignVCenter,
        )

        troca_preview_row.addLayout(
            button_box
        )

        preview_box = (
            QVBoxLayout()
        )

        preview_box.setAlignment(
            Qt.AlignHCenter
            | Qt.AlignVCenter
        )

        lbl_preview = QLabel(
            "PREVIEW DA MARCAÇÃO"
        )

        lbl_preview.setAlignment(
            Qt.AlignHCenter
        )

        lbl_preview.setStyleSheet(
            f"""
            color:{CINZA_CLARO};
            font-size:20px;
            """
        )

        lbl_preview.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Fixed,
        )

        preview_box.addWidget(
            lbl_preview,
            alignment=Qt.AlignHCenter,
        )

        self.preview_area = QLabel(
            "SEM IMAGEM DISPONÍVEL"
        )

        self.preview_area.setAlignment(
            Qt.AlignCenter
        )

        self.preview_area.setWordWrap(
            True
        )

        self.preview_area.setStyleSheet(
            f"""
            color:{BRANCO};
            background:{CINZA_ESCURO};
            border:2px solid {CINZA_CLARO};
            border-radius:6px;
            font-size:21px;
            """
        )

        self.preview_area.setFixedSize(
            140,
            140,
        )

        self.preview_area.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        preview_box.addWidget(
            self.preview_area,
            alignment=Qt.AlignHCenter,
        )

        preview_box.setSpacing(
            8
        )

        troca_preview_row.addLayout(
            preview_box
        )

        troca_preview_row.setAlignment(
            preview_box,
            Qt.AlignVCenter,
        )

        lado_direito.addLayout(
            troca_preview_row
        )

        lado_direito.addSpacing(
            0
        )

        # ----------------------------------------------------
        # POSICIONAMENTO
        # ----------------------------------------------------

        lbl_peca = QLabel(
            "POSICIONAMENTO DA PEÇA"
        )

        lbl_peca.setAlignment(
            Qt.AlignCenter
        )

        lbl_peca.setStyleSheet(
            f"""
            color:{CINZA_CLARO};
            font-size:24px;
            """
        )

        lado_direito.addWidget(
            lbl_peca
        )

        self.peca_area = QLabel(
            "SEM IMAGEM DISPONÍVEL"
        )

        self.peca_area.setAlignment(
            Qt.AlignCenter
        )

        self.peca_area.setWordWrap(
            True
        )

        self.peca_area.setStyleSheet(
            f"""
            color:{BRANCO};
            background:{CINZA_ESCURO};
            border:2px solid {CINZA_CLARO};
            border-radius:12px;
            font-size:20px;
            """
        )

        self.peca_area.setMinimumHeight(
            320
        )

        self.peca_area.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        lado_direito.addWidget(
            self.peca_area
        )

        lado_direito.addStretch()

        conteudo_principal.addLayout(
            lado_direito,
            1,
        )

        conteudo_principal.setStretch(
            0,
            1,
        )

        conteudo_principal.setStretch(
            1,
            1,
        )

        conteudo_principal.setSpacing(
            20
        )

        layout.addLayout(
            conteudo_principal
        )

        layout.setStretch(
            1,
            1,
        )

        layout.addSpacing(
            0
        )

        # ====================================================
        # RODAPÉ
        # ====================================================

        rodape_widget = QWidget()

        rodape = QHBoxLayout(
            rodape_widget
        )

        rodape.setContentsMargins(
            20,
            10,
            20,
            10,
        )

        self.info_rodape = QLabel()

        self.info_rodape.setStyleSheet(
            f"""
            color:{CINZA_CLARO};
            font-size:26px;
            """
        )

        self.info_rodape.setText(
            f"PEÇAS HOJE: "
            f"{self.contador_dia}"
        )

        autor = QLabel(
            "FUNDIMIG\n"
            "SISTEMA DE RASTREABILIDADE\n"
            "v1.0.0"
        )

        autor.setAlignment(
            Qt.AlignRight
        )

        autor.setStyleSheet(
            f"""
            color:{CINZA_MEDIO};
            font-size:16px;
            """
        )

        rodape.addWidget(
            self.info_rodape
        )

        rodape.addStretch()

        rodape.addWidget(
            autor
        )

        layout.addWidget(
            rodape_widget
        )

        self.setLayout(
            layout
        )

        # ====================================================
        # TIMER RELÓGIO
        # ====================================================

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.atualizar_relogio
        )

        self.timer.start(
            1000
        )

        self.atualizar_relogio()

        # ====================================================
        # ATALHOS
        # ====================================================

        self.shortcut_enter = QShortcut(
            QKeySequence("Return"),
            self,
        )

        self.shortcut_enter.activated.connect(
            self.acao_enter
        )

        self.shortcut_enter2 = QShortcut(
            QKeySequence("Enter"),
            self,
        )

        self.shortcut_enter2.activated.connect(
            self.acao_enter
        )

        self.shortcut_f2 = QShortcut(
            QKeySequence("F2"),
            self,
        )

        self.shortcut_f2.activated.connect(
            self.entrar_modo_edicao
        )

        self.shortcut_f3 = QShortcut(
            QKeySequence("F3"),
            self,
        )

        self.shortcut_f3.activated.connect(
            self.trocar_programa
        )

        self.shortcut_escape = QShortcut(
            QKeySequence("Escape"),
            self,
        )

        self.shortcut_escape.activated.connect(
            self.close
        )

        # ====================================================
        # ATUALIZA ESTADO INICIAL
        # ====================================================

        self.atualizar_programa_selecionado(
            self.programa_atual
        )

        # ====================================================
        # CONTROLADOR USB ZL-9019
        # ====================================================

        self.leitor_zl = LeitorZL9019(
            joystick_id=ZL_JOYSTICK_ID,
            debounce_ms=DEBOUNCE_ZL_MS,
            parent=self,
        )

        self.leitor_zl.conexao_alterada.connect(
            self.zl_conexao_alterada
        )

        self.leitor_zl.botao_pressionado.connect(
            self.zl_botao_pressionado
        )

        self.leitor_zl.botao_solto.connect(
            self.zl_botao_solto
        )

        self.leitor_zl.estado_atualizado.connect(
            self.zl_estado_atualizado
        )

        self.leitor_zl.iniciar()

        # Antes da primeira leitura do controlador, mantém
        # o ciclo bloqueado por segurança.
        self.atualizar_habilitacao_controles()
        self.atualizar_status_operacional()

    # ========================================================
    # ZL-9019 / FIM DE CURSO / START / STOP
    # ========================================================

    def pode_iniciar_ciclo(self):

        return (
            self.zl_conectado
            and self.fim_curso_ativo
            and not self.stop_acionado
            and not self.aguardando_retirada_peca
            and not self.ciclo_em_andamento
            and not self.troca_programa_em_andamento
            and not self.modo_edicao
        )

    def zl_conexao_alterada(
        self,
        conectado,
    ):

        self.zl_conectado = conectado

        if not conectado:

            self.fim_curso_ativo = False
            self.stop_acionado = False

        self.atualizar_indicador_fim_curso()
        self.atualizar_habilitacao_controles()
        self.atualizar_status_operacional()

    def zl_estado_atualizado(
        self,
        mascara_botoes,
    ):
        """
        Atualiza continuamente o estado físico do ZL-9019.

        O fim de curso está ligado ao BOTÃO 1. Enquanto o
        contato estiver fechado, o bit permanece ativo.
        """

        mascara_fim_curso = (
            1 << (BOTAO_FIM_CURSO - 1)
        )

        estado_anterior = (
            self.fim_curso_ativo
        )

        self.fim_curso_ativo = bool(
            mascara_botoes
            & mascara_fim_curso
        )

        # Se uma peça já foi confirmada, o sistema só rearma
        # depois que o carro realmente sair do fim de curso.
        if (
            estado_anterior
            and not self.fim_curso_ativo
            and self.aguardando_retirada_peca
        ):
            self.aguardando_retirada_peca = False

        self.atualizar_indicador_fim_curso()

        # Só refaz os controles/status quando houve mudança
        # física, evitando trabalho desnecessário a cada 10 ms.
        if estado_anterior != self.fim_curso_ativo:
            self.atualizar_habilitacao_controles()
            self.atualizar_status_operacional()

    def atualizar_indicador_fim_curso(self):

        if not hasattr(
            self,
            "lbl_fim_curso",
        ):
            return

        if not self.zl_conectado:
            self.lbl_fim_curso.setText(
                "FIM DE CURSO: SEM CONTROLADOR"
            )
            cor = CINZA_MEDIO

        elif self.fim_curso_ativo:
            self.lbl_fim_curso.setText(
                "FIM DE CURSO: ACIONADO ✓"
            )
            cor = VERDE

        else:
            self.lbl_fim_curso.setText(
                "FIM DE CURSO: ABERTO"
            )
            cor = VERMELHO

        self.lbl_fim_curso.setStyleSheet(
            f"""
            QLabel{{
                background:{cor};
                color:{BRANCO};
                font-size:26px;
                font-weight:bold;
                border-radius:10px;
                padding:10px;
            }}
            """
        )

    def zl_botao_pressionado(
        self,
        botao,
    ):

        # BOTÃO 1 = FIM DE CURSO
        if botao == BOTAO_FIM_CURSO:

            self.fim_curso_ativo = True

            self.atualizar_habilitacao_controles()
            self.atualizar_status_operacional()

            return

        # BOTÃO 2 = START
        if botao == BOTAO_START:

            self.start_fisico()

            return

        # BOTÃO 3 = STOP OPERACIONAL
        #
        # IMPORTANTE:
        # isto NÃO é parada de emergência de hardware.
        # Ele apenas bloqueia novos ciclos dentro da IHM.
        if botao == BOTAO_STOP:

            self.stop_acionado = True

            self.atualizar_habilitacao_controles()
            self.atualizar_status_operacional()

    def zl_botao_solto(
        self,
        botao,
    ):

        # Ao retirar a peça, o fim de curso abre e rearma
        # a permissão para uma nova peça.
        if botao == BOTAO_FIM_CURSO:

            self.fim_curso_ativo = False

            if self.aguardando_retirada_peca:
                self.aguardando_retirada_peca = False

            self.atualizar_habilitacao_controles()
            self.atualizar_status_operacional()

            return

        # Por enquanto o STOP é tratado como bloqueio
        # operacional enquanto a botoeira estiver acionada.
        # A função pode ser alterada depois caso o STOP físico
        # seja definido como trava, reset ou outra tarefa.
        if botao == BOTAO_STOP:

            self.stop_acionado = False

            self.atualizar_habilitacao_controles()
            self.atualizar_status_operacional()

    def start_fisico(self):

        if self.troca_programa_em_andamento:
            return

        if self.modo_edicao:

            self.mostrar_erro_temporario(
                "⚠️ FINALIZE A EDIÇÃO DO CÓDIGO"
            )

            return

        # A validação completa, incluindo fim de curso,
        # conexão e STOP, também é refeita em confirmar().
        self.confirmar()

    def atualizar_status_operacional(self):

        if not hasattr(
            self,
            "status",
        ):
            return

        # Não sobrescreve mensagens transitórias importantes.
        if self.troca_programa_em_andamento:
            return

        if self.modo_edicao:
            return

        if self.ciclo_em_andamento:
            return

        if not self.zl_conectado:

            self.status.setText(
                "🔴 CONTROLADOR ZL-9019 DESCONECTADO"
            )

            self.status.setStyleSheet(
                f"""
                color:{VERMELHO};
                font-size:32px;
                font-weight:bold;
                """
            )

            return

        if self.stop_acionado:

            self.status.setText(
                "⛔ STOP ACIONADO - CICLO BLOQUEADO"
            )

            self.status.setStyleSheet(
                f"""
                color:{VERMELHO};
                font-size:32px;
                font-weight:bold;
                """
            )

            return

        if self.aguardando_retirada_peca:

            self.status.setText(
                "🟡 RETIRE A PEÇA PARA REARMAR"
            )

            self.status.setStyleSheet(
                f"""
                color:{AMARELO};
                font-size:32px;
                font-weight:bold;
                """
            )

            return

        if self.fim_curso_ativo:

            self.status.setText(
                "🟢 PRONTO PARA MARCAR"
            )

            self.status.setStyleSheet(
                f"""
                color:{VERDE};
                font-size:32px;
                font-weight:bold;
                """
            )

            return

        self.status.setText(
            "🟡 AGUARDANDO POSICIONAMENTO DA PEÇA"
        )

        self.status.setStyleSheet(
            f"""
            color:{AMARELO};
            font-size:32px;
            font-weight:bold;
            """
        )

    # ========================================================
    # PROGRAMA AUTOMÁTICO
    # ========================================================

    def programa_automatico(self):

        return (
            self.programa_atual.upper()
            in PROGRAMAS_AUTOMATICOS
        )

    # ========================================================
    # ATUALIZAR CONTROLES
    # ========================================================

    def atualizar_habilitacao_controles(
        self
    ):

        ocupado = (
            self.troca_programa_em_andamento
        )

        self.btn_trocar_programa.setEnabled(
            not ocupado
        )

        self.shortcut_f3.setEnabled(
            not ocupado
        )

        if ocupado:

            self.btn_confirmar.setEnabled(
                False
            )

            self.btn_alterar.setEnabled(
                False
            )

            self.shortcut_f2.setEnabled(
                False
            )

            return

        if self.modo_edicao:

            self.btn_confirmar.setEnabled(
                True
            )

        else:

            self.btn_confirmar.setEnabled(
                self.pode_iniciar_ciclo()
            )

        if self.programa_automatico():

            self.btn_alterar.setEnabled(
                False
            )

            self.shortcut_f2.setEnabled(
                False
            )

        else:

            self.btn_alterar.setEnabled(
                True
            )

            self.shortcut_f2.setEnabled(
                True
            )

    # ========================================================
    # MODO PROGRAMA
    # ========================================================

    def atualizar_modo_programa(self):

        if self.programa_automatico():

            self.lbl_codigo.hide()

            self.codigo.hide()

            self.btn_alterar.hide()

            self.lbl_modo_automatico.show()

            self.texto_contador.setText(
                "PEÇAS BOSCH127"
            )

            self.codigo.setReadOnly(
                True
            )

            self.lbl_contador.setText(
                str(
                    self.contador_bosch
                )
            )

        else:

            self.lbl_codigo.show()

            self.codigo.show()

            self.btn_alterar.show()

            self.lbl_modo_automatico.hide()

            self.texto_contador.setText(
                "PEÇAS DESTE CÓDIGO"
            )

            codigo_salvo = (
                ler_codigo()
            )

            if codigo_valido(
                codigo_salvo
            ):

                self.codigo.setText(
                    codigo_salvo
                )

            else:

                self.codigo.setText(
                    ""
                )

            self.contador_codigo = (
                ler_contador_codigo()
            )

            self.lbl_contador.setText(
                str(
                    self.contador_codigo
                )
            )

        if hasattr(
            self,
            "shortcut_f2",
        ):

            self.atualizar_habilitacao_controles()

    # ========================================================
    # SAÍDA / SENHA
    # ========================================================

    def sair_sistema(self):

        senha, ok = QInputDialog.getText(
            self,
            "Acesso Restrito",
            "Digite a senha:",
            QLineEdit.Password,
        )

        if not ok:
            return

        if senha == "123":

            QApplication.quit()

        else:

            self.status.setText(
                "🔴 SENHA INCORRETA"
            )

            self.status.setStyleSheet(
                f"""
                color:{VERMELHO};
                font-size:32px;
                font-weight:bold;
                """
            )

            QTimer.singleShot(
                1500,
                self.reset_status,
            )

    def closeEvent(
        self,
        event,
    ):

        senha, ok = QInputDialog.getText(
            self,
            "Acesso Restrito",
            "Digite a senha:",
            QLineEdit.Password,
        )

        if (
            ok
            and senha == "123"
        ):

            event.accept()

        else:

            event.ignore()

    # ========================================================
    # STATUS
    # ========================================================

    def animar_status(self):

        if (
            self.status.text()
            != "🟢 PRONTO PARA MARCAR"
        ):

            return

        if self.pulso_status:

            self.status.setStyleSheet(
                f"""
                color:{VERDE};
                font-size:32px;
                font-weight:bold;
                """
            )

        else:

            self.status.setStyleSheet(
                f"""
                color:{VERDE_CLARO};
                font-size:32px;
                font-weight:bold;
                """
            )

        self.pulso_status = (
            not self.pulso_status
        )

    def mostrar_erro_temporario(
        self,
        mensagem,
        tempo=1800,
    ):

        self.status.setText(
            mensagem
        )

        self.status.setStyleSheet(
            f"""
            color:{VERMELHO};
            font-size:32px;
            font-weight:bold;
            """
        )

        QTimer.singleShot(
            tempo,
            self.reset_status,
        )

    # ========================================================
    # EDIÇÃO DO CÓDIGO
    # ========================================================

    def entrar_modo_edicao(self):

        if self.troca_programa_em_andamento:

            return

        if self.ciclo_em_andamento:

            return

        if self.programa_automatico():

            self.status.setText(
                "⚠️ PROGRAMA AUTOMÁTICO"
            )

            return

        self.codigo.setStyleSheet(
            f"""
            QLineEdit{{
                background-color:{CINZA_ESCURO};
                border:4px solid {AMARELO};
                border-radius:15px;
                color:{BRANCO};
                font-size:150px;
                font-weight:bold;
            }}
            """
        )

        self.modo_edicao = True

        self.codigo.setReadOnly(
            False
        )

        self.codigo.setFocus()

        self.codigo.selectAll()

        try:

            self.codigo.returnPressed.disconnect()

        except Exception:
            pass

        self.codigo.returnPressed.connect(
            self.salvar_novo_codigo
        )

        self.btn_confirmar.setText(
            "SALVAR"
        )

        # SALVAR código não depende do fim de curso.
        self.btn_confirmar.setEnabled(
            True
        )

        self.btn_alterar.setText(
            "CANCELAR"
        )

        try:

            self.btn_confirmar.clicked.disconnect()

        except Exception:
            pass

        self.btn_confirmar.clicked.connect(
            self.salvar_novo_codigo
        )

        try:

            self.btn_alterar.clicked.disconnect()

        except Exception:
            pass

        self.btn_alterar.clicked.connect(
            self.cancelar_edicao
        )

        self.status.setText(
            "🟡 DIGITE O NOVO CÓDIGO"
        )

        self.status.setStyleSheet(
            f"""
            color:{AMARELO};
            font-size:32px;
            font-weight:bold;
            """
        )

    def cancelar_edicao(self):

        codigo_salvo = (
            ler_codigo()
        )

        if codigo_valido(
            codigo_salvo
        ):

            self.codigo.setText(
                codigo_salvo
            )

        else:

            self.codigo.setText(
                ""
            )

        self.sair_modo_edicao()

    def salvar_novo_codigo(self):

        novo_codigo = (
            self.codigo.text()
            .strip()
            .upper()
        )

        if not codigo_valido(
            novo_codigo
        ):

            self.status.setText(
                "🔴 CÓDIGO DEVE TER 6 LETRAS"
            )

            self.erro_codigo()

            return

        antigo = (
            ler_codigo()
        )

        if (
            novo_codigo
            != antigo
        ):

            salvar_codigo(
                novo_codigo
            )

            registrar_alteracao(
                antigo,
                novo_codigo,
            )

            # O contador visual do código
            # recomeça do zero.
            self.contador_codigo = 0

            salvar_contador_codigo(
                0
            )

            self.lbl_contador.setText(
                "0"
            )

            # IMPORTANTE:
            # O CSV NÃO é zerado aqui.
            #
            # Se o código já produziu peças hoje,
            # incrementar_producao_codigo()
            # continuará somando a produção antiga.

        self.sair_modo_edicao()

    def sair_modo_edicao(self):

        self.codigo.setStyleSheet(
            f"""
            QLineEdit{{
                background:transparent;
                border:none;
                color:{AZUL};
                font-size:150px;
                font-weight:bold;
            }}
            """
        )

        try:

            self.codigo.returnPressed.disconnect()

        except Exception:
            pass

        self.modo_edicao = False

        self.codigo.setReadOnly(
            True
        )

        try:

            self.btn_confirmar.clicked.disconnect()

        except Exception:
            pass

        self.btn_confirmar.clicked.connect(
            self.confirmar
        )

        try:

            self.btn_alterar.clicked.disconnect()

        except Exception:
            pass

        self.btn_alterar.clicked.connect(
            self.entrar_modo_edicao
        )

        self.btn_confirmar.setText(
            "CONFIRMAR(ENTER)"
        )

        self.btn_alterar.setText(
            "ALTERAR CÓDIGO(F2)"
        )

        self.atualizar_habilitacao_controles()
        self.atualizar_status_operacional()

    # ========================================================
    # ENTER
    # ========================================================

    def acao_enter(self):

        if self.troca_programa_em_andamento:

            return

        if self.modo_edicao:

            self.salvar_novo_codigo()

        else:

            self.confirmar()

    # ========================================================
    # ERRO CÓDIGO
    # ========================================================

    def erro_codigo(self):

        self.status.setText(
            "🔴 CÓDIGO INVÁLIDO"
        )

        self.piscar_vermelho_1()

    def piscar_vermelho_1(self):

        self.setStyleSheet(
            f"""
            QWidget{{
                background:{VERMELHO};
                color:white;
            }}
            """
        )

        QTimer.singleShot(
            150,
            self.piscar_preto_1,
        )

    def piscar_preto_1(self):

        self.setStyleSheet(
            f"""
            QWidget{{
                background:{CINZA_ESCURO};
                color:white;
            }}
            """
        )

        QTimer.singleShot(
            150,
            self.piscar_vermelho_2,
        )

    def piscar_vermelho_2(self):

        self.setStyleSheet(
            f"""
            QWidget{{
                background:{VERMELHO};
                color:white;
            }}
            """
        )

        QTimer.singleShot(
            150,
            self.restaurar_erro,
        )

    def restaurar_erro(self):

        self.setStyleSheet(
            f"""
            QWidget{{
                background:{CINZA_ESCURO};
                color:white;
            }}
            """
        )

        self.codigo.setStyleSheet(
            f"""
            QLineEdit{{
                background-color:{CINZA_ESCURO};
                border:4px solid {AMARELO};
                border-radius:15px;
                color:white;
                font-size:150px;
                font-weight:bold;
            }}
            """
        )

        self.status.setText(
            "🟡 DIGITE O NOVO CÓDIGO"
        )

        self.status.setStyleSheet(
            f"""
            color:{AMARELO};
            font-size:32px;
            font-weight:bold;
            """
        )

        self.codigo.setFocus()

    # ========================================================
    # MAIÚSCULAS
    # ========================================================

    def converter_maiusculo(self):

        texto = (
            self.codigo.text()
        )

        cursor = (
            self.codigo.cursorPosition()
        )

        self.codigo.blockSignals(
            True
        )

        self.codigo.setText(
            texto.upper()
        )

        self.codigo.setCursorPosition(
            cursor
        )

        self.codigo.blockSignals(
            False
        )

    # ========================================================
    # RELÓGIO + RESET À MEIA-NOITE
    # ========================================================

    def atualizar_relogio(self):

        agora = (
            datetime.now()
        )

        self.relogio.setText(
            agora.strftime(
                "%d/%m/%Y\n%H:%M:%S"
            )
        )

        self.verificar_mudanca_dia(
            agora.date()
        )

    def verificar_mudanca_dia(
        self,
        hoje,
    ):

        if (
            hoje
            == self.data_referencia
        ):

            return

        self.data_referencia = (
            hoje
        )

        self.contador_dia = 0

        salvar_contador_dia(
            0
        )

        try:

            Path(
                ARQUIVO_DATA
            ).write_text(
                hoje.strftime(
                    "%d/%m/%Y"
                ),
                encoding="utf-8",
            )

        except OSError:
            pass

        self.info_rodape.setText(
            "PEÇAS HOJE: 0"
        )

    # ========================================================
    # TROCA DE PROGRAMA
    # ========================================================

    def trocar_programa(self):

        if self.troca_programa_em_andamento:

            return

        if self.ciclo_em_andamento:

            self.mostrar_erro_temporario(
                "⚠️ AGUARDE O CICLO ATUAL"
            )

            return

        programas = (
            listar_programas_ezd()
        )

        if not programas:

            self.mostrar_erro_temporario(
                "🔴 NENHUM PROGRAMA .EZD ENCONTRADO"
            )

            return

        dialog = SeletorProgramaDialog(
            self,
            programas,
            self.programa_atual,
        )

        if (
            dialog.exec()
            != QDialog.Accepted
        ):

            return

        novo_programa = (
            dialog.selected_programa()
        )

        if not novo_programa:
            return

        if (
            novo_programa
            == self.programa_atual
        ):

            return

        # ----------------------------------------------------
        # AVISO DE SEGURANÇA
        # ----------------------------------------------------

        aviso = AvisoFocoDialog(
            self
        )

        if (
            aviso.exec()
            != QDialog.Accepted
        ):

            return

        # ----------------------------------------------------
        # IMPORTANTE:
        #
        # NÃO salva programa_atual aqui.
        #
        # Primeiro o HORUS precisa confirmar
        # que conseguiu carregar.
        # ----------------------------------------------------

        self.programa_pendente = (
            novo_programa
        )

        self.troca_programa_em_andamento = (
            True
        )

        self.atualizar_habilitacao_controles()

        self.status.setText(
            "🟡 CARREGANDO PROGRAMA NO HORUS..."
        )

        self.status.setStyleSheet(
            f"""
            color:{AMARELO};
            font-size:32px;
            font-weight:bold;
            """
        )

        Thread(
            target=self._executar_carregamento_horus,
            args=(
                novo_programa,
            ),
            daemon=True,
        ).start()

    def _executar_carregamento_horus(
        self,
        novo_programa,
    ):

        sucesso, mensagem = (
            carregar_programa_ezd(
                novo_programa
            )
        )

        # SIGNAL do Qt.
        #
        # Isso é importante porque NÃO devemos
        # alterar widgets diretamente da Thread.
        self.ponte_horus.resultado_carregamento.emit(
            sucesso,
            mensagem,
            novo_programa,
        )

    def finalizar_troca_programa(
        self,
        sucesso,
        mensagem,
        novo_programa,
    ):

        self.troca_programa_em_andamento = (
            False
        )

        self.programa_pendente = ""

        # ----------------------------------------------------
        # SUCESSO
        # ----------------------------------------------------

        if sucesso:

            antigo_programa = (
                self.programa_atual
                if self.programa_atual
                else "SEM PROGRAMA"
            )

            # Agora sim salva.
            salvar_programa_atual(
                novo_programa
            )

            # Agora sim altera a IHM.
            self.atualizar_programa_selecionado(
                novo_programa
            )

            # Agora sim registra troca.
            registrar_troca_programa(
                antigo_programa,
                novo_programa,
            )

            self.status.setText(
                "✅ PROGRAMA CARREGADO NO HORUS"
            )

            self.status.setStyleSheet(
                f"""
                color:{VERDE};
                font-size:32px;
                font-weight:bold;
                """
            )

            self.atualizar_habilitacao_controles()

            QTimer.singleShot(
                1800,
                self.reset_status,
            )

            return

        # ----------------------------------------------------
        # FALHA
        # ----------------------------------------------------

        registrar_erro_horus(
            novo_programa,
            mensagem,
        )

        # Não altera programa_atual.
        # Não altera programa_atual.txt.
        # Não altera preview.
        # Não altera contador.

        self.status.setText(
            "🔴 PROGRAMA NÃO CARREGADO NO HORUS"
        )

        self.status.setStyleSheet(
            f"""
            color:{VERMELHO};
            font-size:32px;
            font-weight:bold;
            """
        )

        self.atualizar_habilitacao_controles()

        QTimer.singleShot(
            3000,
            self.reset_status,
        )

    # ========================================================
    # PROGRAMA SELECIONADO
    # ========================================================

    def atualizar_programa_selecionado(
        self,
        programa_nome,
    ):

        anterior = (
            self.programa_atual
        )

        self.programa_atual = (
            programa_nome
            or ""
        )

        programa = (
            self.programa_atual
            if self.programa_atual
            else "SEM PROGRAMA SELECIONADO"
        )

        html = (
            f'<span style="color:{CINZA_CLARO}; '
            f'font-size:28px;">'
            f'PROGRAMA ATUAL:</span> '
            f'<span style="color:{AZUL}; '
            f'font-weight:bold; font-size:28px;">'
            f'{programa}</span>'
        )

        self.lbl_programa_nome.setTextFormat(
            Qt.RichText
        )

        self.lbl_programa_nome.setText(
            html
        )

        self.atualizar_preview()

        # ----------------------------------------------------
        # CONTADOR VISUAL BOSCH
        #
        # Ao ENTRAR no programa BOSCH,
        # contador visual recomeça do zero.
        #
        # O CSV, entretanto, continua acumulando.
        # ----------------------------------------------------

        if (
            self.programa_automatico()
            and anterior
            != self.programa_atual
        ):

            self.contador_bosch = 0

            salvar_contador_bosch127(
                self.contador_bosch
            )

        self.atualizar_modo_programa()

    # ========================================================
    # PREVIEW
    # ========================================================

    def atualizar_preview(self):

        self.preview_pixmap = None

        self.peca_pixmap = None

        if self.programa_atual:

            preview_path = (
                obter_caminho_programa(
                    self.programa_atual
                )
                .with_suffix(
                    ".png"
                )
            )

            peca_path = (
                Path(PASTA_PROGRAMAS)
                / (
                    f"{Path(self.programa_atual).stem}"
                    f"_setup.png"
                )
            )

            # ------------------------------------------------
            # PREVIEW DA MARCAÇÃO
            # ------------------------------------------------

            if preview_path.exists():

                pixmap = QPixmap(
                    str(
                        preview_path
                    )
                )

                if not pixmap.isNull():

                    self.preview_pixmap = (
                        pixmap
                    )

                    self._atualizar_preview_pixmap()

                else:

                    self.preview_area.setPixmap(
                        QPixmap()
                    )

                    self.preview_area.setText(
                        "SEM IMAGEM DISPONÍVEL"
                    )

            else:

                self.preview_area.setPixmap(
                    QPixmap()
                )

                self.preview_area.setText(
                    "SEM IMAGEM DISPONÍVEL"
                )

            # ------------------------------------------------
            # IMAGEM POSICIONAMENTO
            # ------------------------------------------------

            if peca_path.exists():

                pixmap = QPixmap(
                    str(
                        peca_path
                    )
                )

                if not pixmap.isNull():

                    self.peca_pixmap = (
                        pixmap
                    )

                    self._atualizar_peca_pixmap()

                else:

                    self.peca_area.setPixmap(
                        QPixmap()
                    )

                    self.peca_area.setText(
                        "SEM IMAGEM DISPONÍVEL"
                    )

            else:

                self.peca_area.setPixmap(
                    QPixmap()
                )

                self.peca_area.setText(
                    "SEM IMAGEM DISPONÍVEL"
                )

            return

        self.preview_area.setPixmap(
            QPixmap()
        )

        self.preview_area.setText(
            "SEM IMAGEM DISPONÍVEL"
        )

        self.peca_area.setPixmap(
            QPixmap()
        )

        self.peca_area.setText(
            "SEM IMAGEM DISPONÍVEL"
        )

    def _atualizar_preview_pixmap(self):

        if not self.preview_pixmap:
            return

        area = (
            self.preview_area.size()
        )

        if (
            area.width() < 10
            or area.height() < 10
        ):

            area = QSize(
                360,
                150,
            )

        scaled = (
            self.preview_pixmap.scaled(
                area,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        self.preview_area.setPixmap(
            scaled
        )

        self.preview_area.setText(
            ""
        )

    def _atualizar_peca_pixmap(self):

        if not self.peca_pixmap:
            return

        area = (
            self.peca_area.size()
        )

        if (
            area.width() < 10
            or area.height() < 10
        ):

            area = QSize(
                860,
                420,
            )

        scaled = (
            self.peca_pixmap.scaled(
                area,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        self.peca_area.setPixmap(
            scaled
        )

        self.peca_area.setText(
            ""
        )

    def resizeEvent(
        self,
        event,
    ):

        super().resizeEvent(
            event
        )

        if self.preview_pixmap:

            self._atualizar_preview_pixmap()

        if self.peca_pixmap:

            self._atualizar_peca_pixmap()

    # ========================================================
    # CHAVE DE PRODUÇÃO
    # ========================================================

    def chave_producao_atual(
        self
    ):

        """
        Define o nome usado no producao_diaria.csv.

        Para programas automáticos:
        BOSCH127.EZD vira BOSCH127.

        Para programas normais:
        utiliza o código de 6 letras.
        """

        if self.programa_automatico():

            return (
                Path(
                    self.programa_atual
                )
                .stem
                .upper()
            )

        return (
            self.codigo.text()
            .strip()
            .upper()
        )

    # ========================================================
    # CONFIRMAÇÃO / PRODUÇÃO
    # ========================================================

    def confirmar(self):

        # ----------------------------------------------------
        # BLOQUEIA DURANTE TROCA DE PROGRAMA
        # ----------------------------------------------------

        if self.troca_programa_em_andamento:

            return

        # ----------------------------------------------------
        # BLOQUEIO CONTRA ENTER DUPLO
        # ----------------------------------------------------

        if self.ciclo_em_andamento:

            return

        # ----------------------------------------------------
        # INTERTRAVAMENTO ZL-9019
        # ----------------------------------------------------

        if not self.zl_conectado:

            self.mostrar_erro_temporario(
                "🔴 CONTROLADOR ZL-9019 DESCONECTADO"
            )

            return

        if self.stop_acionado:

            self.mostrar_erro_temporario(
                "⛔ STOP ACIONADO - CICLO BLOQUEADO"
            )

            return

        if self.aguardando_retirada_peca:

            self.mostrar_erro_temporario(
                "🟡 RETIRE A PEÇA PARA REARMAR"
            )

            return

        if not self.fim_curso_ativo:

            self.mostrar_erro_temporario(
                "🔴 PEÇA FORA DE POSIÇÃO - FIM DE CURSO ABERTO"
            )

            return

        # ----------------------------------------------------
        # PRECISA TER PROGRAMA
        # ----------------------------------------------------

        if not self.programa_atual:

            self.mostrar_erro_temporario(
                "🔴 SELECIONE UM PROGRAMA"
            )

            return

        # ----------------------------------------------------
        # VALIDA CÓDIGO
        # ----------------------------------------------------

        if not self.programa_automatico():

            codigo_atual = (
                self.codigo.text()
                .strip()
                .upper()
            )

            if not codigo_valido(
                codigo_atual
            ):

                self.mostrar_erro_temporario(
                    "🔴 CÓDIGO INVÁLIDO"
                )

                return

        # ----------------------------------------------------
        # A PARTIR DAQUI O CICLO FICA BLOQUEADO
        # ----------------------------------------------------

        self.ciclo_em_andamento = (
            True
        )

        # Exige retirar a peça antes de liberar outro ciclo.
        self.aguardando_retirada_peca = True

        self.atualizar_habilitacao_controles()

        # ----------------------------------------------------
        # CONTADOR DIÁRIO
        # ----------------------------------------------------

        self.contador_dia += 1

        salvar_contador_dia(
            self.contador_dia
        )

        # ----------------------------------------------------
        # PROGRAMA AUTOMÁTICO
        # ----------------------------------------------------

        if self.programa_automatico():

            self.contador_bosch += 1

            salvar_contador_bosch127(
                self.contador_bosch
            )

            self.lbl_contador.setText(
                str(
                    self.contador_bosch
                )
            )

        # ----------------------------------------------------
        # PROGRAMA NORMAL
        # ----------------------------------------------------

        else:

            self.contador_codigo += 1

            salvar_contador_codigo(
                self.contador_codigo
            )

            self.lbl_contador.setText(
                str(
                    self.contador_codigo
                )
            )

        # ----------------------------------------------------
        # HISTÓRICO DE PRODUÇÃO
        #
        # Agora soma +1.
        #
        # Não copia mais o contador da tela para o CSV.
        # ----------------------------------------------------

        chave_producao = (
            self.chave_producao_atual()
        )

        incrementar_producao_codigo(
            chave_producao,
            1,
        )

        # ----------------------------------------------------
        # RODAPÉ
        # ----------------------------------------------------

        self.info_rodape.setText(
            f"PEÇAS HOJE: "
            f"{self.contador_dia}"
        )

        # ----------------------------------------------------
        # FEEDBACK VISUAL
        # ----------------------------------------------------

        self.status.setText(
            "✅ PEÇA CONFIRMADA"
        )

        self.status.setStyleSheet(
            """
            color:white;
            font-size:40px;
            font-weight:bold;
            """
        )

        self.setStyleSheet(
            f"""
            QWidget{{
                background-color:{VERDE_CLARO};
                color:white;
            }}
            """
        )

        # ----------------------------------------------------
        # 800 ms de bloqueio
        #
        # Impede ENTER duplo / repetição rápida.
        # ----------------------------------------------------

        QTimer.singleShot(
            800,
            self.finalizar_confirmacao,
        )

    def finalizar_confirmacao(
        self
    ):

        self.ciclo_em_andamento = (
            False
        )

        self.atualizar_habilitacao_controles()
        self.reset_status()

    # ========================================================
    # RESET STATUS
    # ========================================================

    def reset_status(self):

        # Não deixa algum timer antigo sobrescrever
        # "CARREGANDO PROGRAMA..."
        if self.troca_programa_em_andamento:

            return

        # Não sobrescreve tela de edição.
        if self.modo_edicao:

            return

        self.setStyleSheet(
            f"""
            QWidget{{
                background-color:{CINZA_ESCURO};
                color:white;
            }}
            """
        )

        self.atualizar_habilitacao_controles()
        self.atualizar_status_operacional()

        if self.btn_confirmar.isEnabled():
            self.btn_confirmar.setFocus()


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    janela = JanelaPrincipal()

    janela.showFullScreen()

    sys.exit(
        app.exec()
    )