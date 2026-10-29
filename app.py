import streamlit as st
import pandas as pd

from datetime import datetime
from heapq import heappush, heappop

from banco import (
    conectar,
    criar_tabelas,
    registrar_evento,
    listar_aeronaves,
    listar_historico
)


# ==================================================
# CONFIGURAÇÃO
# ==================================================

st.set_page_config(
    page_title="Controle de Tráfego Aéreo",
    page_icon="✈️",
    layout="wide"
)

criar_tabelas()


# ==================================================
# CLASSE AERONAVE
# ==================================================

class Aeronave:

    def __init__(
        self,
        id,
        codigo,
        companhia,
        combustivel,
        emergencia,
        data_entrada
    ):
        self.id = id
        self.codigo = codigo
        self.companhia = companhia
        self.combustivel = combustivel
        self.emergencia = bool(emergencia)
        self.data_entrada = datetime.fromisoformat(data_entrada)

    def tempo_espera_segundos(self):
        agora = datetime.now()

        segundos = (
            agora - self.data_entrada
        ).total_seconds()

        return max(0, int(segundos))

    def calcular_prioridade_base(self):
        if self.emergencia:
            return 0

        if self.combustivel <= 10:
            return 1

        if self.combustivel <= 25:
            return 2

        return 3

    def calcular_prioridade_efetiva(self):
        prioridade_base = self.calcular_prioridade_base()

        # Emergências mantêm prioridade máxima.
        if self.emergencia:
            return 0

        # A cada cinco minutos, a prioridade melhora
        # uma posição, até alcançar o nível 1.
        intervalos = self.tempo_espera_segundos() // 300

        return max(1, prioridade_base - intervalos)

    def tempo_espera_minutos(self):
        return round(
            self.tempo_espera_segundos() / 60,
            1
        )

    def to_dict(self):
        return {
            "Código": self.codigo,
            "Companhia": self.companhia,
            "Combustível (%)": self.combustivel,
            "Emergência": "Sim" if self.emergencia else "Não",
            "Prioridade": self.calcular_prioridade_efetiva(),
            "Espera (min)": self.tempo_espera_minutos()
        }


# ==================================================
# CLASSE CONTROLE DE TRÁFEGO AÉREO
# ==================================================

class ControleTrafegoAereo:

    def registrar_aeronave(
        self,
        codigo,
        companhia,
        combustivel,
        emergencia
    ):
        agora = datetime.now().isoformat(timespec="seconds")

        codigo = codigo.strip().upper()
        companhia = companhia.strip()

        if not codigo or not companhia:
            raise ValueError(
                "Informe o código e a companhia aérea."
            )

        with conectar() as conexao:

            existe = conexao.execute("""
                SELECT id
                FROM aeronaves
                WHERE codigo = ?
            """, (codigo,)).fetchone()

            if existe:
                raise ValueError(
                    "Já existe uma aeronave com esse código."
                )

            cursor = conexao.execute("""
                INSERT INTO aeronaves (
                    codigo,
                    companhia,
                    combustivel,
                    emergencia,
                    data_entrada,
                    status
                )
                VALUES (?, ?, ?, ?, ?, 'Aguardando')
            """, (
                codigo,
                companhia,
                combustivel,
                int(emergencia),
                agora
            ))

            aeronave_id = cursor.lastrowid

        registrar_evento(
            aeronave_id,
            codigo,
            "Cadastro",
            "Aeronave adicionada à fila de pouso.",
            agora
        )

    def obter_fila_prioridades(self):
        registros = listar_aeronaves()

        fila = []

        for registro in registros:

            if registro["status"] != "Aguardando":
                continue

            aeronave = Aeronave(
                id=registro["id"],
                codigo=registro["codigo"],
                companhia=registro["companhia"],
                combustivel=registro["combustivel"],
                emergencia=registro["emergencia"],
                data_entrada=registro["data_entrada"]
            )

            prioridade = aeronave.calcular_prioridade_efetiva()

            # Menor número = maior prioridade.
            # Em caso de empate, atende primeiro
            # quem está esperando há mais tempo.
            heappush(
                fila,
                (
                    prioridade,
                    aeronave.data_entrada.timestamp(),
                    aeronave
                )
            )

        return fila

    def listar_fila_ordenada(self):
        fila = self.obter_fila_prioridades()

        aeronaves = []

        while fila:
            _, _, aeronave = heappop(fila)
            aeronaves.append(aeronave)

        return aeronaves

    def realizar_pouso(self):
        fila = self.obter_fila_prioridades()

        if not fila:
            raise ValueError(
                "Não existem aeronaves aguardando pouso."
            )

        _, _, aeronave = heappop(fila)

        agora = datetime.now().isoformat(timespec="seconds")

        with conectar() as conexao:
            conexao.execute("""
                UPDATE aeronaves
                SET status = 'Pousou'
                WHERE id = ?
                  AND status = 'Aguardando'
            """, (aeronave.id,))

        registrar_evento(
            aeronave.id,
            aeronave.codigo,
            "Pouso",
            "Aeronave marcada como pousada na simulação.",
            agora
        )

        return aeronave

    def listar_historico(self):
        return listar_historico()


# ==================================================
# INTERFACE STREAMLIT
# ==================================================

controle = ControleTrafegoAereo()

st.title("Simulador de Controle de Tráfego Aéreo")

st.write(
    "Sistema acadêmico para simular o gerenciamento "
    "de uma fila de prioridades de pouso."
)

st.info(
    "A prioridade é recalculada com base na emergência, "
    "no combustível e no tempo de espera."
)


# ==================================================
# INDICADORES
# ==================================================

registros = listar_aeronaves()

aguardando = [
    aeronave for aeronave in registros
    if aeronave["status"] == "Aguardando"
]

pousadas = [
    aeronave for aeronave in registros
    if aeronave["status"] == "Pousou"
]

emergencias = [
    aeronave for aeronave in aguardando
    if aeronave["emergencia"]
]

col1, col2, col3 = st.columns(3)

col1.metric(
    "Aeronaves aguardando",
    len(aguardando)
)

col2.metric(
    "Pousos simulados",
    len(pousadas)
)

col3.metric(
    "Emergências na fila",
    len(emergencias)
)


# ==================================================
# CADASTRO DE AERONAVES
# ==================================================

st.divider()

st.header("Cadastrar aeronave")

with st.form("formulario_aeronave"):

    col1, col2 = st.columns(2)

    with col1:
        codigo = st.text_input(
            "Código da aeronave",
            placeholder="Ex.: PTABC"
        )

        companhia = st.text_input(
            "Companhia aérea",
            placeholder="Ex.: Companhia Exemplo"
        )

    with col2:
        combustivel = st.slider(
            "Combustível restante (%)",
            min_value=0,
            max_value=100,
            value=50
        )

        emergencia = st.checkbox(
            "Aeronave em situação de emergência"
        )

    cadastrar = st.form_submit_button(
        "Cadastrar aeronave"
    )

    if cadastrar:

        try:
            controle.registrar_aeronave(
                codigo=codigo,
                companhia=companhia,
                combustivel=combustivel,
                emergencia=emergencia
            )

            st.success(
                f"Aeronave {codigo.strip().upper()} cadastrada!"
            )

        except ValueError as erro:
            st.error(str(erro))


# ==================================================
# FILA DE PRIORIDADES
# ==================================================

st.divider()

st.header("Fila de prioridade para pouso")

fila_ordenada = controle.listar_fila_ordenada()

if fila_ordenada:

    dados_fila = [
        aeronave.to_dict()
        for aeronave in fila_ordenada
    ]

    st.dataframe(
        pd.DataFrame(dados_fila),
        use_container_width=True,
        hide_index=True
    )

    proxima = fila_ordenada[0]

    st.subheader("Próxima aeronave da fila")

    st.write(
        f"**Código:** {proxima.codigo}  \n"
        f"**Companhia:** {proxima.companhia}  \n"
        f"**Prioridade calculada:** "
        f"{proxima.calcular_prioridade_efetiva()}"
    )

    if st.button(
        "Simular pouso da próxima aeronave",
        type="primary"
    ):

        try:
            pouso = controle.realizar_pouso()

            st.success(
                f"Pouso simulado: aeronave {pouso.codigo}."
            )

        except ValueError as erro:
            st.warning(str(erro))

else:
    st.info(
        "Não há aeronaves aguardando pouso."
    )


# ==================================================
# HISTÓRICO DE OPERAÇÕES
# ==================================================

st.divider()

st.header("Histórico de operações")

historico = controle.listar_historico()

if historico:

    df_historico = pd.DataFrame(historico)

    df_historico = df_historico.rename(columns={
        "codigo_aeronave": "Aeronave",
        "evento": "Evento",
        "descricao": "Descrição",
        "data_evento": "Data e hora"
    })

    colunas = [
        "Aeronave",
        "Evento",
        "Descrição",
        "Data e hora"
    ]

    st.dataframe(
        df_historico[colunas],
        use_container_width=True,
        hide_index=True
    )

else:
    st.info(
        "Nenhuma operação foi registrada ainda."
    )


# ==================================================
# AERONAVES REGISTRADAS
# ==================================================

st.divider()

st.header("Todas as aeronaves cadastradas")

if registros:

    df_aeronaves = pd.DataFrame(registros)

    df_aeronaves["emergencia"] = (
        df_aeronaves["emergencia"]
        .map({1: "Sim", 0: "Não"})
    )

    df_aeronaves = df_aeronaves.rename(columns={
        "codigo": "Código",
        "companhia": "Companhia",
        "combustivel": "Combustível (%)",
        "emergencia": "Emergência",
        "data_entrada": "Entrada na fila",
        "status": "Situação"
    })

    st.dataframe(
        df_aeronaves[
            [
                "Código",
                "Companhia",
                "Combustível (%)",
                "Emergência",
                "Entrada na fila",
                "Situação"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:
    st.info(
        "Nenhuma aeronave cadastrada."
    )