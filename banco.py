import sqlite3

BANCO_DADOS = "trafego_aereo.db"


def conectar():
    conexao = sqlite3.connect(BANCO_DADOS)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas():
    with conectar() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS aeronaves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                companhia TEXT NOT NULL,
                combustivel INTEGER NOT NULL
                    CHECK (combustivel BETWEEN 0 AND 100),
                emergencia INTEGER NOT NULL DEFAULT 0
                    CHECK (emergencia IN (0, 1)),
                data_entrada TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Aguardando'
                    CHECK (status IN ('Aguardando', 'Pousou'))
            )
        """)

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aeronave_id INTEGER,
                codigo_aeronave TEXT NOT NULL,
                evento TEXT NOT NULL,
                descricao TEXT NOT NULL,
                data_evento TEXT NOT NULL,

                FOREIGN KEY (aeronave_id)
                REFERENCES aeronaves(id)
                ON DELETE SET NULL
            )
        """)


def registrar_evento(aeronave_id, codigo, evento, descricao, data_evento):
    with conectar() as conexao:
        conexao.execute("""
            INSERT INTO historico (
                aeronave_id,
                codigo_aeronave,
                evento,
                descricao,
                data_evento
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            aeronave_id,
            codigo,
            evento,
            descricao,
            data_evento
        ))


def listar_aeronaves():
    with conectar() as conexao:
        resultado = conexao.execute("""
            SELECT *
            FROM aeronaves
            ORDER BY id DESC
        """).fetchall()

        return [dict(registro) for registro in resultado]


def listar_historico():
    with conectar() as conexao:
        resultado = conexao.execute("""
            SELECT *
            FROM historico
            ORDER BY id DESC
        """).fetchall()

        return [dict(registro) for registro in resultado]