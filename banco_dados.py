"""Persistência do supervisório (SQLite para demonstração ou MySQL).

Para MySQL: DATABASE_URL=mysql+pymysql://usuario:senha@servidor:3306/supervisorio
A aplicação não cria bancos MySQL, somente as tabelas dentro do banco existente.
"""
from __future__ import annotations

import os
from datetime import datetime
from functools import lru_cache

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(20), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class Equipamento(Base):
    __tablename__ = "equipamentos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    setor: Mapped[str] = mapped_column(String(80), nullable=False, default="Linha demonstrativa")


class EventoProcesso(Base):
    __tablename__ = "eventos_processo"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True)
    equipamento: Mapped[str] = mapped_column(String(80), nullable=False)
    evento: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario: Mapped[str] = mapped_column(String(60), nullable=False)
    nivel: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")
    detalhes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class Medicao(Base):
    __tablename__ = "medicoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True)
    temperatura: Mapped[float] = mapped_column(Float, nullable=False)
    velocidade: Mapped[int] = mapped_column(Integer, nullable=False)
    motor_ligado: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sensor_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pecas_produzidas: Mapped[int] = mapped_column(Integer, nullable=False)


class EstadoProcesso(Base):
    __tablename__ = "estado_processo"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    motor_ligado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    velocidade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    temperatura: Mapped[float] = mapped_column(Float, nullable=False, default=28.0)
    sensor_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pecas_produzidas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ultimo_tick: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


PERFIS = ("admin", "operador", "engenheiro")


@lru_cache(maxsize=1)
def obter_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./dados_supervisorio.db")
    argumentos = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=argumentos)


def abrir_sessao() -> Session:
    return Session(obter_engine())


def inicializar_banco(modo_demo: bool = True):
    Base.metadata.create_all(obter_engine())
    with abrir_sessao() as db:
        if db.get(EstadoProcesso, 1) is None:
            db.add(EstadoProcesso(id=1, motor_ligado=False, velocidade=0, temperatura=28.0))
        for nome in ("Motor 01", "Esteira 01", "Sensor 01"):
            if db.scalar(select(Equipamento).where(Equipamento.nome == nome)) is None:
                db.add(Equipamento(nome=nome, setor="Célula de transporte"))
        db.commit()

    # Contas didáticas: somente no modo de demonstração.
    if modo_demo:
        from autenticacao import criar_hash
        exemplos = (("admin", "admin123", "admin"),
                    ("operador", "operador123", "operador"),
                    ("engenheiro", "engenheiro123", "engenheiro"))
        with abrir_sessao() as db:
            for nome, senha, perfil in exemplos:
                if db.scalar(select(Usuario).where(Usuario.nome == nome)) is None:
                    db.add(Usuario(nome=nome, senha_hash=criar_hash(senha), perfil=perfil, ativo=True))
            db.commit()
    else:
        # Opcional: cria o primeiro administrador sem usar contas de demonstração.
        nome_inicial = os.getenv("ADMIN_INICIAL_USUARIO", "").strip().lower()
        senha_inicial = os.getenv("ADMIN_INICIAL_SENHA", "")
        if nome_inicial and len(senha_inicial) >= 12:
            from autenticacao import criar_hash
            with abrir_sessao() as db:
                usuario = db.scalar(select(Usuario).where(Usuario.nome == nome_inicial))
                if usuario is None:
                    db.add(Usuario(nome=nome_inicial, senha_hash=criar_hash(senha_inicial),
                                   perfil="admin", ativo=True))
                    db.commit()


def procurar_usuario(nome: str) -> dict | None:
    with abrir_sessao() as db:
        obj = db.scalar(select(Usuario).where(Usuario.nome == nome))
        if obj is None:
            return None
        return {"id": obj.id, "nome": obj.nome, "senha_hash": obj.senha_hash,
                "perfil": obj.perfil, "ativo": obj.ativo}


def listar_usuarios() -> list[dict]:
    with abrir_sessao() as db:
        objs = db.scalars(select(Usuario).order_by(Usuario.nome)).all()
        return [{"ID": x.id, "Usuário": x.nome, "Perfil": x.perfil,
                 "Ativo": bool(x.ativo), "Criado em": x.criado_em} for x in objs]


def cadastrar_usuario(nome: str, senha_hash: str, perfil: str) -> tuple[bool, str]:
    nome = nome.strip().lower()
    if not nome or len(nome) > 60 or any(c.isspace() for c in nome):
        return False, "Informe um usuário válido, sem espaços (máximo de 60 caracteres)."
    if perfil not in PERFIS:
        return False, "Perfil inválido."
    with abrir_sessao() as db:
        if db.scalar(select(Usuario).where(Usuario.nome == nome)) is not None:
            return False, "Este nome de usuário já existe."
        db.add(Usuario(nome=nome, senha_hash=senha_hash, perfil=perfil, ativo=True))
        db.commit()
    return True, "Usuário cadastrado com sucesso."


def editar_usuario(nome: str, perfil: str, ativo: bool, novo_hash: str | None, executor: str) -> tuple[bool, str]:
    if perfil not in PERFIS:
        return False, "Perfil inválido."
    with abrir_sessao() as db:
        obj = db.scalar(select(Usuario).where(Usuario.nome == nome))
        if obj is None:
            return False, "Usuário não localizado."
        if nome == executor and (not ativo or perfil != "admin"):
            return False, "Não é permitido desativar sua própria conta ou remover seu perfil de administrador."
        if obj.perfil == "admin" and (not ativo or perfil != "admin"):
            admins = db.scalars(select(Usuario).where(Usuario.perfil == "admin", Usuario.ativo.is_(True))).all()
            if len(admins) < 2:
                return False, "Deve permanecer pelo menos um administrador ativo."
        obj.perfil, obj.ativo = perfil, bool(ativo)
        if novo_hash is not None:
            obj.senha_hash = novo_hash
        db.commit()
    return True, "Cadastro atualizado."


def registrar_evento(equipamento: str, evento: str, usuario: str,
                     nivel: str = "INFO", detalhes: str = "", db: Session | None = None):
    item = EventoProcesso(equipamento=equipamento, evento=evento,
                          usuario=usuario or "sistema", nivel=nivel,
                          detalhes=detalhes)
    if db is not None:
        db.add(item)
    else:
        with abrir_sessao() as sessao:
            sessao.add(item)
            sessao.commit()


def listar_eventos(limite: int = 2000) -> list[dict]:
    with abrir_sessao() as db:
        objs = db.scalars(select(EventoProcesso).order_by(EventoProcesso.data_hora.desc(), EventoProcesso.id.desc()).limit(limite)).all()
        return [{"Data/Hora": x.data_hora, "Equipamento": x.equipamento,
                 "Evento": x.evento, "Usuário": x.usuario, "Nível": x.nivel,
                 "Detalhes": x.detalhes} for x in objs]


def listar_medicoes(limite: int = 2000) -> list[dict]:
    with abrir_sessao() as db:
        objs = db.scalars(select(Medicao).order_by(Medicao.data_hora.desc(), Medicao.id.desc()).limit(limite)).all()
        return [{"Data/Hora": x.data_hora, "Temperatura (°C)": round(x.temperatura, 2),
                 "Velocidade (RPM)": x.velocidade, "Motor ligado": bool(x.motor_ligado),
                 "Sensor ativo": bool(x.sensor_ativo), "Peças produzidas": x.pecas_produzidas} for x in reversed(objs)]


def ler_estado() -> dict:
    with abrir_sessao() as db:
        obj = db.get(EstadoProcesso, 1)
        if obj is None:
            raise RuntimeError("Banco não inicializado. Execute inicializar_banco().")
        return {"motor_ligado": bool(obj.motor_ligado), "velocidade": obj.velocidade,
                "temperatura": obj.temperatura, "sensor_ativo": bool(obj.sensor_ativo),
                "pecas_produzidas": obj.pecas_produzidas, "ultimo_tick": obj.ultimo_tick}
