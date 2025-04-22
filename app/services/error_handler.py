import logging
from typing import List

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ErrorHandler")

class ErrorHandler:
    def __init__(self):
        self.error_log = []

    def log_error(error, sensitive_data=None):
        """Log de erros sem expor dados sensíveis"""
        logger = logging.getLogger('security')
        message = f"Erro: {type(error).__name__}"
        if sensitive_data:
            message += f" (Dados: REDACTED)"  # Não loga dados reais
        logger.error(message)

    def get_error_log(self) -> List[str]:
        """
        Retorna a lista de erros registrados.
        
        Returns:
            Lista de mensagens de erro.
        """
        return self.error_log

    def clear_error_log(self):
        """
        Limpa a lista de erros.
        """
        self.error_log = []