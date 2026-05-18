"""
Distribuição de Medicamentos em Hospital
VERSÃO SEM SINCRONISMO — Demonstração de Condição de Corrida (Race Condition)

Disciplina: Princípios de Software Básico — UFRPE
Problema: Threads representando enfermeiros acessando estoque compartilhado
         sem nenhum controle de acesso concorrente.

Como o erro é forçado:
    O Python possui o GIL (Global Interpreter Lock), que protege operações
    simples. Porém, a operação `stock -= amount` é composta por múltiplos
    bytecodes (LOAD → SUBTRACT → STORE). Ao inserir um time.sleep() entre a
    leitura e a escrita, simulamos a latência de um sistema real (ex: consulta
    a banco de dados) e forçamos o GIL a ser liberado — permitindo que outra
    thread entre na seção crítica antes que a primeira termine.
"""

import logging
import threading
import time


class ColoredFormatter(logging.Formatter):
    """Formatter que aplica cor ANSI à mensagem conforme palavras-chave."""

    def format(self, record: logging.LogRecord) -> str:

        # ── Códigos de cor ANSI ────────────────────────────────────────────────────────
        RESET   = "\033[0m"
        BOLD    = "\033[1m"
        RED     = "\033[91m"    # erros críticos / inconsistência
        YELLOW  = "\033[93m"    # avisos / negação de acesso
        CYAN    = "\033[96m"    # leitura de estoque (informativo)
        WHITE   = "\033[97m"    # mensagens neutras / cabeçalho
        MAGENTA = "\033[95m"    # retirada bem-sucedida

        msg = super().format(record)

        # Inconsistência crítica detectada
        if "INCONSISTENCIA" in record.getMessage() or "negativo" in record.getMessage():
            return f"{BOLD}{RED}{msg}{RESET}"

        # Negação de acesso (warning)
        if record.levelno == logging.WARNING or "NEGADO" in record.getMessage():
            return f"{YELLOW}{msg}{RESET}"

        # Retirada bem-sucedida
        if "RETIROU" in record.getMessage():
            return f"{MAGENTA}{msg}{RESET}"

        # Leitura de estoque
        if "leu o estoque" in record.getMessage():
            return f"{CYAN}{msg}{RESET}"

        # Cabeçalho / separadores
        if "===" in record.getMessage() or "INÍCIO" in record.getMessage() or "FINAL" in record.getMessage():
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


# ── Função executada por cada enfermeiro (thread) ─────────────────────────────
def withdraw_medication(nurse_name: str, amount: int) -> None:
    """Tenta retirar `amount` unidades do estoque SEM proteção alguma."""
    global stock

    # 1. Leitura do estoque
    stock_read = stock
    logging.info(f"{nurse_name} leu o estoque: {stock_read} unidades disponíveis")

    # 2. Simulação de latência (ex.: validação em banco de dados, chamada de rede)
    #    É AQUI que o GIL é liberado e outra thread pode entrar.
    time.sleep(0.15)

    # 3. Verificação e escrita — baseadas no valor JÁ DESATUALIZADO
    if stock_read >= amount:
        # Outra thread pode ter reduzido o estoque durante o sleep acima!
        stock -= amount          # operação não-atômica (LOAD → SUB → STORE)
        logging.info(
            f"{nurse_name} RETIROU {amount} unidades. "
            f"Estoque resultante: {stock}"
        )
    else:
        logging.warning(
            f"{nurse_name} NEGADO — estoque insuficiente ao ler "
            f"(leu {stock_read}, precisava de {amount})"
        )


# ── Configuração dos enfermeiros ───────────────────────────────────────────────
NURSES = [
    ("Enfermeira Ana",   30),
    ("Enfermeiro Bruno", 30),
    ("Enfermeira Carla", 30),
    ("Enfermeiro Diego", 30),
]

# Valor correto esperado: o estoque não deve ficar negativo.
# Com 100 unidades e 4 pedidos de 30 cada (total 120), apenas 3 retiradas
# são possíveis → estoque correto = 100 - 3*30 = 10.
INITIAL_STOCK   = stock
EXPECTED_RESULT = 10  # Diego deveria ser negado, pois ao retirar 30 unidades ele ficaria com -20


# ── Execução ───────────────────────────────────────────────────────────────────
def main() -> None:
    logging.info("=" * 60)
    logging.info("INÍCIO DA SIMULAÇÃO — SEM SINCRONISMO")
    logging.info(f"Estoque inicial: {INITIAL_STOCK} unidades")
    logging.info("=" * 60)

    threads = [
        threading.Thread(
            target=withdraw_medication,
            args=(name, qty),
            name=name,
        )
        for name, qty in NURSES
    ]

    # Inicia todas as threads ao mesmo tempo para maximizar a concorrência
    for t in threads:
        t.start()

    for t in threads:
        t.join()

    logging.info("=" * 60)
    logging.info(f"Estoque FINAL:    {stock} unidades")
    logging.info(f"Estoque CORRETO ESPERADO: {EXPECTED_RESULT} unidades")
    logging.info(
        f"INCONSISTENCIA DETECTADA: Estoque ficou em {stock} "
        f"(deveria ser {EXPECTED_RESULT}). Estoque negativo = dados corrompidos!"
        if stock != EXPECTED_RESULT
        else "Sem inconsistencia desta vez. Execute novamente."
    )
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
