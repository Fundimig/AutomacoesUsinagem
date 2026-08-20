# Simulação retrospectiva de políticas — DetectaIA2.0

## 1. Validação dos dados de entrada

- 031 corretas: 281
- 045 corretas: 292
- Sem detecção: 27
- Ambíguas: 18
- Total: 618
- O baseline reproduziu exatamente os números consolidados; a grade foi executada.

## 2. Metodologia

- ROI_CENTER: aceita a box quando seu centro está dentro de x=64..104 e y=80..120.
- ROI_INTERSECTION_50: aceita quando pelo menos 50% da área da box intersecta a ROI.
- O minimumVisionConfidence é aplicado somente depois da ROI e não altera o threshold FOMO interno 0.5.
- Para cada classe permanece o maior score. Quando ambas permanecem, delta=abs(best031-best045); delta menor que a margem gera REJECT_AMBIGUOUS.
- Ausência de box nunca é convertida em classificação. Box existente, mas removida integralmente pela ROI, resulta em REJECT_NO_DETECTION; remoção apenas pela confiança resulta em REJECT_LOW_CONFIDENCE.

## 3. Baseline

- Classificação bruta: 573 CORRETAS, 27 SEM_DETECCAO e 18 AMBIGUAS; taxa correta global bruta 92,72%.

## 4. Cenário A — Modelo bruto

- Política: `NONE_C0.50_M0.00`
- Correct=591, Wrong=0, NoDetection=27, LowConfidence=0, Ambiguous=0, Coverage=95.63%, AcceptedAccuracy=100.00%
- Sem a imagem corrompida: Correct=591, Wrong=0, NoDetection=26, LowConfidence=0, Ambiguous=0, Coverage=95.79%, AcceptedAccuracy=100.00%

## 5. Cenário B — Apenas ROI

- Política: `ROI_CENTER_C0.50_M0.00`
- Correct=590, Wrong=0, NoDetection=28, LowConfidence=0, Ambiguous=0, Coverage=95.47%, AcceptedAccuracy=100.00%
- Sem a imagem corrompida: Correct=590, Wrong=0, NoDetection=27, LowConfidence=0, Ambiguous=0, Coverage=95.62%, AcceptedAccuracy=100.00%

## 6. Cenário C — ROI + confidence 0.90

- Política: `ROI_CENTER_C0.90_M0.00`
- Correct=581, Wrong=0, NoDetection=28, LowConfidence=9, Ambiguous=0, Coverage=94.01%, AcceptedAccuracy=100.00%
- Sem a imagem corrompida: Correct=581, Wrong=0, NoDetection=27, LowConfidence=9, Ambiguous=0, Coverage=94.17%, AcceptedAccuracy=100.00%

## 7. Cenário D — ROI + confidence 0.90 + margin 0.10

- Política: `ROI_CENTER_C0.90_M0.10`
- Correct=580, Wrong=0, NoDetection=28, LowConfidence=9, Ambiguous=1, Coverage=93.85%, AcceptedAccuracy=100.00%
- Sem a imagem corrompida: Correct=580, Wrong=0, NoDetection=27, LowConfidence=9, Ambiguous=1, Coverage=94.00%, AcceptedAccuracy=100.00%

## 8. Cenário E — Política muito conservadora

- Política: `ROI_CENTER_C0.95_M0.15`
- Correct=574, Wrong=0, NoDetection=28, LowConfidence=16, Ambiguous=0, Coverage=92.88%, AcceptedAccuracy=100.00%
- Sem a imagem corrompida: Correct=574, Wrong=0, NoDetection=27, LowConfidence=16, Ambiguous=0, Coverage=93.03%, AcceptedAccuracy=100.00%

## 9. Top 15

| ROI | MinConfidence | MinMargin | CorrectAccept | WrongAccept | NoDetection | LowConfidence | Ambiguous | Coverage | AcceptedAccuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| NONE | 0.50 | 0.00 | 591 | 0 | 27 | 0 | 0 | 95.63% | 100.00% |
| NONE | 0.50 | 0.05 | 591 | 0 | 27 | 0 | 0 | 95.63% | 100.00% |
| NONE | 0.50 | 0.10 | 590 | 0 | 27 | 0 | 1 | 95.47% | 100.00% |
| NONE | 0.60 | 0.00 | 590 | 0 | 27 | 1 | 0 | 95.47% | 100.00% |
| NONE | 0.60 | 0.05 | 590 | 0 | 27 | 1 | 0 | 95.47% | 100.00% |
| ROI_CENTER | 0.50 | 0.00 | 590 | 0 | 28 | 0 | 0 | 95.47% | 100.00% |
| ROI_CENTER | 0.50 | 0.05 | 590 | 0 | 28 | 0 | 0 | 95.47% | 100.00% |
| ROI_INTERSECTION_50 | 0.50 | 0.00 | 590 | 0 | 28 | 0 | 0 | 95.47% | 100.00% |
| ROI_INTERSECTION_50 | 0.50 | 0.05 | 590 | 0 | 28 | 0 | 0 | 95.47% | 100.00% |
| NONE | 0.50 | 0.15 | 589 | 0 | 27 | 0 | 2 | 95.31% | 100.00% |
| NONE | 0.50 | 0.20 | 589 | 0 | 27 | 0 | 2 | 95.31% | 100.00% |
| NONE | 0.60 | 0.10 | 589 | 0 | 27 | 1 | 1 | 95.31% | 100.00% |
| ROI_CENTER | 0.50 | 0.10 | 589 | 0 | 28 | 0 | 1 | 95.31% | 100.00% |
| ROI_CENTER | 0.50 | 0.15 | 589 | 0 | 28 | 0 | 1 | 95.31% | 100.00% |
| ROI_CENTER | 0.50 | 0.20 | 589 | 0 | 28 | 0 | 1 | 95.31% | 100.00% |

## 10. Pareto

- Políticas não dominadas: 2.
- `NONE_C0.50_M0.00` — Wrong=0, AcceptedAccuracy=100.00%, Coverage=95.63%.
- `NONE_C0.50_M0.05` — Wrong=0, AcceptedAccuracy=100.00%, Coverage=95.63%.

## 11. Ambiguidades 045

| Cenário | ACCEPT_045 | REJECT_NO_DETECTION | REJECT_LOW_CONFIDENCE | REJECT_AMBIGUOUS | WRONG_ACCEPT |
|---|---:|---:|---:|---:|---:|
| A | 17 | 0 | 0 | 0 | 0 |
| B | 17 | 0 | 0 | 0 | 0 |
| C | 17 | 0 | 0 | 0 | 0 |
| D | 17 | 0 | 0 | 0 | 0 |
| E | 17 | 0 | 0 | 0 | 0 |

## 12. Ambiguidade 031

- Para confidence de 0.50 a 0.90, margens 0.00 e 0.05 aceitam 031; margens de 0.10 a 0.30 rejeitam como ambígua.
- Em confidence 0.95, a box 045 de 0.921875 é removida e a 031 de 0.992188 é aceita em todas as margens testadas.
- ROI_CENTER e ROI_INTERSECTION_50 não alteram esse caso: ambas as boxes passam pelas duas regras espaciais.

## 13. Falsos negativos

- `031/foto0286.jpg`, `foto0287.jpg`, `foto0288.jpg` e `foto0290.jpg` permaneceram REJECT_NO_DETECTION nas 147 políticas.
- Total verificado: 588/588 decisões fail-safe; nenhuma classificação foi inventada.

## 14. Imagem corrompida

- `045/foto0062.jpg` permaneceu REJECT_NO_DETECTION nas 147 políticas.
- WITH_CORRUPTED_IMAGE usa 618 imagens; WITHOUT_CORRUPTED_IMAGE usa 617. A remoção altera somente o denominador e reduz NoDetection em uma unidade.

## 15. Conclusão

ROI TEM BENEFÍCIO LIMITADO

A ROI remove as boxes secundárias de várias ambiguidades, mas neste conjunto o simples uso do maior score já produz zero WRONG_ACCEPT e maior coverage. A confiança e a margem aumentam rejeições sem melhorar accepted_accuracy, que já é 100% entre os aceites retrospectivos. Isso não demonstra segurança futura: não houve classificações cruzadas brutas neste conjunto.

Esses parâmetros foram avaliados no mesmo conjunto usado para derivar a ROI e analisar os erros. Portanto, não podem ser considerados calibrados para produção.

## 16. Próximo passo

COLETAR CONJUNTO INDEPENDENTE PARA VALIDAR A POLÍTICA
