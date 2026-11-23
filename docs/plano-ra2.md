# InvoiceGuard RA2: plano de execução

Criado em 22/11/2026, atualizado em 23/11/2026. Fonte dos requisitos: `AIPY_ST4 - Course Project.pdf`, `AIPY_ST5 - Course Project.pdf`, Plano de Ensino v3 e a tarefa **Summative Assessment - LO 2** (Canvas, publicada, vence sáb 28/11 23:59, 5 pts, envio por URL ou upload, um envio vale para o grupo).

Rubrica LO2 (pontos): 4.1 lote 0,7 · 4.2 workbook 0,7 · 4.3 relatório e robustez 0,6 · 4.4 IA do ST4 0,5 · 5.1 API 0,7 · 5.2 integração 0,7 · 5.3 workflow 0,6 · 5.4 IA do ST5 0,5. Grupo (Lucas, Eduardo, Patrick) já aprovou tema e plano; o trabalho é feito junto.

## 0. Prazos e bloqueios

| Data | Marco |
|---|---|
| 22 a 23/11 | Combinar tema com Eduardo e Patrick; esqueleto, dados e módulos de regra |
| 24 a 25/11 | Aquisição da API, integração, saídas (CSV, workbook, relatório), log |
| 26/11 | Os 6 testes, README, registro de IA, ensaio da demo |
| 27/11 | Apresentação em equipe |
| 28/11 | Entrega dos artefatos do RA2 (recuperação do RA1 também até 28/11) |
| 04/12 | Recuperação do RA2 / fechamento (não contar com isso) |

Atualização de 23/11: o "Summative Assessment - LO 2" foi publicado no Canvas. Vale 5 pontos, vence 28/11 às 23:59 (o Canvas mostra 29/11 02:59 UTC) e aceita envio por URL (`online_url`) ou upload (`online_upload`). O enunciado lista só os itens 4.1 a 4.4 (ST4) e 5.1 a 5.4 (ST5), exatamente o escopo deste plano; ST6 não entra.

Bloqueio restante: nenhum (equipe alinhada). Decidir só o formato de envio (URL do repo GitHub ou zip) e quem envia.

### Adendos da rubrica (23/11)

1. **ST3.** 4.1 e 4.2 exigem reusar limpeza, validação e agregação do ST3 e documentar adaptações; o repo não tem ST3. Mapeamento: validação do LO1 e do ST3 vira `loader.py`; agregação do resumo vira agrupamento por moeda e nível de aprovação. Seção "Adaptações" no README. Confirmar com o grupo se há código ST3 a reaproveitar.
2. **Registro de IA em duas partes.** `docs/ai-log.md` ganha uma seção ST4 (4.4) e uma ST5 (5.4); cada decisão com ferramenta e versão, prompt, resposta, sugestões consideradas, aceito/rejeitado com motivo, teste que verificou, resultado observado e limitação.
3. **Rastreabilidade.** Coluna `source_file` em CSV processado, integrado e na aba de detalhe; resumo ordenado por total BRL decrescente.
4. **Conferência workbook x CSV e antes/depois do merge.** Passo explícito no workflow (e teste) que relê o `.xlsx` e compara com o CSV; reconciliação de contagem de linhas e total antes e depois do merge (5.2).

## 1. Escopo

O enunciado do ST5 manda estender as saídas do ST4 (lote de CSVs, workbook, relatório, validação, log). O repo hoje só tem o LO1 (um script de uma fatura por vez). Portanto o RA2 precisa de três camadas: ST3/ST4 (lote, validação, workbook, relatório, log) e ST5 (API, integração, 6 testes).

**Pergunta de negócio.** O contas a pagar recebe faturas em BRL, USD e EUR. O limite de aprovação (BRL 1.000 e BRL 10.000) é em reais, então uma fatura de USD 1.900 pode cair em gerência ou diretoria dependendo do câmbio do dia. Pergunta: qual é o total a pagar em BRL de cada fatura, pela cotação oficial da data de emissão, e qual nível de aprovação ela exige?

**Valor da fonte externa.** Sem a cotação, o roteamento de aprovação de faturas em moeda estrangeira fica errado. A API muda o resultado do negócio.

## 2. Fonte externa: PTAX do Banco Central (Olinda)

Verificado em 22/11/2026 com chamada real (nada inventado):

- Provedor: Banco Central do Brasil, serviço aberto `olinda.bcb.gov.br`, sem chave nem cadastro.
- Endpoint: `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)`
- Parâmetros: `@moeda='USD'`, `@dataInicial='MM-DD-AAAA'`, `@dataFinalCotacao='MM-DD-AAAA'`, `$format=json`, `$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao,tipoBoletim`.
- Campos usados: `cotacaoVenda` (BRL por 1 unidade da moeda), `dataHoraCotacao`, `tipoBoletim`.
- Granularidade: cinco boletins por dia útil (Abertura, três Intermediários, Fechamento).
- Fim de semana e feriado: a lista vem vazia (confirmado: 21/11/2026 retornou `value: []`). Isso é o caso real de "correspondência ausente".
- Erro visto na tentativa: o nome do parâmetro é `moeda`, não `codigoMoeda` (a API devolve 400 com mensagem clara).

Decisões a registrar na documentação:

- Taxa usada: `cotacaoVenda` do boletim `Fechamento`, porque a empresa compra moeda para pagar o fornecedor. É suposição da equipe, não regra legal.
- Data sem cotação: usar o último dia útil anterior (janela de busca de 7 dias), com colunas `rate_date` e `rate_fallback` visíveis. Sem cotação na janela: rejeitar o lote.
- Termos de uso e atribuição: dado aberto do BCB, citar a fonte no relatório e no README. Conferir o texto de licença no portal de dados abertos antes de citar.

## 3. Regra de integração

- Linha da fatura: uma fatura (`invoice_number`).
- Linha da cotação: um par (moeda, dia) depois de filtrar `Fechamento`.
- Chave: `(currency, rate_date)`. Faturas em BRL não passam pela API (taxa 1,00).
- Cardinalidade: muitas faturas para uma cotação (N:1). Checar unicidade da chave no lado da cotação e que o número de linhas da fatura não muda no merge.
- Total em BRL: `total_foreign * rate`, arredondado em centavos (half-up, `Decimal`), como o LO1.
- Aprovação: decidida pelo total em BRL, nunca pelo subtotal. Reaproveita BR-1, BR-2 e BR-3 do LO1 sem mudar a regra.
- Prova de correção: soma dos totais em moeda estrangeira × taxa recalculada fora do código para amostra de linhas; contagem de linhas antes e depois; total BRL por moeda reconcilia entre CSV, workbook e relatório.

## 4. Arquitetura (arquivos `.py` com funções nomeadas)

```
invoiceguard/
  invoiceguard.py            LO1 (não mexer)
  run.py                     um comando: python3 run.py --mode live|saved
  src/
    rules.py                 BR-1, BR-2, BR-3 como funções puras (reuso do LO1)
    loader.py                lê lote (>= 2 CSVs), valida colunas e linhas
    fx_api.py                GET com timeout, erros HTTP, salva resposta bruta
    integrate.py             normaliza chave, merge, checagens de cobertura
    outputs.py               CSV integrado, workbook (openpyxl), relatório txt
    workflow.py              orquestra aquisição, validação, integração, saída, log
  data/
    input/                   invoices_a.csv, invoices_b.csv (fictícios, preservados)
    raw/                     resposta bruta da API + metadados (provedor, URL, data, modo)
  output/
    runs/<run_id>/           pacote completo de cada execução bem-sucedida
    latest.txt               aponta o último run e seu status
  tests/                     unittest (stdlib), 6 testes obrigatórios + extras
  docs/                      business-model, ai-log, test-cases, source-record, plano
```

Dependências novas: `pandas` e `openpyxl` (instalados via `requirements.txt` em venv; hoje nenhum dos dois está instalado na máquina). Cliente HTTP: `urllib` da stdlib, sem `requests`.

Modos de execução:

- `live`: chama a API e grava `data/raw/` (resposta autêntica, exigida pelo ST5).
- `saved`: reutiliza a última resposta bruta, para demo offline e repetibilidade. O modo aparece no log, no relatório e no CSV.

## 5. Dados de entrada (fictícios)

Dois CSVs com as mesmas colunas: `invoice_number, supplier, issue_date, currency, subtotal, tax_rate, discount`. Uns 12 a 20 registros por arquivo, incluindo de propósito:

- fatura em USD e EUR perto dos limites de 1.000 e 10.000 depois da conversão;
- fatura em BRL (sem API);
- data em sábado, domingo e feriado (fallback de dia útil);
- caso que muda de nível só por causa do câmbio.

Arquivos inválidos separados em `tests/fixtures/` (nunca em `data/input/`).

## 6. Regras de validação (ST4: no mínimo 3; ST5: dados externos)

Entrada: colunas obrigatórias presentes; `invoice_number` único no lote inteiro; moeda em `{BRL, USD, EUR}`; data válida e não futura; valores no formato do LO1 (`[0-9]+([.,][0-9]{1,2})?`, taxa até 100). Um arquivo ou linha inválida para o lote inteiro.

API: estrutura JSON esperada (`value` é lista), campos presentes, `cotacaoVenda` numérica e positiva, data coerente com a pedida, cobertura de todas as chaves necessárias.

Saída: primeiro em pasta temporária, depois `os.replace` para `output/runs/<run_id>/`. Falha de escrita nunca marca o pacote como concluído; saídas anteriores ficam intactas.

## 7. Os testes obrigatórios

Registrar para cada um: preparação, resultado esperado, resultado observado, PASS/FAIL.

| # | Teste (ST5) | Como simular | Esperado |
|---|---|---|---|
| 1 | Entradas válidas e completas | lote bom, modo `saved` | totais e níveis iguais ao cálculo independente |
| 2 | Dado externo inválido | JSON sem `cotacaoVenda`, moeda ou taxa negativa | rejeição clara, nenhum pacote concluído |
| 3 | Problema de chave | cotação duplicada; data sem cotação na janela | duplicata rejeitada; sem cotação visível e tratada |
| 4 | Falha de aquisição | `urlopen` simulado com timeout e com HTTP 500 | erro visível, `latest.txt` marca falha |
| 5 | Falha de escrita de saída | destino somente leitura ou `os.replace` simulado | nenhum pacote parcial marcado como concluído |
| 6 | Execução repetida válida | duas execuções com a mesma entrada | mesmos resultados de negócio e pacote anterior preservado |

Testes de regressão do LO1 (18 casos) passam a rodar contra `src/rules.py` para provar que a regra não mudou. Os 5 testes do ST4 (lote válido, valor inválido, coluna faltando, sem arquivos, segunda execução) entram como extras, já que o ST5 estende o ST4.

## 8. Entregas

- CSV integrado, workbook atualizado, relatório de texto com a fonte externa.
- Workbook: aba de detalhe (rastreável ao arquivo de origem) e aba de resumo (agrupamento ordenado por métrica); cabeçalho legível, larguras, formato numérico, linha de cabeçalho congelada, filtros; valores numéricos continuam numéricos.
- Relatório: execução, arquivos usados, escopo, no mínimo três indicadores (por exemplo total BRL por moeda, contagem por nível de aprovação, fatura que mudou de nível por causa do câmbio), um achado e uma limitação, separando evidência calculada de interpretação.
- Registro de fonte (`docs/source-record.md`): provedor, endpoint, parâmetros, data de aquisição, unidades, condições de uso.
- `docs/test-cases-ra2.md` com os resultados dos 6 testes (e dos extras).
- README atualizado: seleção da fonte, ambiente, modos, comando, regra de integração, política de falha, arquivos de saída, limitações.
- `docs/ai-log.md` partes ST4 e ST5 (4.4 e 5.4): ferramenta e versão, prompt, resposta, sugestões aceitas e rejeitadas com motivo, teste que verificou cada mudança, resultado e limitação. Declaração de uso de IA do plano de ensino com os campos preenchidos.
- Seção "Adaptações do ST3" no README e verificação workbook x CSV no workflow.
- Todos os integrantes precisam saber explicar o fluxo na apresentação.

## 9. Demonstração (27/11)

1. Execução bem-sucedida em modo `live`, mostrando `latest.txt`, o CSV, o workbook e o relatório.
2. Execução com falha controlada (arquivo com valor inválido), mostrando erro claro, log e pacote anterior preservado.
3. Registro de fonte e evidência dos testes.
4. Um integrante explica cada módulo; revezar quem responde.

## 10. Divisão de trabalho sugerida (ajustar com a equipe)

| Frente | Conteúdo | Sugestão |
|---|---|---|
| A | `rules.py`, `loader.py`, validação, testes 1 e 2 | Lucas |
| B | `fx_api.py`, `integrate.py`, testes 3 e 4 | a combinar |
| C | `outputs.py`, `workflow.py`, testes 5 e 6, workbook | a combinar |
| D | README, ai-log, source-record, relatório, roteiro da demo | todos revisam |

Sem dono único: cada um revisa o PR de outro, para todos conseguirem explicar tudo.

## 11. Fluxo no repositório

O repo tem regras de PR, CODEOWNERS e issue flow (commit `7d679d4`). Seguir: uma issue por frente, branch por frente, PR com `Closes #N`, commits em fases reais no formato `tipo(escopo): resumo` com corpo explicando o porquê, e vigiar o CI de cada PR até o fim. Não commitar nada sem pedido explícito.

## 12. Riscos e decisões em aberto

| Item | Risco ou decisão | Plano |
|---|---|---|
| LO2 publicado | rubrica lida em 23/11 | decidir formato de envio (URL ou zip) e quem envia |
| API fora do ar na demo | demo trava | modo `saved` com resposta bruta autêntica já salva |
| PTAX compra ou venda | muda total | decidir na equipe; padrão proposto: venda no fechamento |
| Moedas | escopo | USD e EUR, mais BRL como controle |
| Eduardo e Patrick | trabalho é em equipe | alinhar tema e divisão antes de codar |
| Prazo curto (6 dias) | corte de escopo | prioridade: lote + API + 6 testes + documentação; workbook com formatação completa antes de relatório elaborado |

## 13. Ordem de execução

1. Alinhar tema e divisão com a equipe (22 a 23/11).
2. Criar issues, branch e `requirements.txt`; instalar venv.
3. `rules.py` + regressão dos 18 casos (garante que a regra não muda).
4. Dados fictícios e `loader.py` com validação e testes 1 e 2.
5. `fx_api.py`: primeira execução `live`, salvar resposta bruta e preencher `source-record.md`.
6. `integrate.py` com testes 3 e 4.
7. `outputs.py` e `workflow.py` com log, `latest.txt`, pacote atômico e testes 5 e 6.
8. README, `ai-log.md` parte 3 e declaração de IA.
9. Ensaio da demo, caminho feliz e falha controlada (26/11).
10. Reconferir Canvas e entregar no formato publicado (27 a 28/11).
