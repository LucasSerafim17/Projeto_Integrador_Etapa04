"""Gerenciador de logs baseado na aula: arquivo local e CloudWatch opcional."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime

import pandas as pd


class GerenciadorLog:
    def __init__(self, arquivo="sistema.log"):
        self.arquivo = os.path.abspath(arquivo)
        self.logger = logging.getLogger("supervisorio_industrial")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == self.arquivo
                   for h in self.logger.handlers):
            handler = logging.FileHandler(self.arquivo, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(handler)

    @staticmethod
    def _limpar(texto) -> str:
        return str(texto).replace("\n", " ").replace("\r", " ").replace(" - ", " / ")[:300]

    def registrar(self, nivel: str, mensagem: str, usuario: str = "sistema"):
        nivel = nivel.upper()
        if nivel not in ("INFO", "WARNING", "ERROR", "CRITICAL"):
            nivel = "INFO"
        texto = f"{self._limpar(mensagem)} | usuário: {self._limpar(usuario)}"
        self.logger.log(getattr(logging, nivel), texto)
        if os.getenv("CLOUDWATCH_ATIVO", "0") == "1":
            self._enviar_cloudwatch(nivel, mensagem, usuario)

    def _enviar_cloudwatch(self, nivel, mensagem, usuario):
        """Requer grupo e fluxo de logs previamente existentes e permissão IAM."""
        try:
            import boto3
            grupo = os.environ["CLOUDWATCH_LOG_GROUP"]
            fluxo = os.environ["CLOUDWATCH_LOG_STREAM"]
            cliente = boto3.client("logs", region_name=os.getenv("AWS_REGION", "us-east-1"))
            cliente.put_log_events(
                logGroupName=grupo,
                logStreamName=fluxo,
                logEvents=[{"timestamp": int(time.time() * 1000),
                            "message": json.dumps({"nivel": nivel, "mensagem": mensagem,
                                                   "usuario": usuario}, ensure_ascii=False)}],
            )
        except Exception as erro:
            self.logger.error("Falha no envio ao CloudWatch: %s", self._limpar(type(erro).__name__))


def ler_logs_local(arquivo="sistema.log") -> pd.DataFrame:
    colunas = ["data", "nivel", "mensagem"]
    if not os.path.exists(arquivo):
        return pd.DataFrame(columns=colunas)
    registros = []
    with open(arquivo, "r", encoding="utf-8", errors="replace") as f:
        for linha in f:
            partes = linha.strip().split(" - ", 2)
            if len(partes) == 3:
                registros.append(dict(zip(colunas, partes)))
    return pd.DataFrame(registros, columns=colunas)


def ler_logs_cloudwatch(limite: int = 500) -> pd.DataFrame:
    """Consulta simplificada dos eventos CloudWatch. Requer permissões IAM."""
    import boto3
    client = boto3.client("logs", region_name=os.getenv("AWS_REGION", "us-east-1"))
    resp = client.filter_log_events(
        logGroupName=os.environ["CLOUDWATCH_LOG_GROUP"], limit=min(limite, 1000)
    )
    linhas = []
    for item in resp.get("events", []):
        try:
            evento = json.loads(item["message"])
            nivel = evento.get("nivel", "INFO")
            mensagem = f'{evento.get("mensagem", "")} | usuário: {evento.get("usuario", "sistema")}'
        except (ValueError, TypeError):
            nivel, mensagem = "INFO", item.get("message", "")
        linhas.append({"data": datetime.fromtimestamp(item["timestamp"] / 1000),
                       "nivel": nivel, "mensagem": mensagem})
    return pd.DataFrame(linhas, columns=["data", "nivel", "mensagem"])
