# Firmware MicroGrav V0.1

## Objetivo e segurança

Esta é a primeira versão operacional segura do controlador da MicroGrav M20. Ela captura uma imagem nova da OV2640, executa o modelo Edge Impulse v2 e pede confirmação humana no LCD. A identificação nunca inicia marcação automaticamente.

Os dois programas do catálogo começam com:

```text
configured = false
validatedForProduction = false
```

Consequentemente, esta versão não envia parâmetros nem o comando START à M20, mesmo depois da confirmação do operador. Não existem parâmetros fictícios de marcação.

## Fluxo operacional

```text
BOOTING -> SELF_TEST -> READY

READY
  START -> CAPTURING -> IDENTIFYING
    falha -> ERROR -> RESET ou START -> nova captura
    sucesso -> WAITING_CONFIRMATION

WAITING_CONFIRMATION
  RESET -> descarta resultado -> CAPTURING -> nova imagem -> nova inferência
  START -> PREPARING_MARKING
    programa não validado -> bloqueia marcação e aguarda RESET
    programa futuro validado -> envia programa -> START M20 -> MARKING

MARKING -> E03 -> VERIFYING -> E05 -> COMPLETED -> READY
```

Se RESET e START forem detectados no mesmo ciclo, RESET tem prioridade.

## Máquina de estados

Estados implementados em `ApplicationState`:

```text
Booting
SelfTest
Ready
Capturing
Identifying
WaitingConfirmation
PreparingMarking
Marking
Verifying
Completed
Error
```

Não existe estado de iluminação.

## Botoeiras e GPIOs

| Função | GPIO | Configuração | Justificativa |
|---|---:|---|---|
| START | 14 | `INPUT_PULLUP`, pressionada em LOW | Exposto, não usado pela OV2640, SD, USB, PSRAM, I2C ou UART; não é strapping pin. |
| RESET operacional | 21 | `INPUT_PULLUP`, pressionada em LOW | Exposto; o conector SPI-LCD não é usado; não é strapping pin e não conflita com o LCD I2C. |

Ligação recomendada para cada botão:

```text
GPIO ---- botoeira normalmente aberta ---- GND
```

O debounce é de 50 ms e usa `millis()`, sem espera bloqueante. Um botão mantido pressionado produz apenas um evento; um novo evento exige liberação e novo pressionamento.

O RESET desta aplicação não chama `ESP.restart()` e não é o pino EN da placa.

## Mapa de periféricos

| Periférico | GPIOs |
|---|---|
| OV2640 | 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18 |
| microSD SDMMC 1-bit | D0=38, CLK=39, CMD=40 |
| USB nativo | D+=19, D-=20 |
| LCD 20x4 I2C | SDA=1, SCL=2 |
| START | 14 |
| RESET operacional | 21 |
| RS232 UART1 | TX=41, RX=42, CTS=47, RTS=43 |

GPIO26–37 não são usados porque a variante N16R8 usa barramento octal de Flash/PSRAM. GPIO0, GPIO3, GPIO45 e GPIO46 foram evitados para as botoeiras por serem strapping pins.

GPIO43 está ligado também à entrada RX do conversor USB-UART CH343 da placa. Na aplicação ele é saída RTS e encontra apenas entradas, sem disputa elétrica. Os logs usam o USB nativo em GPIO19/20. Pode haver atividade de boot ROM em GPIO43 antes da aplicação assumir o RTS; isso deve ser verificado com o transceptor final.

## Câmera

`Ov2640Camera` preserva a configuração funcional existente:

```text
JPEG
UXGA 1600x1200
quality = 4
1 framebuffer
framebuffer em PSRAM
```

`CapturedImage` expõe somente dados, tamanho, dimensões e formato. `camera_fb_t` permanece interno ao driver e a imagem é sempre devolvida à câmera depois da inferência.

## Visão e Edge Impulse

Somente `EdgeImpulsePartIdentifier.cpp` inclui `Micropulsionador_inferencing.h`.

Validações de compilação:

```cpp
EI_CLASSIFIER_INPUT_WIDTH == 160
EI_CLASSIFIER_INPUT_HEIGHT == 160
EI_CLASSIFIER_RESIZE_MODE == EI_CLASSIFIER_RESIZE_FIT_LONGEST
EI_CLASSIFIER_OBJECT_DETECTION == 1
EI_HAS_FOMO == 1
```

Pipeline:

```text
JPEG 1600x1200
-> RGB888 em PSRAM
-> resize oficial do SDK EI com FIT_LONGEST
-> 160x120 centralizado e padding preto até 160x160
-> signal_t em 0xRRGGBB
-> grayscale/quantização internos
-> run_classifier
-> boxes FOMO 031/045
```

Política V0.1:

```text
zero boxes -> falha
uma classe -> usa a melhor box da classe
duas classes -> registra ambas e escolhe a maior confiança
confidence < 0.50 -> falha
```

Não há ROI nesta versão.

Dois buffers previsíveis são alocados uma vez na PSRAM durante o boot: 5.760.000 bytes para RGB888 UXGA e 76.800 bytes para a entrada 160x160 RGB888. Não há alocação desses buffers no loop de produção.

## LCD 20x4

O driver usa diretamente o backpack PCF8574 comum no endereço configurável `0x27`, com mapeamento P0=RS, P1=RW, P2=EN, P3=backlight e P4..P7=dados. O barramento usa 100 kHz.

Telas principais:

```text
SISTEMA PRONTO
COLOQUE A PECA
PRESSIONE START

PECA: 031
CONF: 99.6%
START: MARCAR
RESET: RELER

PECA CONFIRMADA
PROGRAMA NAO
CONFIGURADO
RESET: RELER
```

Se o backpack tiver endereço ou mapeamento diferente, apenas a configuração/driver de display deverá ser adaptado.

## microSD

O cartão é inicializado em SDMMC 1-bit. Na V0.1 ele é opcional e reservado para persistência/logs futuros; ausência do cartão gera log `[HW]` mas não impede identificação e confirmação.

## RS232

Configuração confirmada no manual MicroGrav M20, páginas 30–37:

```text
57600 baud
8 data bits
sem paridade
1 stop bit
RTS/CTS
```

É obrigatório usar transceptor RS232 compatível com lógica de 3,3 V. Nunca conectar níveis RS232 diretamente ao ESP32-S3.

## Protocolo MicroGrav M20

Builders possuem capacidade fixa de 128 bytes e retornam `OperationResult<ProtocolFrame>`. Foram implementados:

```text
memoryClear, selectBlock, selectLinear, selectCircular, selectPlot,
select2D, selectFont, setX, setY, setAngle, setSpacing, setHeight,
setMarkingData, nextBlock, reset, start, stop e query
```

Frames fundamentais verificados no auto teste:

```text
memoryClear: 1B 40 3B
linear:      1B 47 31 3B
start:       1B 21 3B
stop:        18
```

O parser reconhece:

```text
1B 45 30 33 3B -> MarkingFinished
1B 45 30 35 3B -> CountFinished
1B 45 31 32 3B -> OutOfArea
1B 45 31 38 3B -> MotorOrDriveFault
```

## Logs USB

USB CDC em 115200 baud, com prefixos:

```text
[BOOT] [HW] [BUTTON] [CAMERA] [VISION] [APP] [MARKING] [ERROR]
```

O boot também registra Flash, PSRAM, heap livre e PSRAM livre detectadas fisicamente.

## Como compilar

```powershell
pio run
```

O environment padrão é `goouuu-esp32-s3-cam`. O antigo `ei-smoke-test` permanece isolado e seleciona a biblioteca antiga; o firmware principal seleciona somente a biblioteca v2 armazenada em `lib/EIv2`.

## Testes físicos

1. Conferir alimentação, GND comum e transceptor RS232; manter a M20 incapaz de marcar durante a validação inicial.
2. Confirmar no log Flash=16 MB e PSRAM aproximadamente 8 MB.
3. Em READY, pressionar e manter START: deve ocorrer somente uma captura.
4. Em WAITING_CONFIRMATION, pressionar RESET: o resultado anterior deve ser descartado e o log deve mostrar nova captura JPEG.
5. Repetir com 031 e 045.
6. Sem peça, confirmar que nenhuma marcação ocorre. Mesmo um falso positivo exige segundo START e ainda é bloqueado pelo catálogo.
7. Pressionar o segundo START após uma identificação: deve aparecer `PROGRAMA NAO CONFIGURADO` e nenhum frame deve ser transmitido à M20.

## Limitações da V0.1

- Programas 031 e 045 não possuem parâmetros reais e não estão validados.
- Marcação real é deliberadamente impossível.
- A ROI candidata não foi implementada.
- O decoder JPEG usa um buffer RGB888 UXGA grande, adequado à PSRAM disponível, mas deverá ser otimizado depois da validação funcional.
- Endereço e mapeamento do backpack LCD precisam corresponder ao hardware real.
- Pinagem RTS/CTS e polaridade precisam ser confirmadas com o transceptor e cabo definitivos.
- microSD ainda não armazena logs, imagens ou configurações.
- Não há persistência NVS nesta versão.
