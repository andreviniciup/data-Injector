from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

# Conexão com o banco de dados
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Exemplo de modelo (ajuste conforme necessário)
class ProcedimentoOrigem(Base):
    __tablename__ = "rl_procedimento_origem"
    id = Column(Integer, primary_key=True, index=True)
    coluna1 = Column(String)
    coluna2 = Column(Integer)
    # Adicione outras colunas conforme o layout