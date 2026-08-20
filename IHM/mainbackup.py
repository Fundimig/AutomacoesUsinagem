import sys
import time
import importlib
from threading import Thread
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QRegularExpression, QSize
from PySide6.QtGui import QPixmap, QShortcut, QKeySequence, QRegularExpressionValidator
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

ARQUIVO_CODIGO = "codigo.txt"
ARQUIVO_CONTADOR_DIA = "contador_dia.txt"
ARQUIVO_CONTADOR_CODIGO = "contador_codigo.txt"
ARQUIVO_LOG = "historico.log"
ARQUIVO_DATA = "data_contador.txt"
ARQUIVO_HISTORICO_PRODUCAO = "producao_diaria.csv"
ARQUIVO_PROGRAMA_ATUAL = "programa_atual.txt"
PASTA_PROGRAMAS = "C:\\Programas marcação a laser"

PROGRAMAS_AUTOMATICOS = [
    "BOSCH127",
    "BOSCH127.EZD",
]

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


# ==========================
# ARQUIVOS
# ==========================

def ler_codigo():
    arq = Path(ARQUIVO_CODIGO)
    if not arq.exists():
        arq.write_text("SEM CODIGO", encoding="utf-8")
    return arq.read_text(encoding="utf-8").strip()


def salvar_codigo(codigo):
    Path(ARQUIVO_CODIGO).write_text(codigo, encoding="utf-8")


def ler_contador_dia():
    arq = Path(ARQUIVO_CONTADOR_DIA)
    if not arq.exists():
        arq.write_text("0")
    return int(arq.read_text().strip())


def salvar_contador_dia(valor):
    Path(ARQUIVO_CONTADOR_DIA).write_text(str(valor))


def ler_contador_codigo():
    arq = Path(ARQUIVO_CONTADOR_CODIGO)
    if not arq.exists():
        arq.write_text("0")
    return int(arq.read_text().strip())


def verificar_reset_diario():
    hoje = datetime.now().strftime("%d/%m/%Y")
    arq = Path(ARQUIVO_DATA)
    if not arq.exists():
        arq.write_text(hoje, encoding="utf-8")
        return

    ultima_data = arq.read_text(encoding="utf-8").strip()
    if ultima_data != hoje:
        salvar_contador_dia(0)
        arq.write_text(hoje, encoding="utf-8")


def atualizar_producao_codigo(codigo, quantidade):
    hoje = datetime.now().strftime("%d/%m/%Y")
    arquivo = Path(ARQUIVO_HISTORICO_PRODUCAO)
    registros = {}
    if arquivo.exists():
        with open(arquivo, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                partes = linha.split(";")
                if len(partes) != 3:
                    continue
                data, cod, qtd = partes
                registros[(data, cod)] = qtd

    registros[(hoje, codigo)] = str(quantidade)
    with open(arquivo, "w", encoding="utf-8") as f:
        for (data, cod), qtd in registros.items():
            f.write(f"{data};{cod};{qtd}\n")


def salvar_contador_codigo(valor):
    Path(ARQUIVO_CONTADOR_CODIGO).write_text(str(valor))


def ler_contador_bosch127():
    arq = Path("contador_bosch127.txt")
    if not arq.exists():
        arq.write_text("0")
    return int(arq.read_text().strip())


def salvar_contador_bosch127(valor):
    Path("contador_bosch127.txt").write_text(str(valor))


def listar_programas_ezd():
    pasta = Path(PASTA_PROGRAMAS)
    if not pasta.exists():
        return []
    return sorted(
        [arquivo.name for arquivo in pasta.glob("*.ezd") if arquivo.is_file()],
        key=str.casefold,
    )


def ler_programa_atual():
    arq = Path(ARQUIVO_PROGRAMA_ATUAL)
    if not arq.exists():
        arq.write_text("", encoding="utf-8")
        return ""
    return arq.read_text(encoding="utf-8").strip()


def salvar_programa_atual(nome):
    Path(ARQUIVO_PROGRAMA_ATUAL).write_text(nome, encoding="utf-8")


def obter_caminho_programa(nome):
    return Path(PASTA_PROGRAMAS) / nome


def registrar_alteracao(antigo, novo):
    agora = datetime.now()
    texto = f"""

{agora.strftime('%d/%m/%Y %H:%M:%S')}

ANTIGO:
{antigo}

NOVO:
{novo}

------------------------------------

"""
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as arquivo:
        arquivo.write(texto)


def registrar_troca_programa(antigo, novo):
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
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as arquivo:
        arquivo.write(texto)


def carregar_programa_ezd(nome_programa):

    log_path = Path("debug_horus.log")

    with log_path.open("a", encoding="utf-8") as log_fh:

        def log(msg):
            print(msg)
            log_fh.write(msg + "\n")
            log_fh.flush()

        try:

            log("PASSO 1 - Importando pywinauto")

            from pywinauto import Desktop

            log("PASSO 2 - Procurando HORUS")

            horus = Desktop(
                backend="win32"
            ).window(
                title_re=".*HORUS.*"
            )

            log(
                f"PASSO 3 - Janela encontrada: "
                f"{horus.window_text()}"
            )

            menu_items = horus.menu_items()

            programa_sem_extensao = (
                Path(nome_programa)
                .stem
                .upper()
            )

            log(
                f"PASSO 4 - Procurando "
                f"{programa_sem_extensao}"
            )

            caminho_menu = None

            for item in menu_items:

                if item.get("text") != "Arquivo":
                    continue

                submenu = item.get(
                    "menu_items",
                    {}
                ).get(
                    "menu_items",
                    []
                )

                for subitem in submenu:

                    texto = subitem.get(
                        "text",
                        ""
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
                    "PROGRAMA NÃO ENCONTRADO NO MENU HORUS"
                )

            log(
                f"PASSO 5 - Executando: "
                f"{caminho_menu}"
            )

            horus.menu_select(
                caminho_menu
            )

            try:
                from pywinauto import Desktop

                janelas = Desktop(
                    backend="win32"
                ).windows()

                for w in janelas:

                    try:

                        if (
                            w.window_text()
                            == "Rastreabilidade Laser"
                        ):

                            w.set_focus()
                            break

                    except:
                        pass

            except Exception as e:

                log(
                    f"Falha ao devolver foco: {e}"
                )

            log(
                "PASSO 6 - PROGRAMA CARREGADO"
            )

            return (
                True,
                "PROGRAMA CARREGADO"
            )

        except Exception as e:

            import traceback

            traceback.print_exc()

            log(
                f"ERRO HORUS: {e}"
            )

            return (
                False,
                f"ERRO: {e}"
            )


class SeletorProgramaDialog(QDialog):
    def __init__(self, parent, programas, selecionado):
        super().__init__(parent)
        self.setWindowTitle("Trocar Programa")
        self.setModal(True)
        self.setMinimumSize(900, 700)
        self.setStyleSheet(f"""
            QDialog{{
                background:{CINZA_ESCURO_TELA};
                color:white;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        titulo = QLabel("SELECIONE O PROGRAMA")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(f"""
            color:{BRANCO};
            font-size:32px;
            font-weight:bold;
        """)
        layout.addWidget(titulo)

        self.lista = QListWidget()
        self.lista.setStyleSheet(f"""
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
        """)
        self.lista.setUniformItemSizes(True)
        self.lista.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for programa in programas:
            item = QListWidgetItem(programa)
            item.setTextAlignment(Qt.AlignCenter)
            item.setSizeHint(QSize(0, 80))
            self.lista.addItem(item)

        if selecionado in programas:
            self.lista.setCurrentRow(programas.index(selecionado))

        lista_container = QHBoxLayout()
        lista_container.addStretch(1)
        lista_container.addWidget(self.lista, 2)
        lista_container.addStretch(1)
        layout.addLayout(lista_container)

        botoes = QHBoxLayout()
        botoes.setSpacing(30)
        botoes.addStretch(1)

        self.btn_ok = QPushButton("OK")
        self.btn_ok.setFixedHeight(70)
        self.btn_ok.setStyleSheet(f"""
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
        """)
        self.btn_ok.clicked.connect(self.accept)
        botoes.addWidget(self.btn_ok)

        self.btn_cancelar = QPushButton("CANCELAR")
        self.btn_cancelar.setFixedHeight(70)
        self.btn_cancelar.setStyleSheet(f"""
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
        """)
        self.btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(self.btn_cancelar)

        botoes.addStretch(1)
        layout.addLayout(botoes)

        QShortcut(QKeySequence("Return"), self, activated=self._aceitar)
        QShortcut(QKeySequence("Enter"), self, activated=self._aceitar)

    def _aceitar(self):
        if self.lista.currentRow() >= 0:
            self.accept()

    def selected_programa(self):
        item = self.lista.currentItem()
        return item.text() if item else None


class AvisoFocoDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("ATENÇÃO")
        self.setModal(True)
        self.setMinimumSize(900, 700)
        self.setStyleSheet(f"""
            QDialog{{
                background:{CINZA_ESCURO};
                color:white;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        top = QHBoxLayout()
        top.setSpacing(20)
        top.addStretch(1)

        icone_label = QLabel()
        icone = self.style().standardIcon(QStyle.SP_MessageBoxWarning)
        icone_label.setPixmap(icone.pixmap(90, 90))
        top.addWidget(icone_label, alignment=Qt.AlignCenter)

        titulo = QLabel("ATENÇÃO")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(f"""
            color:{AMARELO};
            font-size:48px;
            font-weight:bold;
        """)
        top.addWidget(titulo)
        top.addStretch(1)
        layout.addLayout(top)

        mensagem = QLabel(
            "PROGRAMA ALTERADO.\n\n"
            "ANTES DE INICIAR A MARCAÇÃO:\n\n"
            "🎯 CONFIRMAR O FOCO DO LASER \n"
            "🧩 CONFIRMAR O POSICIONAMENTO DA PEÇA\n"
            "💾 CONFIRMAR O PROGRAMA SELECIONADO\n\n"
            "Pressione enter para continuar."
        )
        mensagem.setAlignment(Qt.AlignCenter)
        mensagem.setWordWrap(True)
        mensagem.setStyleSheet(f"""
            color:{BRANCO};
            font-size:28px;
        """)
        layout.addWidget(mensagem, alignment=Qt.AlignCenter)

        self.btn_continuar = QPushButton("ENTER PARA CONTINUAR")
        self.btn_continuar.setFixedHeight(80)
        self.btn_continuar.setStyleSheet(f"""
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
        """)
        self.btn_continuar.clicked.connect(self.accept)

        botao_layout = QHBoxLayout()
        botao_layout.addStretch(1)
        botao_layout.addWidget(self.btn_continuar)
        botao_layout.addStretch(1)
        layout.addLayout(botao_layout)

        QShortcut(QKeySequence("Return"), self, activated=self.accept)
        QShortcut(QKeySequence("Enter"), self, activated=self.accept)


# ==========================
# TELA PRINCIPAL
# ==========================

class JanelaPrincipal(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)

        verificar_reset_diario()
        self.setWindowTitle("Rastreabilidade Laser")

        self.contador_dia = ler_contador_dia()
        self.contador_codigo = ler_contador_codigo()
        self.contador_bosch = ler_contador_bosch127()
        self.modo_edicao = False
        self.preview_pixmap = None
        self.peca_pixmap = None

        self.programas_ezd = listar_programas_ezd()
        self.programa_atual = ler_programa_atual()
        self.codigo_inicial = "" if self.programa_atual.upper() in PROGRAMAS_AUTOMATICOS else ler_codigo()

        self.setStyleSheet(f"""
            QWidget{{
                background:{CINZA_ESCURO};
                color:white;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pulso_status = True
        self.timer_pulso = QTimer()
        self.timer_pulso.timeout.connect(self.animar_status)
        self.timer_pulso.start(500)

        layout = QVBoxLayout()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # CABEÇALHO + TÍTULO NA MESMA LINHA
        cabecalho_widget = QWidget()
        #cabecalho_widget.setStyleSheet(f"background:{CINZA_ESCURO};")
        cabecalho = QHBoxLayout(cabecalho_widget)
        cabecalho.setContentsMargins(20, 10, 20, 10)
        cabecalho.setSpacing(20)

        self.logo = QLabel()
        pixmap = QPixmap("assets/logo-fundimig.png")

        if not pixmap.isNull():
            self.logo.setPixmap(
                pixmap.scaled(
                    180,
                    70,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        titulo = QLabel("SISTEMA DE RASTREABILIDADE")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("""
            font-size:40px;
            font-weight:bold;
        """)

        self.relogio = QLabel()
        self.relogio.setAlignment(Qt.AlignRight)
        self.relogio.setStyleSheet("""
            font-size:24px;
            font-weight:bold;
        """)

        cabecalho.addWidget(self.logo)

        cabecalho.addStretch(1)

        cabecalho.addWidget(
            titulo,
            alignment=Qt.AlignCenter
        )

        cabecalho.addStretch(1)

        cabecalho.addWidget(self.relogio)

        layout.addWidget(cabecalho_widget)

        conteudo_principal = QHBoxLayout()

        # LADO ESQUERDO
        lado_esquerdo = QVBoxLayout()
        self.lbl_codigo = QLabel("CÓDIGO ATUAL")
        self.lbl_codigo.setAlignment(Qt.AlignCenter)
        self.lbl_codigo.setStyleSheet(f"""
            color:{CINZA_CLARO};
            font-size:28px;
        """)
        lado_esquerdo.addWidget(self.lbl_codigo)

        self.codigo = QLineEdit(self.codigo_inicial)
        self.codigo.setAlignment(Qt.AlignCenter)
        self.codigo.setReadOnly(True)
        self.codigo.setMaxLength(6)
        regex = QRegularExpression("[A-Za-z]{0,6}")
        validador = QRegularExpressionValidator(regex)
        self.codigo.setValidator(validador)
        self.codigo.textChanged.connect(self.converter_maiusculo)
        self.codigo.setStyleSheet(f"""
        QLineEdit{{
            background: transparent;
            border:none;
            color:{AZUL};
            font-size:150px;
            font-weight:bold;
        }}
        """)
        self.codigo.setMaximumHeight(220)
        self.codigo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lado_esquerdo.addWidget(self.codigo)

        self.status = QLabel("🟢 PRONTO PARA MARCAR")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet(f"""
            color:{VERDE};
            font-size:32px;
            font-weight:bold;
        """)
        self.status.setMaximumHeight(90)
        self.status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lado_esquerdo.addWidget(self.status)

        self.texto_contador = QLabel("PEÇAS DESTE CÓDIGO")
        self.texto_contador.setAlignment(Qt.AlignCenter)
        self.texto_contador.setStyleSheet("""
            font-size:24px;
        """)
        self.texto_contador.setMaximumHeight(50)
        self.texto_contador.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_contador = QLabel(str(self.contador_codigo))
        self.lbl_contador.setAlignment(Qt.AlignCenter)
        self.lbl_contador.setStyleSheet(f"""
            color:{AZUL};
            font-size:60px;
            font-weight:bold;
        """)
        self.lbl_contador.setMaximumHeight(140)
        self.lbl_contador.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lado_esquerdo.addWidget(self.texto_contador)
        lado_esquerdo.addWidget(self.lbl_contador)
        lado_esquerdo.addStretch()

        botoes = QHBoxLayout()
        self.btn_confirmar = QPushButton("CONFIRMAR(ENTER)")
        self.btn_confirmar.clicked.connect(self.confirmar)
        self.btn_confirmar.setStyleSheet(f"""
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
        """)
        self.btn_alterar = QPushButton("ALTERAR CÓDIGO(F2)")
        self.btn_alterar.clicked.connect(self.entrar_modo_edicao)
        self.btn_alterar.setStyleSheet(f"""
            QPushButton{{
                background:{AMARELO};
                color:black;
                font-size:32px;
                font-weight:bold;
                padding:20px;
                border-radius:10px;
            }}
        """)
        botoes.addWidget(self.btn_confirmar)
        botoes.addWidget(self.btn_alterar)
        lado_esquerdo.addLayout(botoes)
        lado_esquerdo.addStretch()

        conteudo_principal.addLayout(lado_esquerdo, 1)

        # LADO DIREITO - PROGRAMA
        lado_direito = QVBoxLayout()
        linha_programa = QHBoxLayout()
        programa = self.programa_atual if self.programa_atual else "SEM PROGRAMA SELECIONADO"
        html = (
            f"<span style=\"color:{CINZA_CLARO}; font-size:28px;\">PROGRAMA ATUAL:</span> "
            f"<span style=\"color:{AZUL}; font-weight:bold; font-size:28px;\">{programa}</span>"
        )
        self.lbl_programa_nome = QLabel(html)
        self.lbl_programa_nome.setTextFormat(Qt.RichText)
        self.lbl_programa_nome.setMaximumHeight(80)
        self.lbl_programa_nome.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_programa_nome.setMaximumHeight(80)
        self.lbl_programa_nome.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        linha_programa.addStretch()
        linha_programa.addWidget(self.lbl_programa_nome)
        linha_programa.addStretch()

        lado_direito.addLayout(linha_programa)

        self.lbl_modo_automatico = QLabel("MODO AUTOMÁTICO - CÓDIGO FIXO")
        self.lbl_modo_automatico.setAlignment(Qt.AlignCenter)
        self.lbl_modo_automatico.setStyleSheet(f"""
            color:{VERDE};
            font-size:24px;
            font-weight:bold;
        """)
        self.lbl_modo_automatico.setMaximumHeight(70)
        self.lbl_modo_automatico.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lbl_modo_automatico.hide()
        lado_direito.addWidget(self.lbl_modo_automatico)
        lado_direito.addSpacing(0)

        troca_preview_row = QHBoxLayout()
        troca_preview_row.setAlignment(Qt.AlignTop)

        button_box = QVBoxLayout()
        button_box.setAlignment(Qt.AlignVCenter)
        self.btn_trocar_programa = QPushButton("TROCAR PROGRAMA (F3)")
        self.btn_trocar_programa.clicked.connect(self.trocar_programa)
        self.btn_trocar_programa.setFixedSize(280, 70)
        self.btn_trocar_programa.setStyleSheet(f"""
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
        """)
        button_box.addWidget(self.btn_trocar_programa, alignment=Qt.AlignVCenter)
        troca_preview_row.addLayout(button_box)

        preview_box = QVBoxLayout()
        preview_box.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        lbl_preview = QLabel("PREVIEW DA MARCAÇÃO")
        lbl_preview.setAlignment(Qt.AlignHCenter)
        lbl_preview.setStyleSheet(f"""
            color:{CINZA_CLARO};
            font-size:20px;
        """)
        lbl_preview.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        preview_box.addWidget(lbl_preview, alignment=Qt.AlignHCenter)

        self.preview_area = QLabel("SEM IMAGEM DISPONÍVEL")
        self.preview_area.setAlignment(Qt.AlignCenter)
        self.preview_area.setWordWrap(True)
        self.preview_area.setStyleSheet(f"""
            color:{BRANCO};
            background:{CINZA_ESCURO};
            border:2px solid {CINZA_CLARO};
            border-radius:6px;
            font-size:21px;
        """)
        self.preview_area.setFixedSize(140, 140)
        self.preview_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        preview_box.addWidget(self.preview_area, alignment=Qt.AlignHCenter)
        preview_box.setSpacing(8)
        troca_preview_row.addLayout(preview_box)
        troca_preview_row.setAlignment(preview_box, Qt.AlignVCenter)

        lado_direito.addLayout(troca_preview_row)
        lado_direito.addSpacing(0)

        lbl_peca = QLabel("POSICIONAMENTO DA PEÇA")
        lbl_peca.setAlignment(Qt.AlignCenter)
        lbl_peca.setStyleSheet(f"""
            color:{CINZA_CLARO};
            font-size:24px;
        """)
        lado_direito.addWidget(lbl_peca)

        self.peca_area = QLabel("SEM IMAGEM DISPONÍVEL")
        self.peca_area.setAlignment(Qt.AlignCenter)
        self.peca_area.setWordWrap(True)
        self.peca_area.setStyleSheet(f"""
            color:{BRANCO};
            background:{CINZA_ESCURO};
            border:2px solid {CINZA_CLARO};
            border-radius:12px;
            font-size:20px;
        """)
        self.peca_area.setMinimumHeight(320)
        self.peca_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lado_direito.addWidget(self.peca_area)
        lado_direito.addStretch()

        conteudo_principal.addLayout(lado_direito, 1)
        conteudo_principal.setStretch(0, 1)
        conteudo_principal.setStretch(1, 1)
        conteudo_principal.setSpacing(20)
        layout.addLayout(conteudo_principal)
        layout.setStretch(1, 1)
        layout.addSpacing(0)

        # RODAPÉ
        rodape_widget = QWidget()
        #rodape_widget.setStyleSheet(f"background:{CINZA_ESCURO};")
        rodape = QHBoxLayout(rodape_widget)
        rodape.setContentsMargins(20, 10, 20, 10)
        self.info_rodape = QLabel()
        self.info_rodape.setStyleSheet(f"""
            color:{CINZA_CLARO};
            font-size:26px;
        """)
        self.info_rodape.setText(f"PEÇAS HOJE: {self.contador_dia}")
        autor = QLabel(
            "FUNDIMIG\n"
            "SISTEMA DE RASTREABILIDADE\n"
            "v1.0.0"
        )
        autor.setAlignment(Qt.AlignRight)
        autor.setStyleSheet(f"""
            color:{CINZA_MEDIO};
            font-size:16px;
        """)
        rodape.addWidget(self.info_rodape)
        rodape.addStretch()
        rodape.addWidget(autor)
        layout.addWidget(rodape_widget)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.atualizar_relogio)
        self.timer.start(1000)
        self.atualizar_relogio()

        self.shortcut_enter = QShortcut(QKeySequence("Return"), self)
        self.shortcut_enter.activated.connect(self.acao_enter)
        self.shortcut_enter2 = QShortcut(QKeySequence("Enter"), self)
        self.shortcut_enter2.activated.connect(self.acao_enter)
        self.shortcut_f2 = QShortcut(QKeySequence("F2"), self)
        self.shortcut_f2.activated.connect(self.entrar_modo_edicao)
        QShortcut(QKeySequence("F3"), self, self.trocar_programa)
        QShortcut(QKeySequence("Escape"), self, self.close)

        self.atualizar_programa_selecionado(self.programa_atual)
        self.atualizar_modo_programa()

    def programa_automatico(self):
        return (
            self.programa_atual.upper()
            in PROGRAMAS_AUTOMATICOS
        )

    def atualizar_modo_programa(self):
        if self.programa_automatico():
            self.lbl_codigo.hide()
            self.codigo.hide()
            self.btn_alterar.hide()
            self.lbl_modo_automatico.show()
            self.texto_contador.setText("PEÇAS BOSCH127")
            self.codigo.setReadOnly(True)
            self.shortcut_f2.setEnabled(False)
            self.lbl_contador.setText(str(self.contador_bosch))
        else:
            self.lbl_codigo.show()
            self.codigo.show()
            self.btn_alterar.show()
            self.lbl_modo_automatico.hide()
            self.texto_contador.setText("PEÇAS DESTE CÓDIGO")
            self.shortcut_f2.setEnabled(True)
            self.codigo.setText(ler_codigo())
            self.contador_codigo = ler_contador_codigo()
            self.lbl_contador.setText(str(self.contador_codigo))

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
            self.status.setText("🔴 SENHA INCORRETA")
            QTimer.singleShot(1500, self.reset_status)

    def closeEvent(self, event):
        senha, ok = QInputDialog.getText(
            self,
            "Acesso Restrito",
            "Digite a senha:",
            QLineEdit.Password,
        )
        if ok and senha == "123":
            event.accept()
        else:
            event.ignore()

    def animar_status(self):
        if self.status.text() != "🟢 PRONTO PARA MARCAR":
            return
        if self.pulso_status:
            self.status.setStyleSheet(f"""
                color:{VERDE};
                font-size:32px;
                font-weight:bold;
            """)
        else:
            self.status.setStyleSheet(f"""
                color:{VERDE_CLARO};
                font-size:32px;
                font-weight:bold;
            """)
        self.pulso_status = not self.pulso_status

    def entrar_modo_edicao(self):
        if self.programa_automatico():
            self.status.setText("⚠️ PROGRAMA AUTOMÁTICO")
            return

        self.codigo.setStyleSheet(f"""
        QLineEdit{{
            background-color:{CINZA_ESCURO};
            border:4px solid {AMARELO};
            border-radius:15px;
            color:{BRANCO};
            font-size:150px;
            font-weight:bold;
        }}
        """)
        self.modo_edicao = True
        self.codigo.setReadOnly(False)
        self.codigo.setFocus()
        self.codigo.selectAll()
        try:
            self.codigo.returnPressed.disconnect()
        except:
            pass
        self.codigo.returnPressed.connect(self.salvar_novo_codigo)
        self.btn_confirmar.setText("SALVAR")
        self.btn_alterar.setText("CANCELAR")
        try:
            self.btn_confirmar.clicked.disconnect()
        except:
            pass
        self.btn_confirmar.clicked.connect(self.salvar_novo_codigo)
        try:
            self.btn_alterar.clicked.disconnect()
        except:
            pass
        self.btn_alterar.clicked.connect(self.cancelar_edicao)
        self.status.setText("🟡 DIGITE O NOVO CÓDIGO")

    def cancelar_edicao(self):
        self.codigo.setText(ler_codigo())
        self.sair_modo_edicao()

    def salvar_novo_codigo(self):
        novo_codigo = self.codigo.text().strip().upper()
        if len(novo_codigo) != 6:
            self.status.setText("🔴 CÓDIGO DEVE TER 6 LETRAS")
            self.erro_codigo()
            return
        antigo = ler_codigo()
        if novo_codigo != antigo:
            salvar_codigo(novo_codigo)
            registrar_alteracao(antigo, novo_codigo)
            self.contador_codigo = 0
            salvar_contador_codigo(0)
            self.lbl_contador.setText("0")
        self.sair_modo_edicao()

    def sair_modo_edicao(self):
        self.codigo.setStyleSheet(f"""
        QLineEdit{{
            background: transparent;
            border:none;
            color:{AZUL};
            font-size:150px;
            font-weight:bold;
        }}
        """)
        try:
            self.codigo.returnPressed.disconnect()
        except:
            pass
        self.modo_edicao = False
        self.codigo.setReadOnly(True)
        self.btn_confirmar.clicked.disconnect()
        self.btn_confirmar.clicked.connect(self.confirmar)
        self.btn_alterar.clicked.disconnect()
        self.btn_alterar.clicked.connect(self.entrar_modo_edicao)
        self.btn_confirmar.setText("CONFIRMAR(ENTER)")
        self.btn_alterar.setText("ALTERAR CÓDIGO(F2)")
        self.status.setText("🟢 PRONTO PARA MARCAR")

    def acao_enter(self):
        if self.modo_edicao:
            self.salvar_novo_codigo()
        else:
            self.confirmar()

    def erro_codigo(self):
        self.status.setText("🔴 CÓDIGO INVÁLIDO")
        self.piscar_vermelho_1()

    def piscar_vermelho_1(self):
        self.setStyleSheet(f"""
            QWidget{{
                background:{VERMELHO};
                color:white;
            }}
        """)
        QTimer.singleShot(150, self.piscar_preto_1)

    def piscar_preto_1(self):
        self.setStyleSheet(f"""
            QWidget{{
                background:{CINZA_ESCURO};
                color:white;
            }}
        """)
        QTimer.singleShot(150, self.piscar_vermelho_2)

    def piscar_vermelho_2(self):
        self.setStyleSheet(f"""
            QWidget{{
                background:{VERMELHO};
                color:white;
            }}
        """)
        QTimer.singleShot(150, self.restaurar_erro)

    def restaurar_erro(self):
        self.setStyleSheet(f"""
            QWidget{{
                background:{CINZA_ESCURO};
                color:white;
            }}
        """)
        self.codigo.setStyleSheet(f"""
            QLineEdit{{
                background-color:{CINZA_ESCURO};
                border:4px solid {AMARELO};
                border-radius:15px;
                color:white;
                font-size:150px;
                font-weight:bold;
            }}
        """)
        self.status.setText("🟡 DIGITE O NOVO CÓDIGO")
        self.codigo.setFocus()

    def converter_maiusculo(self):
        texto = self.codigo.text()
        cursor = self.codigo.cursorPosition()
        self.codigo.blockSignals(True)
        self.codigo.setText(texto.upper())
        self.codigo.setCursorPosition(cursor)
        self.codigo.blockSignals(False)

    def atualizar_relogio(self):
        agora = datetime.now()
        self.relogio.setText(agora.strftime("%d/%m/%Y\n%H:%M:%S"))

    def trocar_programa(self):
        programas = listar_programas_ezd()
        if not programas:
            self.status.setText("🔴 NENHUM PROGRAMA .EZD ENCONTRADO")
            QTimer.singleShot(1500, self.reset_status)
            return

        dialog = SeletorProgramaDialog(self, programas, self.programa_atual)
        if dialog.exec() != QDialog.Accepted:
            return

        novo_programa = dialog.selected_programa()
        if not novo_programa:
            return

        if novo_programa == self.programa_atual:
            return

        aviso = AvisoFocoDialog(self)
        aviso.exec()

        antigo_programa = self.programa_atual if self.programa_atual else "SEM PROGRAMA"
        salvar_programa_atual(novo_programa)
        self.atualizar_programa_selecionado(novo_programa)
        registrar_troca_programa(antigo_programa, novo_programa)
        self.status.setText("🟡 TROCA INICIADA EM SEGUNDO PLANO")
        self.status.setStyleSheet("""
            color:yellow;
            font-size:32px;
            font-weight:bold;
        """)
        Thread(target=carregar_programa_ezd, args=(novo_programa,), daemon=True).start()

        QTimer.singleShot(
            2000,
            self.reset_status
        )

    def atualizar_programa_selecionado(self, programa_nome):
        anterior = self.programa_atual
        self.programa_atual = programa_nome or ""
        programa = self.programa_atual if self.programa_atual else "SEM PROGRAMA SELECIONADO"
        html = (
            f"<span style=\"color:{CINZA_CLARO}; font-size:28px;\">PROGRAMA ATUAL:</span> "
            f"<span style=\"color:{AZUL}; font-weight:bold; font-size:28px;\">{programa}</span>"
        )
        self.lbl_programa_nome.setTextFormat(Qt.RichText)
        self.lbl_programa_nome.setText(html)
        self.atualizar_preview()
        if self.programa_automatico() and anterior != self.programa_atual:
            self.contador_bosch = 0
            salvar_contador_bosch127(self.contador_bosch)
        self.atualizar_modo_programa()

    def atualizar_preview(self):
        self.preview_pixmap = None
        self.peca_pixmap = None
        if self.programa_atual:
            preview_path = obter_caminho_programa(self.programa_atual).with_suffix(".png")
            peca_path = Path(PASTA_PROGRAMAS) / f"{Path(self.programa_atual).stem}_setup.png"

            if preview_path.exists():
                pixmap = QPixmap(str(preview_path))
                if not pixmap.isNull():
                    self.preview_pixmap = pixmap
                    self._atualizar_preview_pixmap()
                else:
                    self.preview_area.setPixmap(QPixmap())
                    self.preview_area.setText("SEM IMAGEM DISPONÍVEL")
            else:
                self.preview_area.setPixmap(QPixmap())
                self.preview_area.setText("SEM IMAGEM DISPONÍVEL")

            if peca_path.exists():
                pixmap = QPixmap(str(peca_path))
                if not pixmap.isNull():
                    self.peca_pixmap = pixmap
                    self._atualizar_peca_pixmap()
                else:
                    self.peca_area.setPixmap(QPixmap())
                    self.peca_area.setText("SEM IMAGEM DISPONÍVEL")
            else:
                self.peca_area.setPixmap(QPixmap())
                self.peca_area.setText("SEM IMAGEM DISPONÍVEL")
            return

        self.preview_area.setPixmap(QPixmap())
        self.preview_area.setText("SEM IMAGEM DISPONÍVEL")
        self.peca_area.setPixmap(QPixmap())
        self.peca_area.setText("SEM IMAGEM DISPONÍVEL")

    def _atualizar_preview_pixmap(self):
        if not self.preview_pixmap:
            return
        area = self.preview_area.size()
        if area.width() < 10 or area.height() < 10:
            area = QSize(360, 150)
        scaled = self.preview_pixmap.scaled(area, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_area.setPixmap(scaled)
        self.preview_area.setText("")

    def _atualizar_peca_pixmap(self):
        if not self.peca_pixmap:
            return
        area = self.peca_area.size()
        if area.width() < 10 or area.height() < 10:
            area = QSize(860, 420)
        scaled = self.peca_pixmap.scaled(area, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.peca_area.setPixmap(scaled)
        self.peca_area.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.preview_pixmap:
            self._atualizar_preview_pixmap()
        if self.peca_pixmap:
            self._atualizar_peca_pixmap()

    def confirmar(self):
        self.contador_dia += 1
        salvar_contador_dia(self.contador_dia)
        if self.programa_automatico():
            self.contador_bosch += 1
            salvar_contador_bosch127(self.contador_bosch)
            atualizar_producao_codigo(self.programa_atual, self.contador_bosch)
            self.lbl_contador.setText(str(self.contador_bosch))
        else:
            self.contador_codigo += 1
            salvar_contador_codigo(self.contador_codigo)
            atualizar_producao_codigo(self.codigo.text(), self.contador_codigo)
            self.lbl_contador.setText(str(self.contador_codigo))
        self.info_rodape.setText(f"PEÇAS HOJE: {self.contador_dia}")
        self.status.setText("✅ PEÇA CONFIRMADA")
        self.status.setStyleSheet("""
            color:white;
            font-size:40px;
            font-weight:bold;
        """)
        self.setStyleSheet(f"""
            QWidget{{
                background-color:{VERDE_CLARO};
                color:white;
            }}
        """)
        QTimer.singleShot(800, self.reset_status)

    def reset_status(self):
        self.setStyleSheet(f"""
            QWidget{{
                background-color:{CINZA_ESCURO};
                color:white;
            }}
        """)
        self.status.setText("🟢 PRONTO PARA MARCAR")
        self.status.setStyleSheet(f"""
            color:{VERDE};
            font-size:32px;
            font-weight:bold;
        """)
        self.btn_confirmar.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = JanelaPrincipal()
    janela.showFullScreen()
    sys.exit(app.exec())
