"""
Distribuição de Medicamentos em Hospital
VERSÃO COM SINCRONISMO — Solução com Semáforo (Semaphore)

Disciplina: Princípios de Software Básico — UFRPE
Problema: Threads representando enfermeiros acessando estoque compartilhado
         com controle de acesso via semáforo binário.

Como o semáforo resolve o problema:
    threading.Semaphore(1) cria um semáforo com contador inicial 1.
    - semaphore.acquire() decrementa o contador; se já for 0, a thread BLOQUEIA
      até que outra thread libere o recurso.
    - semaphore.release() incrementa o contador, acordando a próxima thread.
    Com valor inicial 1 o semáforo se comporta como um mutex (exclusão mútua),
    garantindo que apenas UM enfermeiro por vez acesse a seção crítica.
"""

import logging
import threading
import time

# ── Códigos de cor ANSI ────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
RED     = "\033[91m"    # erros críticos / inconsistência
YELLOW  = "\033[93m"    # avisos / negação de acesso
GREEN   = "\033[92m"    # saída da seção crítica (liberação do recurso)
BLUE    = "\033[94m"    # aguardando / entrada na seção crítica
CYAN    = "\033[96m"    # leitura de estoque (informativo)
WHITE   = "\033[97m"    # mensagens neutras / cabeçalho
MAGENTA = "\033[95m"    # retirada bem-sucedida


class ColoredFormatter(logging.Formatter):
    """Formatter que aplica cor ANSI à mensagem conforme palavras-chave."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        text = record.getMessage()

        # Resultado final correto
        if "CONSISTENCIA GARANTIDA" in text:
            return f"{BOLD}{GREEN}{msg}{RESET}"

        # Negação de acesso
        if record.levelno == logging.WARNING or "NEGADO" in text:
            return f"{YELLOW}{msg}{RESET}"

        # Saída da seção crítica (recurso liberado)
        if "SAIU da seção crítica" in text:
            return f"{GREEN}{msg}{RESET}"

        # Entrada na seção crítica
        if "ENTROU na seção crítica" in text:
            return f"{BOLD}{RED}{msg}{RESET}"

        # Retirada bem-sucedida
        if "RETIROU" in text:
            return f"{MAGENTA}{msg}{RESET}"

        # Aguardando acesso
        if "aguardando" in text:
            return f"{BLUE}{msg}{RESET}"

        # Leitura de estoque
        if "leu o estoque" in text:
            return f"{CYAN}{msg}{RESET}"

        # Cabeçalho / separadores
        if "===" in text or "INÍCIO" in text or "FINAL" in text or "ESPERADO" in text:
            return f"{BOLD}{WHITE}{msg}{RESET}"

        return msg


# ── Configuração de log com timestamp e nome da thread ────────────────────────
_handler = logging.StreamHandler()
_handler.setFormatter(
    ColoredFormatter(
        fmt="%(asctime)s.%(msecs)03d  [%(threadName)s]  %(message)s",
        datefmt="%H:%M:%S",
    )
)
logging.basicConfig(level=logging.INFO, handlers=[_handler])

# ── Recurso compartilhado ──────────────────────────────────────────────────────
stock = 100  # unidades de medicamento disponíveis

# ── Semáforo binário (equivalente a mutex) ─────────────────────────────────────
#    Semaphore(1) → apenas 1 thread por vez pode estar na seção crítica.
#    Para permitir N acessos simultâneos use Semaphore(N).
semaphore = threading.Semaphore(1)


# ── Função executada por cada enfermeiro (thread) ─────────────────────────────
def withdraw_medication(nurse_name: str, amount: int) -> None:
    """Tenta retirar `amount` unidades do estoque COM proteção por semáforo."""
    global stock

    logging.info(f"{nurse_name} aguardando acesso ao estoque...")

    # ── ENTRADA NA SEÇÃO CRÍTICA ──────────────────────────────────────────────
    semaphore.acquire()  # bloqueia aqui se outra thread já estiver dentro
    try:
        logging.info(f"{nurse_name} ENTROU na seção crítica.")

        # 1. Leitura do estoque (agora segura — ninguém mais pode entrar)
        stock_read = stock
        logging.info(f"{nurse_name} leu o estoque: {stock_read} unidades disponíveis")

        # 2. Simulação de latência — mesmo com sleep, o semáforo protege
        time.sleep(0.15)

        # 3. Verificação e escrita — estoque não pode ter mudado
        if stock_read >= amount:
            stock -= amount
            logging.info(
                f"{nurse_name} RETIROU {amount} unidades. "
                f"Estoque resultante: {stock}"
            )
        else:
            logging.warning(
                f"{nurse_name} NEGADO — estoque insuficiente "
                f"({stock_read} disponíveis, necessário {amount})"
            )

    finally:
        # ── SAÍDA DA SEÇÃO CRÍTICA — executado SEMPRE (mesmo em exceções) ──
        semaphore.release()
        logging.info(f"{nurse_name} SAIU da seção crítica. Próximo pode entrar.")


# ── Configuração dos enfermeiros ───────────────────────────────────────────────
NURSES = [
    ("Enfermeiro Ana",   30),
    ("Enfermeiro Bruno", 30),
    ("Enfermeiro Carla", 30),
    ("Enfermeiro Diego", 30),
]

EXPECTED_RESULT = 10  # apenas 3 retiradas de 30 cabem em 100 unidades


# ── Execução ───────────────────────────────────────────────────────────────────
def main() -> None:
    logging.info("=" * 60)
    logging.info("INÍCIO DA SIMULAÇÃO — COM SINCRONISMO (Semáforo)")
    logging.info(f"Estoque inicial: {stock} unidades")
    logging.info("=" * 60)

    threads = [
        threading.Thread(
            target=withdraw_medication,
            args=(name, qty),
            name=name,
        )
        for name, qty in NURSES
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    logging.info("=" * 60)
    logging.info(f"Estoque FINAL:    {stock} unidades")
    logging.info(f"Estoque ESPERADO: {EXPECTED_RESULT} unidades")
    logging.info(
        "CONSISTENCIA GARANTIDA! Estoque correto."
        if stock == EXPECTED_RESULT
        else "ERRO — valor inesperado."
    )
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
