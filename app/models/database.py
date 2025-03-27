from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL, DATABASE_SCHEMA

# Usa postgresql+psycopg2 explicitamente
engine = create_engine(f'postgresql+psycopg2://{DATABASE_URL.split("://")[1]}')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base(metadata=MetaData(schema=DATABASE_SCHEMA))

# Exemplo de modelo (ajuste conforme necessário)
class ProcedimentoOrigem(Base):
    __tablename__ = "rl_procedimento_origem"
    __table_args__ = {'schema': DATABASE_SCHEMA}
    id = Column(Integer, primary_key=True, index=True)
    coluna1 = Column(String)
    coluna2 = Column(Integer)
    # Adicione outras colunas conforme o layout