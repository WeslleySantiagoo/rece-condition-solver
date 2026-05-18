"""
Distribuição de Medicamentos em Hospital
VERSÃO SEM SINCRONISMO — Demonstração de Condição de Corrida (Race Condition)

Disciplina: Princípios de Software Básico — UFRPE
Problema: Threads representando enfermeiros acessando estoque compartilhado
         sem nenhum controle de acesso concorrente.

Como o erro é forçado:
    O Python possui o GIL (Global Interpreter Lock), que protege operações
    simples. Porém, a operação `estoque -= quantidade` é composta por múltiplos
    bytecodes (LOAD → SUBTRACT → STORE). Ao inserir um time.sleep() entre a
    leitura e a escrita, simulamos a latência de um sistema real (ex: consulta
    a banco de dados) e forçamos o GIL a ser liberado — permitindo que outra
    thread entre na seção crítica antes que a primeira termine.
"""

import threading
import time
import logging

# Configuração de log com timestamp e nome da thread
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d  [%(threadName)s]  %(message)s",
    datefmt="%H:%M:%S",
)

# ── Recurso compartilhado ──────────────────────────────────────────────────────
estoque = 100  # unidades de medicamento disponíveis

# ── Função executada por cada enfermeiro (thread) ─────────────────────────────
def retirar_medicamento(nome: str, quantidade: int) -> None:
    """Tenta retirar `quantidade` unidades do estoque SEM proteção alguma."""
    global estoque

    # 1. Leitura do estoque
    estoque_lido = estoque
    logging.info(f"{nome} leu o estoque: {estoque_lido} unidades disponíveis")

    # 2. Simulação de latência (ex.: validação em banco de dados, chamada de rede)
    #    É AQUI que o GIL é liberado e outra thread pode entrar.
    time.sleep(0.15)

    # 3. Verificação e escrita — baseadas no valor JÁ DESATUALIZADO
    if estoque_lido >= quantidade:
        # Outra thread pode ter reduzido o estoque durante o sleep acima!
        estoque -= quantidade          # operação não-atômica (LOAD → SUB → STORE)
        logging.info(
            f"{nome} RETIROU {quantidade} unidades. "
            f"Estoque resultante: {estoque}"
        )
    else:
        logging.warning(
            f"{nome} NEGADO — estoque insuficiente ao ler "
            f"(leu {estoque_lido}, precisava de {quantidade})"
        )


# ── Configuração dos enfermeiros ───────────────────────────────────────────────
ENFERMEIROS = [
    ("Enfermeiro Ana",    30),
    ("Enfermeiro Bruno",  30),
    ("Enfermeiro Carla",  30),
    ("Enfermeiro Diego",  30),
]

# Valor correto esperado: o estoque não deve ficar negativo.
# Com 100 unidades e 4 pedidos de 30 cada (total 120), apenas 3 retiradas
# são possíveis → estoque correto = 100 - 3*30 = 10.
ESTOQUE_INICIAL = estoque
CORRETO_ESPERADO = 10  # Diego deveria ser negado, pois ao retirar 30 unidades ele ficaria com -20


# ── Execução ───────────────────────────────────────────────────────────────────
def main() -> None:
    logging.info("=" * 60)
    logging.info("INÍCIO DA SIMULAÇÃO — SEM SINCRONISMO")
    logging.info(f"Estoque inicial: {ESTOQUE_INICIAL} unidades")
    logging.info("=" * 60)

    threads = [
        threading.Thread(
            target=retirar_medicamento,
            args=(nome, qtd),
            name=nome,
        )
        for nome, qtd in ENFERMEIROS
    ]

    # Inicia todas as threads ao mesmo tempo para maximizar a concorrência
    for t in threads:
        t.start()

    for t in threads:
        t.join()

    logging.info("=" * 60)
    logging.info(f"Estoque FINAL:    {estoque} unidades")
    logging.info(f"Estoque CORRETO ESPERADO: {CORRETO_ESPERADO} unidades")
    logging.info(
        f"!!! INCONSISTENCIA DETECTADA !!! Estoque ficou em {estoque} "
        f"(deveria ser {CORRETO_ESPERADO}). Estoque negativo = dados corrompidos!"
        if estoque != CORRETO_ESPERADO
        else "Sem inconsistencia desta vez. Execute novamente."
    )
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
