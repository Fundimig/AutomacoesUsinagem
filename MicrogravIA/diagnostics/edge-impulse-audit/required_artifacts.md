# Artefatos necessários para a auditoria

Os itens abaixo devem pertencer ao projeto Edge Impulse `1091379`, owner
`engmarcelfrank`, e devem ser obtidos sem alteração. Sempre que a interface
oferecer mais de um formato, preservar o download original e registrar de qual
tela, job, impulse, modelo ou deployment ele foi obtido.

## 1. Dataset

- imagens originais rotuladas como `031`;
- imagens originais rotuladas como `045`;
- imagens negativas, de fundo ou sem peça, caso tenham sido usadas;
- annotations completas, incluindo todas as bounding boxes;
- metadata por imagem disponível no projeto;
- identificação do split de cada imagem: training, validation e test;
- nomes/identificadores originais das amostras;
- informação sobre origem, sessão de captura ou dispositivo, se disponível;
- arquivos de labels, como `info.labels` ou `bounding_boxes.labels`, somente se
  forem realmente fornecidos pelo export.

Esses dados permitirão calcular quantidade de imagens e boxes por classe,
detectar imagens sem annotation, boxes incorretas, duplicatas e possível
leakage entre splits.

## 2. Configuração do impulse

- configuração completa do impulse ID `1` (`Impulse #1`);
- Image block configuration;
- resolução de entrada;
- resize mode;
- seleção grayscale ou RGB;
- preprocessing e scaling;
- parâmetros do DSP/Image block;
- versões dos blocos, quando registradas;
- qualquer transformação aplicada antes do learning block.

O export atual indica `96x96`, grayscale e `FIT_SHORTEST`, mas a configuração
original ainda é necessária para confirmar o treinamento que originou o
deployment.

## 3. Learning block

- nome e arquitetura do learning block;
- configuração FOMO;
- epochs;
- learning rate e scheduler, se houver;
- batch size;
- augmentation completa;
- quantização e representative dataset;
- backbone ou modelo base;
- parâmetros adicionais do treinamento;
- versão/ID do learning block e do trained model.

## 4. Treinamento

- training job ID;
- trained model ID;
- versão ou revisão do modelo;
- data e hora de início e conclusão;
- métricas globais;
- loss e validation loss por epoch, quando disponíveis;
- precision, recall e F1;
- confusion matrix;
- métricas específicas por classe;
- métricas FOMO/object detection;
- logs e warnings do job;
- distribuição efetiva entre training e validation.

Não substituir métricas por screenshots parciais se houver uma exportação
estruturada disponível. Se apenas screenshots existirem, preservar os arquivos
originais e registrar a tela e a data.

## 5. Model Testing

- conjunto exato usado no Model Testing;
- resultado por imagem;
- boxes preditas, labels e confidências;
- métricas globais e por classe;
- falsos negativos;
- falsos positivos;
- confusion matrix ou relatório equivalente;
- data e trained model ao qual o teste se refere.

## 6. Deployment

- deployment ID, se existir;
- deploy version;
- trained model ID associado;
- data e hora da geração;
- formato e configuração do export;
- uso de EON Compiler;
- tipo de quantização;
- target/plataforma selecionada;
- arquivo exportado original;
- histórico suficiente para confirmar se era o deployment esperado.

O deployment deverá ser confrontado com estes identificadores do artefato
atual:

```text
Project ID: 1091379
Impulse ID: 1
Deploy version: 1
Generated: 18/08/2026 18:13:58
Learning block ID no código gerado: 3
DetectaIA.zip SHA-256:
7EE84844CEF7867CAA28D275DCE2549BD192C02A47CACA45252C60897E43D923
```

## 7. Integridade e proveniência

Para cada download recebido:

- manter o nome e o conteúdo originais;
- não editar, normalizar, renomear em massa ou recomprimir;
- registrar a origem e a data do download;
- calcular SHA-256 antes da análise;
- manter exports de versões diferentes separados;
- não incluir token, cookie, senha ou chave de API.

## 8. Resultado esperado da futura auditoria

Com esses artefatos será possível confrontar o treinamento com as 618
inferências físicas e investigar:

- cobertura e diversidade da classe `045`;
- qualidade e distribuição das bounding boxes;
- balanceamento e independência dos splits;
- duplicatas ou sequências correlacionadas entre splits;
- diferenças entre o domínio de treinamento e `ImagensParaIA`;
- diferença entre métricas internas e desempenho físico;
- correspondência exata entre trained model, deployment e `DetectaIA.zip`.
