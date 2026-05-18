"""
Distribuição de Medicamentos em Hospital
VERSÃO COM SINCRONISMO — Solução com Semáforo (Semaphore)

Disciplina: Princípios de Software Básico — UFRPE
Problema: Threads representando enfermeiros acessando estoque compartilhado
         com controle de acesso via semáforo binário.

Como o semáforo resolve o problema:
    threading.Semaphore(1) cria um semáforo com contador inicial 1.
    - semaforo.acquire() decrementa o contador; se já for 0, a thread BLOQUEIA
      até que outra thread libere o recurso.
    - semaforo.release() incrementa o contador, acordando a próxima thread.
    Com valor inicial 1 o semáforo se comporta como um mutex (exclusão mútua),
    garantindo que apenas UM enfermeiro por vez acesse a seção crítica.
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

# ── Semáforo binário (equivalente a mutex) ─────────────────────────────────────
#    Semaphore(1) → apenas 1 thread por vez pode estar na seção crítica.
#    Para permitir N acessos simultâneos use Semaphore(N).
semaforo = threading.Semaphore(1)


# ── Função executada por cada enfermeiro (thread) ─────────────────────────────
def retirar_medicamento(nome: str, quantidade: int) -> None:
    """Tenta retirar `quantidade` unidades do estoque COM proteção por semáforo."""
    global estoque

    logging.info(f"{nome} aguardando acesso ao estoque...")

    # ── ENTRADA NA SEÇÃO CRÍTICA ──────────────────────────────────────────────
    semaforo.acquire()  # bloqueia aqui se outra thread já estiver dentro
    try:
        logging.info(f"{nome} ENTROU na seção crítica.")

        # 1. Leitura do estoque (agora segura — ninguém mais pode entrar)
        estoque_lido = estoque
        logging.info(f"{nome} leu o estoque: {estoque_lido} unidades disponíveis")

        # 2. Simulação de latência — mesmo com sleep, o semáforo protege
        time.sleep(0.15)

        # 3. Verificação e escrita — estoque não pode ter mudado
        if estoque_lido >= quantidade:
            estoque -= quantidade
            logging.info(
                f"{nome} RETIROU {quantidade} unidades. "
                f"Estoque resultante: {estoque}"
            )
        else:
            logging.warning(
                f"{nome} NEGADO — estoque insuficiente "
                f"({estoque_lido} disponíveis, necessário {quantidade})"
            )

    finally:
        # ── SAÍDA DA SEÇÃO CRÍTICA — executado SEMPRE (mesmo em exceções) ──
        semaforo.release()
        logging.info(f"{nome} SAIU da seção crítica. Próximo pode entrar.")


# ── Configuração dos enfermeiros ───────────────────────────────────────────────
ENFERMEIROS = [
    ("Enfermeiro Ana",    30),
    ("Enfermeiro Bruno",  30),
    ("Enfermeiro Carla",  30),
    ("Enfermeiro Diego",  30),
]

CORRETO_ESPERADO = 10  # apenas 3 retiradas de 30 cabem em 100 unidades


# ── Execução ───────────────────────────────────────────────────────────────────
def main() -> None:
    logging.info("=" * 60)
    logging.info("INÍCIO DA SIMULAÇÃO — COM SINCRONISMO (Semáforo)")
    logging.info(f"Estoque inicial: {estoque} unidades")
    logging.info("=" * 60)

    threads = [
        threading.Thread(
            target=retirar_medicamento,
            args=(nome, qtd),
            name=nome,
        )
        for nome, qtd in ENFERMEIROS
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    logging.info("=" * 60)
    logging.info(f"Estoque FINAL:    {estoque} unidades")
    logging.info(f"Estoque ESPERADO: {CORRETO_ESPERADO} unidades")
    logging.info(
        "CONSISTENCIA GARANTIDA! Estoque correto."
        if estoque == CORRETO_ESPERADO
        else "ERRO — valor inesperado."
    )
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
