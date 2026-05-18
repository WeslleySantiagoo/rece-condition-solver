# Concorrência de Recursos
## Distribuição de Medicamentos em Hospital

**Disciplina:** Princípios de Software Básico  
**Curso:** Sistemas de Informação — UFRPE

---

## 1. Descrição do Problema

Em ambientes hospitalares, múltiplos profissionais de saúde acessam simultaneamente o
sistema de controle de estoque de medicamentos. No contexto desta atividade, esse
cenário foi modelado com **threads** representando enfermeiros que retiram
medicamentos de um **estoque compartilhado** (variável global em memória).

O objetivo é demonstrar que, sem o devido controle de acesso concorrente, operações
de leitura-verificação-escrita podem gerar **inconsistências críticas** — como o
estoque ficar negativo —, e depois apresentar a solução utilizando **semáforos**.

---

## 2. Fundamento Técnico — Por que o erro ocorre

O Python possui o **GIL (Global Interpreter Lock)**, que garante que apenas uma thread
execute bytecodes por vez. Isso pode dar a falsa impressão de que variáveis
compartilhadas estão automaticamente protegidas.

Porém, o GIL **não protege operações compostas**. A instrução:

```python
stock -= amount
```

é compilada internamente em três bytecodes separados:

```
LOAD_GLOBAL   stock     # lê o valor atual
BINARY_SUBTRACT amount  # calcula o novo valor
STORE_GLOBAL  stock     # escreve o resultado
```

O GIL pode ser **liberado entre qualquer um desses passos** (especialmente em
chamadas de I/O, sleep ou após um número fixo de instruções). Quando isso ocorre,
outra thread entra e lê um valor de estoque **já desatualizado**, tomando decisões
incorretas com base nesse valor obsoleto.

Para tornar a condição de corrida **reproduzível e visível**, foi inserido um
`time.sleep(0.15)` entre a leitura e a escrita, simulando a latência real de
um sistema (consulta a banco de dados, validação em servidor, etc.).

---

## 3. Sem Sincronismo — Demonstração do Erro

### Código: `no_sync.py`

#### Variáveis principais

| Variável         | Tipo   | Descrição                                        |
|------------------|--------|--------------------------------------------------|
| `stock`          | `int`  | Estoque global compartilhado entre todas as threads |
| `stock_read`     | `int`  | Snapshot local do estoque lido pela thread       |
| `NURSES`         | `list` | Lista de tuplas `(nurse_name, amount)`           |
| `INITIAL_STOCK`  | `int`  | Valor do estoque antes do início da simulação    |
| `EXPECTED_RESULT`| `int`  | Estoque correto esperado ao final (10 unidades)  |

#### Função principal

```python
def withdraw_medication(nurse_name: str, amount: int) -> None:
    global stock

    stock_read = stock                      # (1) lê o valor atual
    logging.info(f"{nurse_name} leu o estoque: {stock_read}")

    time.sleep(0.15)                        # (2) latência — GIL é liberado aqui!

    if stock_read >= amount:                # (3) verifica valor JÁ DESATUALIZADO
        stock -= amount                     # (4) escrita sem proteção
```

### Análise do Problema

O estoque inicial é **100 unidades**. Cada enfermeiro solicita **30 unidades**
(total de 4 solicitações = 120 unidades). O comportamento correto seria:
- Laura retira 30 → estoque: 70
- Bruno retira 30 → estoque: 40
- Carla retira 30 → estoque: 10
- Diego é **negado** (apenas 10 disponíveis, precisa de 30)
- **Estoque final correto: 10**

### Log Real Observado

```
11:53:20.398  [MainThread]  ============================================================
11:53:20.398  [MainThread]  INÍCIO DA SIMULAÇÃO — SEM SINCRONISMO
11:53:20.398  [MainThread]  Estoque inicial: 100 unidades
11:53:20.398  [MainThread]  ============================================================
11:53:20.399  [Enfermeiro Laura]  Enfermeiro Laura leu o estoque: 100 unidades disponíveis
11:53:20.399  [Enfermeiro Bruno]  Enfermeiro Bruno leu o estoque: 100 unidades disponíveis
11:53:20.399  [Enfermeiro Carla]  Enfermeiro Carla leu o estoque: 100 unidades disponíveis
11:53:20.399  [Enfermeiro Diego]  Enfermeiro Diego leu o estoque: 100 unidades disponíveis
11:53:20.549  [Enfermeiro Laura]  Enfermeiro Laura RETIROU 30 unidades. Estoque resultante: 70
11:53:20.549  [Enfermeiro Bruno]  Enfermeiro Bruno RETIROU 30 unidades. Estoque resultante: 40
11:53:20.549  [Enfermeiro Carla]  Enfermeiro Carla RETIROU 30 unidades. Estoque resultante: 10
11:53:20.549  [Enfermeiro Diego]  Enfermeiro Diego RETIROU 30 unidades. Estoque resultante: -20
11:53:20.549  [MainThread]  ============================================================
11:53:20.549  [MainThread]  Estoque FINAL:    -20 unidades
11:53:20.549  [MainThread]  Estoque CORRETO ESPERADO: 10 unidades
11:53:20.549  [MainThread]  INCONSISTENCIA DETECTADA: Estoque ficou em -20 (deveria ser 10). Estoque negativo = dados corrompidos!
11:53:20.549  [MainThread]  ============================================================
```

### Causa Raiz (Race Condition)

Todas as quatro threads leram o estoque **quase simultaneamente** (timestamps
idênticos em `11:53:20.399`) e todas viram **100 unidades**. Todas passaram pela
verificação `if stock_read >= amount` com sucesso e todas realizaram a retirada.
O estoque foi decrementado quatro vezes a partir de valores já obsoletos, chegando a
**-20**, estado **impossível e inválido** em um sistema real.

---

## 4. Com Sincronismo — Solução com Semáforo

### Conceito

Um **semáforo** é uma variável inteira controlada pelo sistema operacional com duas
operações atômicas:

- **`acquire()` (P / wait):** decrementa o contador; se for 0, **bloqueia** a thread
  até que outra libere.
- **`release()` (V / signal):** incrementa o contador, **desbloqueando** a próxima
  thread em espera.

Usando `threading.Semaphore(1)` — semáforo binário, equivalente a *mutex* —
garantimos que **apenas uma thread por vez** execute a seção crítica.

### Código: `with_sync.py`

#### Variáveis principais

| Variável         | Tipo                  | Descrição                                           |
|------------------|-----------------------|-----------------------------------------------------|
| `stock`          | `int`                 | Estoque global compartilhado entre todas as threads |
| `stock_read`     | `int`                 | Snapshot local do estoque lido pela thread          |
| `semaphore`      | `threading.Semaphore` | Semáforo binário que garante exclusão mútua         |
| `NURSES`         | `list`                | Lista de tuplas `(nurse_name, amount)`              |
| `EXPECTED_RESULT`| `int`                 | Estoque correto esperado ao final (10 unidades)     |

#### Função principal

```python
semaphore = threading.Semaphore(1)  # apenas 1 thread na seção crítica

def withdraw_medication(nurse_name: str, amount: int) -> None:
    global stock

    semaphore.acquire()     # ENTRADA: bloqueia se outra thread já estiver dentro
    try:
        stock_read = stock
        time.sleep(0.15)    # latência — sem risco, recurso está protegido

        if stock_read >= amount:
            stock -= amount
        else:
            logging.warning(f"{nurse_name} NEGADO — estoque insuficiente")
    finally:
        semaphore.release() # SAÍDA: libera para a próxima thread (sempre executado)
```

> O bloco `try/finally` é essencial: garante que o `release()` seja chamado mesmo
> que uma exceção ocorra dentro da seção crítica, evitando **deadlocks**.

### Log Real Observado

```
11:59:08.851  [MainThread]  ============================================================
11:59:08.851  [MainThread]  INÍCIO DA SIMULAÇÃO — COM SINCRONISMO (Semáforo)
11:59:08.851  [MainThread]  Estoque inicial: 100 unidades
11:59:08.851  [MainThread]  ============================================================
11:59:08.852  [Enfermeiro Laura]    Enfermeiro Laura aguardando acesso ao estoque...
11:59:08.852  [Enfermeiro Laura]    Enfermeiro Laura ENTROU na seção crítica.
11:59:08.852  [Enfermeiro Laura]    Enfermeiro Laura leu o estoque: 100 unidades disponíveis
11:59:08.852  [Enfermeiro Bruno]  Enfermeiro Bruno aguardando acesso ao estoque...
11:59:08.852  [Enfermeiro Carla]  Enfermeiro Carla aguardando acesso ao estoque...
11:59:08.852  [Enfermeiro Diego]  Enfermeiro Diego aguardando acesso ao estoque...
11:59:09.002  [Enfermeiro Laura]    Enfermeiro Laura RETIROU 30 unidades. Estoque resultante: 70
11:59:09.002  [Enfermeiro Laura]    Enfermeiro Laura SAIU da seção crítica. Próximo pode entrar.
11:59:09.002  [Enfermeiro Bruno]  Enfermeiro Bruno ENTROU na seção crítica.
11:59:09.002  [Enfermeiro Bruno]  Enfermeiro Bruno leu o estoque: 70 unidades disponíveis
11:59:09.152  [Enfermeiro Bruno]  Enfermeiro Bruno RETIROU 30 unidades. Estoque resultante: 40
11:59:09.153  [Enfermeiro Bruno]  Enfermeiro Bruno SAIU da seção crítica. Próximo pode entrar.
11:59:09.153  [Enfermeiro Carla]  Enfermeiro Carla ENTROU na seção crítica.
11:59:09.153  [Enfermeiro Carla]  Enfermeiro Carla leu o estoque: 40 unidades disponíveis
11:59:09.303  [Enfermeiro Carla]  Enfermeiro Carla RETIROU 30 unidades. Estoque resultante: 10
11:59:09.303  [Enfermeiro Carla]  Enfermeiro Carla SAIU da seção crítica. Próximo pode entrar.
11:59:09.303  [Enfermeiro Diego]  Enfermeiro Diego ENTROU na seção crítica.
11:59:09.303  [Enfermeiro Diego]  Enfermeiro Diego leu o estoque: 10 unidades disponíveis
11:59:09.453  [Enfermeiro Diego]  Enfermeiro Diego NEGADO — estoque insuficiente (10 disponíveis, necessário 30)
11:59:09.453  [Enfermeiro Diego]  Enfermeiro Diego SAIU da seção crítica. Próximo pode entrar.
11:59:09.453  [MainThread]  ============================================================
11:59:09.453  [MainThread]  Estoque FINAL:    10 unidades
11:59:09.453  [MainThread]  Estoque ESPERADO: 10 unidades
11:59:09.453  [MainThread]  CONSISTENCIA GARANTIDA! Estoque correto.
11:59:09.453  [MainThread]  ============================================================
```

### Resultado Correto

Cada thread entrou na seção crítica **sequencialmente**, leu o valor **atualizado**
do estoque e tomou a decisão correta. O Enfermeiro Diego foi corretamente **negado**
porque, quando sua vez chegou, o estoque real era de apenas 10 unidades.

---

## 5. Comparação dos Resultados

| Aspecto                    | Sem Sincronismo         | Com Semáforo            |
|----------------------------|-------------------------|-------------------------|
| Estoque final              | **-20** (inválido)      | **10** (correto)        |
| Diego foi negado?          | Não (erro)              | Sim (comportamento certo)|
| Valor lido pelas threads   | Todas leram **100**     | Cada uma leu o valor real|
| Acesso simultâneo          | Sim — 4 threads juntas  | Não — 1 de cada vez     |
| Integridade dos dados      | **Violada**             | **Garantida**           |

---

## 6. Conclusão

A atividade demonstrou que **concorrência sem controle de acesso** pode corromper
dados críticos de forma silenciosa — o programa não lança exceção, mas o resultado
é logicamente inválido (estoque negativo). Em sistemas hospitalares reais, essa
falha poderia resultar em distribuição de medicamentos além do disponível.

O uso de `threading.Semaphore(1)` resolveu o problema ao serializar o acesso à
**seção crítica** (leitura + verificação + escrita), garantindo que cada operação
seja concluída atomicamente antes que a próxima comece. A proteção com
`try/finally` assegura que o semáforo seja sempre liberado, prevenindo deadlocks.
