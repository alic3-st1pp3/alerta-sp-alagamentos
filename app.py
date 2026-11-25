import datetime
import folium
import streamlit as st
from streamlit_folium import st_folium

# Configuração da página
st.set_page_config(
    page_title="Alerta SP — Mobilidade Segura em Dias de Chuva",
    page_icon="🌧️",
    layout="wide",
)

# Estilo visual acessível e amigável
st.markdown(
    """
    <style>
        .stApp {
            background-color: #F8FAFC;
            color: #0F172A;
            font-size: 16px;
        }
        .header-box {
            background-color: #1E3A8A;
            color: #FFFFFF;
            padding: 24px 28px;
            border-radius: 14px;
            margin-bottom: 20px;
        }
        .header-box h1 {
            color: #FFFFFF;
            font-size: 30px;
            margin: 0 0 8px 0;
        }
        .header-box p {
            color: #E2E8F0;
            font-size: 17px;
            margin: 0;
        }
        .card-resumo {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 18px 20px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
        }
        .card-titulo {
            font-size: 15px;
            font-weight: 600;
            color: #475569;
            margin-bottom: 6px;
        }
        .card-valor {
            font-size: 24px;
            font-weight: 700;
            margin: 0;
        }
        .card-sub {
            font-size: 14px;
            color: #475569;
            margin-top: 6px;
        }
        .privacidade-box {
            background-color: #EFF6FF;
            border-left: 4px solid #1E3A8A;
            padding: 12px 16px;
            border-radius: 8px;
            color: #1E293B;
            font-size: 15px;
            margin-bottom: 16px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 10 bairros reais de São Paulo com coordenadas aproximadas
BAIRROS_SP = {
    "Itaquera": (-23.5414, -46.4733),
    "Lapa": (-23.5275, -46.7036),
    "Capão Redondo": (-23.6686, -46.7806),
    "Sé": (-23.5505, -46.6339),
    "Pinheiros": (-23.5673, -46.7019),
    "Santana": (-23.5025, -46.6247),
    "Santo Amaro": (-23.6549, -46.7102),
    "Mooca": (-23.5558, -46.5978),
    "Grajaú": (-23.7764, -46.6889),
    "Tatuapé": (-23.5403, -46.5764),
}

NIVEIS_AGUA = [
    "Risco leve / Poças",
    "Água na calçada",
    "Intransitável - Água alta",
]

# Inicializa as ocorrências no estado da sessão
if "ocorrencias" not in st.session_state:
    hora_atual = datetime.datetime.now().strftime("%H:%M")
    st.session_state.ocorrencias = [
        {
            "id": 1,
            "usuario": "@carlos_zl",
            "bairro": "Itaquera",
            "lat": -23.5414,
            "lon": -46.4733,
            "nivel": "Intransitável - Água alta",
            "horario": hora_atual,
            "descricao": "Água acumulando perto da estação; ônibus com passagem lenta.",
            "foto": None,
            "secou_votos": 0,
        },
        {
            "id": 2,
            "usuario": "@ana_lapa",
            "bairro": "Lapa",
            "lat": -23.5275,
            "lon": -46.7036,
            "nivel": "Água na calçada",
            "horario": hora_atual,
            "descricao": "Calçada tomada pela água e trânsito parado nos arredores.",
            "foto": None,
            "secou_votos": 0,
        },
        {
            "id": 3,
            "usuario": "@marcos_sul",
            "bairro": "Capão Redondo",
            "lat": -23.6686,
            "lon": -46.7806,
            "nivel": "Intransitável - Água alta",
            "horario": hora_atual,
            "descricao": "Trecho baixo com água alta; pedestres buscando ruas mais altas.",
            "foto": None,
            "secou_votos": 0,
        },
        {
            "id": 4,
            "usuario": "@bia_centro",
            "bairro": "Sé",
            "lat": -23.5505,
            "lon": -46.6339,
            "nivel": "Risco leve / Poças",
            "horario": hora_atual,
            "descricao": "Grandes poças na via e retenção no fluxo de veículos.",
            "foto": None,
            "secou_votos": 0,
        },
        {
            "id": 5,
            "usuario": "@rafa_mooca",
            "bairro": "Mooca",
            "lat": -23.5558,
            "lon": -46.5978,
            "nivel": "Água na calçada",
            "horario": hora_atual,
            "descricao": "Acúmulo de água em ponto conhecido de chuva forte.",
            "foto": None,
            "secou_votos": 0,
        },
    ]

if "mensagem_sucesso" not in st.session_state:
    st.session_state.mensagem_sucesso = None

# Cabeçalho principal
st.markdown(
    """
    <div class="header-box">
        <h1>🌧️ Alerta SP — Mobilidade Segura em Dias de Chuva</h1>
        <p>Acompanhe a previsão de chuva, veja pontos de alagamento em São Paulo e planeje seu trajeto com mais tranquilidade.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Barra lateral com filtros e simulador de chuva
with st.sidebar:
    st.header("🧭 Seu Trajeto e Chuva")
    st.write("Escolha os bairros do seu dia a dia e simule o volume de chuva previsto para hoje.")

    lista_bairros = list(BAIRROS_SP.keys())
    bairro_moradia = st.selectbox("Bairro onde você mora", options=lista_bairros, index=0)
    bairro_trabalho = st.selectbox("Bairro onde você trabalha", options=lista_bairros, index=3)

    chuva_mm = st.slider(
        "Chuva prevista hoje (mm)",
        min_value=0,
        max_value=60,
        value=18,
        step=1,
        help="Arraste para simular o volume de chuva esperado para o dia.",
    )

# Cálculo do nível de risco com base nos milímetros de chuva
if chuva_mm < 10:
    risco_texto = "Risco Baixo"
    risco_cor = "#059669"
    risco_aviso = "Trajeto livre de alertas críticos pela chuva."
elif chuva_mm <= 30:
    risco_texto = "Risco Moderado"
    risco_cor = "#D97706"
    risco_aviso = "Atenção: chance de poças e trânsito lento."
else:
    risco_texto = "Risco Alto"
    risco_cor = "#DC2626"
    risco_aviso = "Alerta: chuva forte com alto risco de alagamento."

total_ativos = len(st.session_state.ocorrencias)

# Cartões de resumo no topo (3 colunas)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class="card-resumo">
            <div class="card-titulo">☔ Chuva Prevista Hoje</div>
            <p class="card-valor" style="color: #1E3A8A;">{chuva_mm} mm</p>
            <div class="card-sub">Simulação diária para São Paulo</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="card-resumo">
            <div class="card-titulo">🚦 Nível de Risco no Trajeto</div>
            <p class="card-valor" style="color: {risco_cor};">{risco_texto}</p>
            <div class="card-sub">{bairro_moradia} ↔ {bairro_trabalho} • {risco_aviso}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="card-resumo">
            <div class="card-titulo">📍 Pontos de Alagamento Ativos</div>
            <p class="card-valor" style="color: #DC2626;">{total_ativos}</p>
            <div class="card-sub">Registros exibidos no mapa agora</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### 🗺️ Mapa de Alagamentos em São Paulo")
st.write("Clique em qualquer marcador vermelho no mapa para ver o bairro, o nível da água, o horário e os detalhes do registro.")

# Centraliza o mapa no bairro de moradia selecionado
lat_centro, lon_centro = BAIRROS_SP[bairro_moradia]
mapa = folium.Map(location=[lat_centro, lon_centro], zoom_start=12, tiles="CartoDB positron")

for item in st.session_state.ocorrencias:
    popup_html = f"""
    <div style="font-family: sans-serif; min-width: 200px;">
        <strong style="color: #DC2626; font-size: 14px;">📍 {item['bairro']}</strong><br>
        <span><b>Nível da água:</b> {item['nivel']}</span><br>
        <span><b>Horário:</b> {item['horario']}</span><br>
        <span><b>Relato:</b> {item['descricao']}</span><br>
        <span style="color: #475569; font-size: 12px;">Por {item['usuario']}</span>
    </div>
    """
    folium.Marker(
        location=[item["lat"], item["lon"]],
        popup=folium.Popup(popup_html, max_width=260),
        tooltip=f"{item['bairro']} — {item['nivel']}",
        icon=folium.Icon(color="red", icon="tint", prefix="fa"),
    ).add_to(mapa)

st_folium(mapa, width="100%", height=500)

# Seção Reportar Novo Alagamento
st.divider()
st.markdown("### 🚨 Reportar Novo Alagamento")

if st.session_state.mensagem_sucesso:
    st.success(st.session_state.mensagem_sucesso)
    st.session_state.mensagem_sucesso = None

st.markdown(
    """
    <div class="privacidade-box">
        🔒 <strong>Sua privacidade importa:</strong> Para registrar um ponto, usamos apenas o seu apelido público (<code>@username</code>).
        Não pedimos CPF nem endereço exato, e seu e-mail nunca é exibido publicamente.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("form_reportar_alagamento", clear_on_submit=True):
    col_form1, col_form2 = st.columns(2)

    with col_form1:
        apelido_input = st.text_input(
            "Apelido público (@username) *",
            placeholder="Ex.: @maria_zl ou joao_sp",
            help="Campo obrigatório. Aparecerá no registro no lugar dos seus dados pessoais.",
        )
        bairro_escolhido = st.selectbox(
            "Bairro do alagamento *",
            options=list(BAIRROS_SP.keys()),
        )

    with col_form2:
        nivel_escolhido = st.selectbox(
            "Nível da água *",
            options=NIVEIS_AGUA,
        )
        foto_enviada = st.file_uploader(
            "Foto do local (opcional)",
            type=["png", "jpg", "jpeg"],
            help="Ajude outras pessoas a visualizarem a situação do ponto.",
        )

    descricao_curta = st.text_area(
        "Descrição curta (opcional — até 140 caracteres)",
        max_chars=140,
        placeholder="Ex.: Perto do ponto de ônibus, água subindo rápido na via.",
    )

    enviado = st.form_submit_button("Enviar Alerta", type="primary", use_container_width=True)

    if enviado:
        apelido_limpo = apelido_input.strip()
        if not apelido_limpo:
            st.error("Por favor, preencha o seu apelido público (@username) antes de enviar o alerta.")
        else:
            if not apelido_limpo.startswith("@"):
                apelido_limpo = f"@{apelido_limpo}"

            lat_bairro, lon_bairro = BAIRROS_SP[bairro_escolhido]
            # Pequeno deslocamento proporcional ao ID para não sobrepor exatamente pinos no mesmo bairro
            deslocamento = (len(st.session_state.ocorrencias) % 5) * 0.0025
            novo_id = max([o["id"] for o in st.session_state.ocorrencias], default=0) + 1
            hora_registro = datetime.datetime.now().strftime("%H:%M")

            foto_bytes = foto_enviada.getvalue() if foto_enviada is not None else None
            texto_descricao = descricao_curta.strip() if descricao_curta.strip() else "Ponto de alagamento informado pela comunidade."

            nova_ocorrencia = {
                "id": novo_id,
                "usuario": apelido_limpo,
                "bairro": bairro_escolhido,
                "lat": lat_bairro + deslocamento,
                "lon": lon_bairro - deslocamento,
                "nivel": nivel_escolhido,
                "horario": hora_registro,
                "descricao": texto_descricao,
                "foto": foto_bytes,
                "secou_votos": 0,
            }

            st.session_state.ocorrencias.append(nova_ocorrencia)
            st.session_state.mensagem_sucesso = "Obrigado por ajudar outros trabalhadores!"
            st.rerun()
