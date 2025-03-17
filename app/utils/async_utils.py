import asyncio
from typing import Any, Coroutine

async def run_async(task: Coroutine) -> Any:
    """
    Executa uma tarefa assíncrona e retorna o resultado.
    
    Args:
        task: Corotina a ser executada.
        
    Returns:
        Resultado da tarefa.
    """
    try:
        return await task
    except Exception as e:
        raise e

async def batch_process(tasks: list, batch_size: int = 10):
    """
    Processa uma lista de tarefas assíncronas em lotes.
    
    Args:
        tasks: Lista de tarefas assíncronas.
        batch_size: Tamanho do lote.
    """
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        await asyncio.gather(*batch)
        await asyncio.sleep(0.1)  # Pequena pausa entre lotes