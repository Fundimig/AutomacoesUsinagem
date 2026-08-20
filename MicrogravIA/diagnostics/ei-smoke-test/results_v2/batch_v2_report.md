# Relatório DetectaIA2.0 — ESP32-S3 físico

## 1. Biblioteca DetectaIA2.0

- Arquivo de origem: `DetectaIA2.0.zip` (SHA-256 `9D50163E39D62E706CE1E155BB572FEE254C22E672272F499F058B077995C81D`).
- Diretório raiz/nome da biblioteca: `Micropulsionador_inferencing`; header: `Micropulsionador_inferencing.h`.
- Project ID 1091379; Impulse ID 1; deploy version 2; gerada em 19/08/2026 11:32:07.
- FOMO EON compilado, entrada 160x160x1 grayscale, int8 quantizado, grid 20x20, labels exatas `031` e `045`, threshold 0.5.
- Resize exportado: `FIT_LONGEST`; arena: 479.948 bytes nos metadados e 399.616 bytes no código EON para este alvo.
- A v2 fica isolada em `v2_project/lib/Micropulsionador_inferencing`; a biblioteca v1 não é compilada nesse subprojeto.

## 2. Compatibilidade de build

- Resultado: COMPATÍVEL COM AJUSTES (subprojeto isolado e caminho curto temporário no Windows; biblioteca gerada intacta).
- RAM estática: 24.104 bytes (7,4%).
- Flash do linker: 373.717 bytes (5,7%); `firmware.bin`: 374.080 bytes.
- Warnings relevantes: macro `EI_PORTING_ARDUINO` redefinida por headers vendorizados e aviso de API legada para contagem de boxes; nenhum impediu build/link/runtime.

## 3. Runtime

- ESP32-S3 rev. 0.2, Flash física 16.777.216 bytes, PSRAM física 8.386.279 bytes.
- Smoke sintético: 10/10 inferências com `EI_IMPULSE_OK`, sem panic, watchdog, reset ou allocation failure.
- Heap no smoke: 363.612 antes e 363.156 depois (delta -456 de inicialização); PSRAM 8.386.275 antes/depois (delta 0).

## 4. Controle 031

- Resultado: 031; confidence 0.996094; boxes 1; DSP 12532 us; inferência 332666 us; pós 252 us.

## 5. Controle 045

- Resultado: 045; confidence 0.996094; boxes 1; DSP 12534 us; inferência 332779 us; pós 244 us.

## 6. Lote 031

- Total: 308
- Corretas: 281
- Sem detecção: 26
- Confundidas: 0
- Ambíguas: 1
- Erro runtime: 0
- Taxa correta: 91.23%
- Confiança correta mínima/média/mediana/máxima: 0.542969 / 0.985237 / 0.996094 / 0.996094

## 7. Lote 045

- Total: 310
- Corretas: 292
- Sem detecção: 1
- Confundidas: 0
- Ambíguas: 17
- Erro runtime: 0
- Taxa correta: 94.19%
- Confiança correta mínima/média/mediana/máxima: 0.925781 / 0.995853 / 0.996094 / 0.996094

## 8. Matriz

| | 031 | 045 | NONE | AMBIGUA | ERROR |
|---|---:|---:|---:|---:|---:|
| Esperado 031 | 281 | 0 | 26 | 1 | 0 |
| Esperado 045 | 0 | 292 | 1 | 17 | 0 |

## 9. Performance

- DSP médio: 12.540 ms.
- Inferência média: 332.980 ms; mínima 332.467 ms; máxima 333.896 ms.
- Pós-processamento médio: 0.250 ms.

## 10. Memória

- Heap da primeira imagem: 363156 antes / 363156 depois; heap ao final: 362892; mínimo observado: 357508.
- PSRAM do buffer de imagem: 8309459 antes / 8309459 depois; ao final: 8309459; delta por inferência entre 0 e 0.
- Não houve perda progressiva de heap/PSRAM, panic, watchdog ou falha de alocação.

## 11. Comparação antigo vs novo

| Métrica | Modelo antigo 96x96 | Novo modelo 160x160 |
|---|---:|---:|
| 031 corretas | 205/308 | 281/308 |
| 031 taxa | 66,56% | 91.23% |
| 045 corretas | 7/310 | 292/310 |
| 045 taxa | 2,26% | 94.19% |
| Confusões | 0 | 0 |
| Ambíguas | 1 | 18 |
| Inferência média | 117,135 ms | 332.980 ms |
| RAM estática | ~24 KB (referência anterior) | 24.104 bytes |
| Flash | ~372–399 KB (referência anterior) | 373.717 bytes; bin 374.080 bytes |
| PSRAM estável | sim | sim |
| Crashes | 0 | 0 |

## 12. Casos problemáticos

- Total: 45; sem detecção: 27; confundidas: 0; ambíguas: 18; erros runtime: 0.
- A lista completa está em `batch_v2_problematic.csv`; todas as boxes estão em `batch_v2_boxes.csv`.

## 13. Conclusão

NOVO MODELO FUNCIONA MAS AINDA APRESENTA FALHAS.

O runtime 160x160 está validado e a melhora externa é grande nas duas classes, sem classificação cruzada exclusiva. Entretanto, 45/618 imagens não ficaram na categoria CORRETA (27 sem detecção e 18 ambíguas), uma taxa ainda relevante para decisão industrial automática. O resultado não autoriza integração de produção nem definição de threshold de aplicação.

## 14. Alterações realizadas

- Consulte `artifact_manifest.txt` para a relação exata dos arquivos do diagnóstico v2.
- `src/main.cpp`, câmera, biblioteca v1 e arquivos gerados da biblioteca v2 não foram modificados.

## 15. Próximo passo

Executar uma auditoria dirigida das 45 imagens problemáticas, sobrepondo todas as boxes e comparando-as às anotações do treinamento v2, antes de integrar a câmera.
