# Auditoria visual dos 45 casos problemáticos — DetectaIA2.0

## 1. Total analisado

- SEM_DETECCAO: 27
- AMBIGUA: 18
- TOTAL: 45
- Todos os 45 previews 160x160 foram regenerados com o mesmo Q14/FIT_LONGEST e tiveram CRC32 idêntico ao lote físico.

## 2. Distribuição das causas

| Causa | 031 | 045 | Total |
|---|---:|---:|---:|
| PECA_FORA_POSICAO | 0 | 0 | 0 |
| PECA_ROTACIONADA | 11 | 0 | 11 |
| OCLUSAO_MAO | 10 | 1 | 11 |
| OCLUSAO_OBJETO | 0 | 0 | 0 |
| REFLEXO_ILUMINACAO | 0 | 0 | 0 |
| DESFOQUE_MOVIMENTO | 2 | 0 | 2 |
| FUNDO_INTERFERINDO | 0 | 0 | 0 |
| BOX_ESPURIA_FORA_PECA | 0 | 4 | 4 |
| MODELO_FALHOU_COM_PECA_BEM_VISIVEL | 4 | 12 | 16 |
| INDETERMINADO | 0 | 1 | 1 |

## 3. Casos 031 sem detecção

- Oclusão pela mão (9): `031/foto0170.jpg`, `031/foto0174.jpg`, `031/foto0175.jpg`, `031/foto0176.jpg`, `031/foto0213.jpg`, `031/foto0214.jpg`, `031/foto0234.jpg`, `031/foto0253.jpg`, `031/foto0284.jpg`
- Peça rotacionada (11): `031/foto0237.jpg`, `031/foto0238.jpg`, `031/foto0239.jpg`, `031/foto0265.jpg`, `031/foto0268.jpg`, `031/foto0269.jpg`, `031/foto0270.jpg`, `031/foto0271.jpg`, `031/foto0272.jpg`, `031/foto0273.jpg`, `031/foto0274.jpg`
- Desfoque de movimento (2): `031/foto0266.jpg`, `031/foto0267.jpg`
- Peça bem visível/modelo falhou (4): `031/foto0286.jpg`, `031/foto0287.jpg`, `031/foto0288.jpg`, `031/foto0290.jpg`
- O padrão dominante é captura fora da condição nominal, mas quatro falhas permanecem com peça nítida e visível.

## 4. Casos 045 sem detecção

- `045/foto0062.jpg`: o JPEG está truncado/corrompido. Apenas uma faixa superior contém dados; o restante é cinza. A ausência de detecção não deve ser usada como evidência contra o modelo.

## 5. Ambiguidades 031

- Arquivo: `031/foto0263.jpg`
- Confidence correta 031: 0.992188
- Confidence incorreta 045: 0.921875
- Delta: 0.070313
- Box correta: 031 0.992188 [x=72,y=88,w=16,h=8] SOBRE_PECA
- Box incorreta: 045 0.921875 [x=80,y=96,w=8,h=8] SOBRE_PECA
- Ambas estão sobre a peça; há mão dentro da abertura e leve borramento.

## 6. Ambiguidades 045

| Arquivo | Conf 045 | Conf 031 | Delta | Box 045 | Box 031 | Observação |
|---|---:|---:|---:|---|---|---|
| 045/foto0137.jpg | 0.996094 | 0.582031 | 0.414063 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.582031 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça montada, nítida e sem oclusão; a box 031 está sobre a própria peça. |
| 045/foto0139.jpg | 0.996094 | 0.582031 | 0.414063 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.582031 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça montada e nítida; a box 031 está sobre a mesma região superior da peça. |
| 045/foto0142.jpg | 0.996094 | 0.539062 | 0.457032 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.539062 [x=88,y=72,w=8,h=8] SOBRE_PECA | Mão está acima sem cobrir a região detectada; ambas as boxes estão sobre a peça. |
| 045/foto0144.jpg | 0.996094 | 0.625000 | 0.371094 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.625000 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça bem visível; a ativação 031 ocorre sobre o colar superior da própria peça. |
| 045/foto0145.jpg | 0.996094 | 0.542969 | 0.453125 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.542969 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça montada e sem oclusão; ambas as classes ativam regiões adjacentes da peça. |
| 045/foto0148.jpg | 0.996094 | 0.500000 | 0.496094 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.500000 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça bem visível e estática; box 031 sobre a própria peça. |
| 045/foto0149.jpg | 0.996094 | 0.660156 | 0.335938 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.660156 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça bem visível e estática; box 031 sobre a própria peça. |
| 045/foto0150.jpg | 0.996094 | 0.582031 | 0.414063 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.582031 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça bem visível e estática; box 031 sobre a própria peça. |
| 045/foto0152.jpg | 0.996094 | 0.500000 | 0.496094 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.500000 [x=88,y=72,w=8,h=8] SOBRE_PECA | Mão está distante da região detectada; a box 031 permanece sobre a peça. |
| 045/foto0153.jpg | 0.996094 | 0.625000 | 0.371094 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.625000 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça montada e sem oclusão; box 031 sobre o colar superior. |
| 045/foto0154.jpg | 0.996094 | 0.582031 | 0.414063 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.582031 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça montada e sem oclusão; box 031 sobre o colar superior. |
| 045/foto0157.jpg | 0.996094 | 0.500000 | 0.496094 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.500000 [x=88,y=72,w=8,h=8] SOBRE_PECA | Peça montada e sem oclusão; a box incorreta está sobre a própria peça. |
| 045/foto0173.jpg | 0.996094 | 0.660156 | 0.335938 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA; 045 0.546875 [x=88,y=104,w=8,h=8] SOBRE_PECA | 031 0.625000 [x=80,y=96,w=8,h=8] SOBRE_MAO; 031 0.660156 [x=80,y=120,w=8,h=8] SOBRE_MAO | Mão cobre grande parte do lado esquerdo; duas boxes 031 aparecem sobre a mão. |
| 045/foto0198.jpg | 0.996094 | 0.585938 | 0.410156 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.585938 [x=104,y=32,w=8,h=8] SOBRE_MAO | A detecção 045 está na peça; a box 031 está sobre um dedo acima da peça. |
| 045/foto0211.jpg | 0.996094 | 0.867188 | 0.128906 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.867188 [x=112,y=40,w=8,h=8] SOBRE_MAO | A box 031 está sobre a ponta do dedo, espacialmente separada da peça. |
| 045/foto0234.jpg | 0.996094 | 0.542969 | 0.453125 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.542969 [x=104,y=40,w=8,h=8] SOBRE_MAO | A box 031 está sobre o dedo acima/direita da peça. |
| 045/foto0238.jpg | 0.996094 | 0.765625 | 0.230469 | 045 0.996094 [x=88,y=80,w=8,h=16] SOBRE_PECA | 031 0.765625 [x=112,y=40,w=8,h=8] SOBRE_MAO | A box 031 está sobre o dedo acima/direita da peça. |

Estatística do delta correto-incorreto nas 17 ambiguidades 045:

- Mínimo: 0.128906
- Média: 0.393612
- Mediana: 0.414063
- Máximo: 0.496094

Nas 18 ambiguidades totais: mínimo 0.070313; média 0.375651; mediana 0.414063; máximo 0.496094.

## 7. Boxes espúrias

- Sobre mão: 6
- Sobre fundo: 0
- Sobre fixação: 0
- Sobre a própria peça: 13
- Outras/indeterminadas: 0
- Foram avaliadas 19 boxes de classe incorreta: 13 sobre a própria peça e 6 sobre a mão.

## 8. Casos realmente preocupantes

- `031/foto0286.jpg` — Peça nítida, centralizada e praticamente sem oclusão; falha não explicada pela captura.
- `031/foto0287.jpg` — Peça nítida, centralizada e praticamente sem oclusão; falha não explicada pela captura.
- `031/foto0288.jpg` — Peça nítida e bem enquadrada, com mão apenas na periferia.
- `031/foto0290.jpg` — Peça nítida e bem posicionada no campo, sem oclusão relevante das características principais.
- Além desses quatro falsos negativos, 12 ambiguidades 045 mostram a peça montada e nítida, com a box 031 sobre a própria peça.

## 9. ROI

ROI POTENCIALMENTE ÚTIL: SIM

- Região candidata apenas para estudo: `x=64..104`, `y=80..120` no frame 160x160.
- Ela contém 575/581 boxes corretas do lote (98.97%).
- Contém 19/19 boxes corretas dos casos ambíguos.
- Rejeitaria geometricamente 17/19 boxes incorretas observadas nas ambiguidades.
- Isso eliminaria sobretudo boxes 031 em y=72 e boxes sobre a mão em y=32..40. Não resolveria as duas ativações incorretas que permanecem dentro da região central.
- A ROI foi inferida do mesmo conjunto de validação; não deve ser adotada sem uma validação separada e sem regra de segurança.

## 10. Conclusão

RESULTADO MISTO

As falhas 031 são majoritariamente associadas a oclusão, rotação e movimento, mas existem quatro falsos negativos com captura adequada. Nas ambiguidades 045, a classe correta é sempre dominante em confiança, porém 13 boxes incorretas estão sobre a própria peça e seis sobre a mão. Há fragilidade real do modelo e também forte influência da condição de captura. Uma ROI parece capaz de remover grande parte das boxes espúrias, mas não todas.

## 11. Próxima ação

Definir e validar uma ROI/política segura usando um conjunto separado, sem alterar o modelo nem integrar ainda a câmera ao fluxo de produção.
