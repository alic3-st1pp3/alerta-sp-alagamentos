import datetime
import io
import json
import re
import urllib.parse
import feedparser
from google import genai
from google.genai import types
import pandas as pd
from PIL import Image
import pydeck as pdk
import requests
import streamlit as st

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
        .legenda-box {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 12px;
            font-size: 15px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Bairros da cidade de São Paulo com coordenadas aproximadas
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
    "Jabaquara": (-23.6464, -46.6408),
    "Butantã": (-23.5719, -46.7081),
    "Zona Leste": (-23.5450, -46.4950),
    "Zona Sul": (-23.6500, -46.6900),
    "Zona Norte": (-23.4950, -46.6300),
    "Zona Oeste": (-23.5550, -46.7100),
    "Centro": (-23.5489, -46.6388),
}

MUNICIPIOS_GRANDE_SP = [
    "sao paulo",
    "guarulhos",
    "osasco",
    "santo andre",
    "sao bernardo",
    "sao caetano",
    "diadema",
    "maua",
    "ribeirao pires",
    "rio grande da serra",
    "barueri",
    "carapicuiba",
    "cotia",
    "embu das artes",
    "itapecerica da serra",
    "jandira",
    "santana de parnaiba",
    "taboao da serra",
    "aruja",
    "ferraz de vasconcelos",
    "itaquaquecetuba",
    "mogi das cruzes",
    "poa",
    "suzano",
    "caieiras",
    "cajamar",
    "franco da rocha",
    "francisco morato",
    "mairipora",
]

TERMOS_INTERIOR_EXCLUIR = [
    "campinas",
    "santos",
    "baixada santista",
    "sorocaba",
    "ribeirao preto",
    "sao jose dos campos",
    "vale do paraiba",
    "bauru",
    "franca",
    "marilia",
    "presidente prudente",
    "sao jose do rio preto",
    "piracicaba",
    "jundiai",
    "araraquara",
    "botucatu",
    "itu",
    "americana",
    "limeira",
    "ubatuba",
    "caraguatatuba",
    "sao sebastiao",
    "ilhabela",
]

NIVEIS_AGUA = [
    "Risco leve / Poças",
    "Água na calçada",
    "Intransitável - Água alta",
]


def normalizar_texto(texto: str) -> str:
    mapa_acentos = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return texto.translate(mapa_acentos).lower()


def validar_imagem_com_ia(foto_bytes: bytes):
    """Valida se a imagem é segura e relacionada a rua/alagamento usando o Gemini."""
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return False, "Chave GEMINI_API_KEY não configurada nos Secrets do Streamlit."

    try:
        client = genai.Client(api_key=api_key)
        imagem = Image.open(io.BytesIO(foto_bytes))

        prompt = (
            "Analise esta imagem enviada para um sistema público de alerta de alagamentos em São Paulo. "
            "Responda APENAS em JSON válido com duas chaves booleanas e uma string curta em português:\n"
            '{"segura": true/false, "relacionada_alagamento_ou_via": true/false, "motivo": "explicação curta"}\n'
            "Regras:\n"
            "- segura deve ser false se houver nudez, pornografia, conteúdo sexual, violência explícita ou ofensivo.\n"
            "- relacionada_alagamento_ou_via deve ser true APENAS se a foto mostrar rua, avenida, estação, calçada, chuva, poça, enchente ou trânsito afetado por água.\n"
            "- Se for selfie, meme, tela, animal ou foto interna sem relação com via/chuva/alagamento, relacionada_alagamento_ou_via deve ser false."
        )

        resposta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[imagem, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        resultado = json.loads(resposta.text)
        segura = bool(resultado.get("segura", False))
        relacionada = bool(resultado.get("relacionada_alagamento_ou_via", False))
        motivo = resultado.get("motivo", "Imagem fora dos critérios do sistema.")

        if not segura:
            return False, "Imagem bloqueada pelo filtro de segurança (conteúdo impróprio detectado)."
        if not relacionada:
            return False, f"Imagem recusada: {motivo}. Envie apenas fotos reais da rua ou do alagamento."

        return True, "Imagem validada com sucesso."
    except Exception as e:
        return False, f"Não foi possível validar a imagem agora ({e}). Tente novamente."


@st.cache_data(ttl=1800)
def buscar_chuva_real_sp():
    """Busca previsão real de precipitação (mm) e temperatura para São Paulo via Open-Meteo."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=-23.5505&longitude=-46.6339"
        "&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
        "&timezone=America%2FSao_Paulo"
    )
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json().get("daily", {})
        chuva_hoje = float(data.get("precipitation_sum", [0.0])[0] or 0.0)
        temp_max = data.get("temperature_2m_max", [None])[0]
        temp_min = data.get("temperature_2m_min", [None])[0]
        return round(chuva_hoje, 1), temp_min, temp_max, True
    except Exception:
        return 12.0, None, None, False


@st.cache_data(ttl=900)
def buscar_noticias_sp_e_grande_sp():
    """
    Busca notícias recentes sobre alagamento e chuva focadas em São Paulo e Grande SP,
    excluindo manchetes voltadas a cidades do interior paulista.
    """
    query = urllib.parse.quote(
        '(alagamento OR enchente OR "chuva forte") ("São Paulo" OR "Grande SP" OR Guarulhos OR Osasco OR ABC)'
    )
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    noticias = []

    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            titulo = entry.get("title", "Notícia sem título")
            link = entry.get("link", "")
            fonte = entry.get("source", {}).get("title", "Imprensa local")
            texto_norm = normalizar_texto(f"{titulo} {fonte}")

            # Exclui notícias claramente ligadas ao interior/litoral fora da Grande SP
            if any(re.search(rf"\b{re.escape(termo)}\b", texto_norm) for termo in TERMOS_INTERIOR_EXCLUIR):
                continue

            # Confirma vínculo com município de SP ou Grande SP
            tem_grande_sp = any(
                re.search(rf"\b{re.escape(mun)}\b", texto_norm) for mun in MUNICIPIOS_GRANDE_SP
            )
            if not tem_grande_sp and "sp" not in texto_norm.split():
                continue

            bairro_detectado = None
            for bairro in BAIRROS_SP:
                bairro_norm = normalizar_texto(bairro)
                if re.search(rf"\b{re.escape(bairro_norm)}\b", texto_norm):
                    bairro_detectado = bairro
                    break

            # Se for notícia da capital/Grande SP sem bairro específico citado, associa ao Centro de SP para plotar no mapa
            if not bairro_detectado:
                bairro_detectado = "Centro"

            noticias.append(
                {
                    "titulo": titulo,
                    "link": link,
                    "fonte": fonte,
                    "bairro_detectado": bairro_detectado,
                }
            )
    except Exception:
        pass

    return noticias[:6]


# Inicializa ocorrências de usuários no estado da sessão
if "ocorrencias_usuarios" not in st.session_state:
    hora_atual = datetime.datetime.now().strftime("%H:%M")
    st.session_state.ocorrencias_usuarios = [
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
    ]

if "mensagem_sucesso" not in st.session_state:
    st.session_state.mensagem_sucesso = None

chuva_real_mm, temp_min, temp_max, clima_ok = buscar_chuva_real_sp()
noticias_sp = buscar_noticias_sp_e_grande_sp()

# Monta pinos de notícias reais (roxo)
pinos_noticias = []
for idx, n in enumerate(noticias_sp):
    bairro = n["bairro_detectado"]
    lat_b, lon_b = BAIRROS_SP.get(bairro, BAIRROS_SP["Centro"])
    desloc = ((idx % 5) - 2) * 0.0045
    pinos_noticias.append(
        {
            "tipo_label": "Notícia Real (SP/Grande SP)",
            "bairro": bairro,
            "lat": lat_b + desloc,
            "lon": lon_b - desloc,
            "resumo": f"{n['fonte']}: {n['titulo']}",
            "cor": [139, 92, 246, 230],  # Roxo
        }
    )

# Cabeçalho principal
st.markdown(
    """
    <div class="header-box">
        <h1>🌧️ Alerta SP — Mobilidade Segura em Dias de Chuva</h1>
        <p>Dados reais de chuva em São Paulo, notícias locais, relatos validados por IA e mapa de pontos críticos.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Barra lateral
with st.sidebar:
    st.header("🧭 Seu Trajeto e Chuva")
    lista_bairros = list(BAIRROS_SP.keys())
    bairro_moradia = st.selectbox("Bairro onde você mora", options=lista_bairros, index=0)
    bairro_trabalho = st.selectbox("Bairro onde você trabalha", options=lista_bairros, index=3)

    st.divider()
    st.subheader("🌦️ Clima Real (São Paulo)")
    if clima_ok:
        st.success(f"Previsão real hoje: **{chuva_real_mm} mm**")
        if temp_min is not None and temp_max is not None:
            st.caption(f"Temperatura prevista: {temp_min}°C a {temp_max}°C")
    else:
        st.warning("Sem conexão com a API meteorológica no momento; usando estimativa.")

    usar_simulacao = st.checkbox("Simular outro volume de chuva manualmente", value=False)
    if usar_simulacao:
        chuva_ativa_mm = float(
            st.slider("Chuva simulada (mm)", min_value=0, max_value=80, value=int(chuva_real_mm), step=1)
        )
    else:
        chuva_ativa_mm = chuva_real_mm

    if st.button("🔄 Atualizar dados reais agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Verifica pontos ativos no trajeto
bairros_trajeto = {bairro_moradia, bairro_trabalho}
pontos_usuario_trajeto = [
    item for item in st.session_state.ocorrencias_usuarios if item["bairro"] in bairros_trajeto
]
noticias_no_trajeto = [
    item for item in pinos_noticias if item["bairro"] in bairros_trajeto
]
tem_alerta_trajeto = len(pontos_usuario_trajeto) > 0 or len(noticias_no_trajeto) > 0

if tem_alerta_trajeto:
    risco_texto = "Risco Alto"
    risco_cor = "#DC2626"
    risco_aviso = "Ponto ou notícia de alagamento no seu trajeto!"
elif chuva_ativa_mm < 10:
    risco_texto = "Risco Baixo"
    risco_cor = "#059669"
    risco_aviso = "Trajeto livre de alertas críticos pela chuva."
elif chuva_ativa_mm <= 30:
    risco_texto = "Risco Moderado"
    risco_cor = "#D97706"
    risco_aviso = "Atenção: chance de poças e trânsito lento."
else:
    risco_texto = "Risco Alto"
    risco_cor = "#DC2626"
    risco_aviso = "Alerta: chuva forte com alto risco de alagamento."

if tem_alerta_trajeto:
    bairros_afetados = sorted(
        {p["bairro"] for p in pontos_usuario_trajeto} | {n["bairro"] for n in noticias_no_trajeto}
    )
    st.error(
        f"⚠️ **Atenção no seu trajeto ({bairro_moradia} ↔ {bairro_trabalho}):** "
        f"Há registro ou notícia envolvendo **{', '.join(bairros_afetados)}**. "
        f"Considere sair mais cedo, aguardar ou buscar rota alternativa."
    )

total_pinos = len(st.session_state.ocorrencias_usuarios) + len(pinos_noticias)

# Cartões de resumo no topo
col1, col2, col3 = st.columns(3)

with col1:
    origem_chuva = "Simulação manual" if usar_simulacao else "Previsão real (Open-Meteo)"
    st.markdown(
        f"""
        <div class="card-resumo">
            <div class="card-titulo">☔ Chuva Prevista Hoje</div>
            <p class="card-valor" style="color: #1E3A8A;">{chuva_ativa_mm} mm</p>
            <div class="card-sub">{origem_chuva}</div>
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
            <div class="card-titulo">📍 Marcadores no Mapa</div>
            <p class="card-valor" style="color: #DC2626;">{total_pinos}</p>
            <div class="card-sub">{len(st.session_state.ocorrencias_usuarios)} da comunidade • {len(pinos_noticias)} de notícias</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Mapa nativo PyDeck focado na cidade de São Paulo
st.markdown("### 🗺️ Mapa de Alagamentos e Notícias — Cidade de São Paulo")

st.markdown(
    """
    <div class="legenda-box">
        <strong>Legenda dos marcadores:</strong> &nbsp;&nbsp;
        🔴 <strong>Vermelho:</strong> Comunidade <strong>com foto</strong> &nbsp;&nbsp;|&nbsp;&nbsp;
        🟠 <strong>Laranja:</strong> Comunidade <strong>sem foto</strong> &nbsp;&nbsp;|&nbsp;&nbsp;
        🟣 <strong>Roxo:</strong> Notícia real de chuva/alagamento (SP / Grande SP)
    </div>
    """,
    unsafe_allow_html=True,
)

dados_mapa = []

for item in st.session_state.ocorrencias_usuarios:
    tem_foto = item.get("foto") is not None
    dados_mapa.append(
        {
            "lat": item["lat"],
            "lon": item["lon"],
            "bairro": item["bairro"],
            "tipo_label": "Comunidade (com foto)" if tem_foto else "Comunidade (sem foto)",
            "resumo": f"{item['nivel']} — {item['descricao']} ({item['usuario']})",
            "cor": [220, 38, 38, 235] if tem_foto else [249, 115, 22, 235],
        }
    )

for pino in pinos_noticias:
    dados_mapa.append(
        {
            "lat": pino["lat"],
            "lon": pino["lon"],
            "bairro": pino["bairro"],
            "tipo_label": pino["tipo_label"],
            "resumo": pino["resumo"],
            "cor": pino["cor"],
        }
    )

df_mapa = pd.DataFrame(dados_mapa)

# Garante que o foco inicial fique dentro da cidade de São Paulo
lat_foco, lon_foco = BAIRROS_SP.get(bairro_moradia, (-23.5505, -46.6339))

layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_mapa,
    get_position="[lon, lat]",
    get_color="cor",
    get_radius=420,
    pickable=True,
    auto_highlight=True,
)

view_state = pdk.ViewState(
    latitude=lat_foco,
    longitude=lon_foco,
    zoom=11.3,
    min_zoom=10.2,
    max_zoom=15.0,
    pitch=0,
)

tooltip = {
    "html": "<b>{tipo_label}</b><br/><b>Bairro:</b> {bairro}<br/>{resumo}",
    "style": {
        "backgroundColor": "#0F172A",
        "color": "#FFFFFF",
        "fontSize": "13px",
        "borderRadius": "8px",
        "padding": "10px",
    },
}

st.pydeck_chart(
    pdk.Deck(
        map_style="light",
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip,
    ),
    use_container_width=True,
    height=480,
)

# Mural de notícias reais focadas em SP e Grande SP
st.divider()
st.markdown("### 📰 Notícias Reais — São Paulo e Grande SP")
st.write("Manchetes recentes da imprensa local focadas na capital e região metropolitana (sem cidades do interior). Passe o mouse nos pontos roxos no mapa para ver os detalhes.")

if not noticias_sp:
    st.info("Nenhuma manchete recente encontrada agora para SP/Grande SP. Clique em 'Atualizar dados reais agora' na barra lateral.")
else:
    for n in noticias_sp:
        with st.container(border=True):
            st.markdown(f"**{n['titulo']}**")
            st.caption(f"Fonte: {n['fonte']} • 📍 Referência no mapa: **{n['bairro_detectado']}**")
            if n["link"]:
                st.markdown(f"[Abrir notícia]({n['link']})")

# Formulário de registro colaborativo com moderação de imagem por IA
st.divider()
st.markdown("### 🚨 Reportar Novo Alagamento")

if st.session_state.mensagem_sucesso:
    st.success(st.session_state.mensagem_sucesso)
    st.session_state.mensagem_sucesso = None

st.markdown(
    """
    <div class="privacidade-box">
        🔒 <strong>Privacidade e Segurança:</strong> Usamos apenas o seu apelido público (<code>@username</code>).
        Não pedimos CPF nem endereço exato. Fotos enviadas passam por <strong>verificação automática por IA</strong> para garantir que sejam registros reais de ruas ou alagamentos.
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
            "Foto do local (opcional — verificada automaticamente por IA)",
            type=["png", "jpg", "jpeg"],
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
            foto_bytes = None
            imagem_aprovada = True

            if foto_enviada is not None:
                foto_bytes = foto_enviada.getvalue()
                with st.spinner("🤖 Analisando a imagem com IA para garantir segurança e relevância..."):
                    imagem_aprovada, mensagem_ia = validar_imagem_com_ia(foto_bytes)

                if not imagem_aprovada:
                    st.error(f"🚫 {mensagem_ia}")

            if imagem_aprovada:
                if not apelido_limpo.startswith("@"):
                    apelido_limpo = f"@{apelido_limpo}"

                lat_bairro, lon_bairro = BAIRROS_SP[bairro_escolhido]
                deslocamento = (len(st.session_state.ocorrencias_usuarios) % 5) * 0.0025
                novo_id = max([o["id"] for o in st.session_state.ocorrencias_usuarios], default=0) + 1
                hora_registro = datetime.datetime.now().strftime("%H:%M")

                texto_descricao = (
                    descricao_curta.strip()
                    if descricao_curta.strip()
                    else "Ponto de alagamento informado pela comunidade."
                )

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

                st.session_state.ocorrencias_usuarios.append(nova_ocorrencia)
                st.session_state.mensagem_sucesso = "Obrigado por ajudar outros trabalhadores!"
                st.rerun()

# Lista de ocorrências da comunidade
st.divider()
st.markdown("### 📋 Ocorrências da Comunidade e Validação")
st.write("A água baixou por aí? Clique em **Já secou**. Com **3 confirmações**, o registro sai do mapa.")

if not st.session_state.ocorrencias_usuarios:
    st.info("Não há relatos de usuários ativos no momento.")
else:
    ocorrencia_para_remover = None

    for item in st.session_state.ocorrencias_usuarios:
        with st.container(border=True):
            c_info, c_foto, c_acao = st.columns([4, 2, 2])

            with c_info:
                destaque_trajeto = " • 🧭 **No seu trajeto**" if item["bairro"] in bairros_trajeto else ""
                tem_foto_tag = "📷 Com foto verificada" if item.get("foto") is not None else "📝 Sem foto"
                st.markdown(f"**📍 {item['bairro']}** — *{item['nivel']}* • {tem_foto_tag}{destaque_trajeto}")
                st.write(item["descricao"])
                st.caption(
                    f"Registrado às {item['horario']} por **{item['usuario']}** • "
                    f"Confirmações de que secou: **{item['secou_votos']}/3**"
                )

            with c_foto:
                if item.get("foto") is not None:
                    st.image(item["foto"], caption="Foto validada", use_container_width=True)
                else:
                    st.caption("Sem foto anexada")

            with c_acao:
                st.write("")
                if st.button("✅ Já secou", key=f"secou_{item['id']}", use_container_width=True):
                    item["secou_votos"] += 1
                    if item["secou_votos"] >= 3:
                        ocorrencia_para_remover = item["id"]
                    st.rerun()

    if ocorrencia_para_remover is not None:
        st.session_state.ocorrencias_usuarios = [
            o for o in st.session_state.ocorrencias_usuarios if o["id"] != ocorrencia_para_remover
        ]
        st.rerun()
