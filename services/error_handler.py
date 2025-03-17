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

    def log_error(self, message: str):
        """
        Registra um erro no log e na lista de erros.
        
        Args:
            message: Mensagem de erro.
        """
        logger.error(message)
        self.error_log.append(message)

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