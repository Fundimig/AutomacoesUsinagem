# Auditoria do projeto Edge Impulse 1091379

Esta pasta prepara a auditoria do projeto Edge Impulse que gerou a biblioteca
`Micropulsionador_inferencing`. Ela não altera o modelo, o dataset, as
annotations, o firmware ou os resultados das inferências já executadas.

## Identificação do artefato atual

- Project ID: `1091379`
- Owner: `engmarcelfrank`
- Project name: `Micropulsionador`
- Impulse ID: `1`
- Deploy version: `1`
- Data de geração registrada: `18/08/2026 18:13:58`
- Modelo: FOMO, entrada `96x96x1` grayscale
- Labels: `031` e `045`
- Threshold interno: `0.5`
- SHA-256 do `DetectaIA.zip` auditado:
  `7EE84844CEF7867CAA28D275DCE2549BD192C02A47CACA45252C60897E43D923`

## Escopo

Esta etapa serve somente para receber e organizar cópias dos artefatos
originais. Não é permitido durante a auditoria inicial:

- editar imagens ou annotations;
- alterar split, threshold, impulse ou learning block;
- retreinar ou exportar outro modelo;
- substituir a biblioteca atualmente validada;
- modificar os scripts de inferência ou o firmware.

## Checklist de recuperação

- [ ] Dataset original recuperado
- [ ] Annotations recuperadas
- [ ] Split recuperado
- [ ] Configuração do impulse recuperada
- [ ] Configuração do learning block recuperada
- [ ] Métricas recuperadas
- [ ] Model Testing recuperado
- [ ] Deployment identificado
- [ ] Trained model identificado

A descrição detalhada de cada item está em
[`required_artifacts.md`](required_artifacts.md).

## Organização

- `imported_artifacts/`: recebe futuramente os downloads originais, sem edição.
- `analysis/`: contém pontos de entrada para análises futuras.
- Os formatos reais deverão ser observados nos exports antes que qualquer
  parser seja implementado.

Nenhum login, token ou chave de API do Edge Impulse foi encontrado no
workspace. A recuperação dos artefatos depende de um usuário autorizado na
interface do Edge Impulse. Credenciais não devem ser copiadas para esta pasta.

## Cruzamento futuro

Depois que os artefatos forem obtidos, a auditoria deverá cruzar:

1. dataset e splits de treinamento/validação/teste do Edge Impulse;
2. `ImagensParaIA/031/`;
3. `ImagensParaIA/045/`;
4. `diagnostics/ei-smoke-test/batch_complete_results.csv`;
5. `diagnostics/ei-smoke-test/batch_complete_boxes.csv`.

O cruzamento deverá responder, sem modificar os dados:

- se as imagens atuais estavam no treinamento ou em outro split;
- se a classe `045` tinha poucas imagens ou pouca diversidade;
- se suas bounding boxes estavam ausentes ou incorretas;
- se o split continha sequências correlacionadas ou leakage;
- se há evidência de overfitting;
- se o deployment auditado corresponde ao modelo esperado;
- se ocorreu mudança de domínio visual entre treinamento e operação.

## Scripts auxiliares

Os scripts atuais apenas validam que um caminho informado existe. Eles não
assumem schema, nomes de arquivos ou formato de export:

```text
python analysis/analyze_dataset.py <caminho-do-dataset>
python analysis/analyze_annotations.py <caminho-das-annotations>
python analysis/analyze_metrics.py <caminho-das-metricas>
```

Um parser somente deverá ser adicionado após a inspeção de um artefato real e
preservado.
