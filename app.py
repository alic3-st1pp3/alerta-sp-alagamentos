import datetime
import io
import json
import re
import time
import urllib.parse
import feedparser
from google import genai
from google.genai import types
import pandas as pd
from PIL import Image
import pydeck as pdk
import requests
import streamlit as st

# Configuração da página e tema claro consistente
st.set_page_config(
    page_title="Alerta SP — Mobilidade Segura em Dias de Chuva",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo visual acessível e de alto contraste
st.markdown(
    """
    <style>
        /* Área principal clara */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            font-size: 16px;
        }

        /* Barra lateral clara e legível */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div,
        [data-testid="stSidebarContent"] {
            background-color: #F1F5F9 !important;
            color: #0F172A !important;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] {
            color: #0F172A !important;
        }

        /* Rótulos e textos gerais da área principal */
        [data-testid="stMain"] label,
        [data-testid="stMain"] .stTextInput label,
        [data-testid="stMain"] .stSelectbox label,
        [data-testid="stMain"] .stTextArea label,
        [data-testid="stMain"] .stFileUploader label,
        [data-testid="stMain"] .stSlider label,
        [data-testid="stMain"] .stCheckbox label {
            color: #0F172A !important;
            font-weight: 600 !important;
            font-size: 15px !important;
        }

        [data-testid="stMain"] p,
        [data-testid="stMain"] [data-testid="stCaptionContainer"] {
            color: #1E293B;
        }

        /* Cabeçalho azul escuro */
        .header-box {
            background-color: #1E3A8A !important;
            color: #FFFFFF !important;
            padding: 24px 28px;
            border-radius: 14px;
            margin-bottom: 20px;
        }
        .header-box h1 {
            color: #FFFFFF !important;
            font-size: 30px;
            margin: 0 0 8px 0;
        }
        .header-box p {
            color: #F1F5F9 !important;
            font-size: 17px;
            line-height: 1.5;
            margin: 0;
        }

        /* Área de upload de arquivo */
        [data-testid="stFileUploaderDropzone"] {
            background-color: #FFFFFF !important;
            border: 1.5px dashed #64748B !important;
            color: #0F172A !important;
        }
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] div {
            color: #0F172A !important;
        }

        /* Cartões e caixas informativas */
        .card-resumo {
            background-color: #FFFFFF !important;
            border-radius: 12px;
            padding: 18px 20px;
            border: 1px solid #CBD5E1;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05);
        }
        .card-titulo {
            font-size: 15px;
            font-weight: 700;
            color: #334155 !important;
            margin-bottom: 6px;
        }
        .card-valor {
            font-size: 24px;
            font-weight: 800;
            margin: 0;
        }
        .card-sub {
            font-size: 14px;
            color: #334155 !important;
            margin-top: 6px;
        }
        .privacidade-box {
            background-color: #EFF6FF !important;
            border-left: 4px solid #1E3A8A;
            padding: 12px 16px;
            border-radius: 8px;
            color: #0F172A !important;
            font-size: 15px;
            margin-bottom: 16px;
        }
        .escopo-box {
            background-color: #FFFBEB !important;
            border-left: 4px solid #D97706;
            padding: 12px 16px;
            border-radius: 8px;
            color: #0F172A !important;
            font-size: 15px;
            margin-bottom: 14px;
        }
        .jornada-dica-box {
            background-color: #E0F2FE !important;
            border-left: 4px solid #0284C7;
            padding: 10px 12px;
            border-radius: 8px;
            color: #0F172A !important;
            font-size: 14px;
            margin-top: 8px;
        }
        .legenda-box {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1;
            border-radius: 10px;
            padding: 12px 16px;
            margin-bottom: 12px;
            font-size: 15px;
            color: #0F172A !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 96 distritos oficiais do município de São Paulo com coordenadas aproximadas
DISTRITOS_SP = {
    "Água Rasa": (-23.5683, -46.5719),
    "Alto de Pinheiros": (-23.5494, -46.7097),
    "Anhanguera": (-23.4381, -46.7836),
    "Aricanduva": (-23.5700, -46.5064),
    "Artur Alvim": (-23.5403, -46.4858),
    "Barra Funda": (-23.5256, -46.6656),
    "Bela Vista": (-23.5614, -46.6464),
    "Belém": (-23.5425, -46.5906),
    "Bom Retiro": (-23.5289, -46.6353),
    "Brás": (-23.5450, -46.6158),
    "Brasilândia": (-23.4614, -46.6939),
    "Butantã": (-23.5719, -46.7081),
    "Cachoeirinha": (-23.4750, -46.6636),
    "Cambuci": (-23.5617, -46.6164),
    "Campo Belo": (-23.6233, -46.6697),
    "Campo Grande": (-23.6797, -46.6933),
    "Campo Limpo": (-23.6489, -46.7594),
    "Capão Redondo": (-23.6686, -46.7806),
    "Carrão": (-23.5469, -46.5397),
    "Casa Verde": (-23.5117, -46.6572),
    "Cidade Ademar": (-23.6758, -46.6553),
    "Cidade Dutra": (-23.7294, -46.6978),
    "Cidade Líder": (-23.5644, -46.4931),
    "Cidade Tiradentes": (-23.5917, -46.4042),
    "Consolação": (-23.5558, -46.6611),
    "Cursino": (-23.6283, -46.6197),
    "Ermelino Matarazzo": (-23.4956, -46.4817),
    "Freguesia do Ó": (-23.5008, -46.7008),
    "Grajaú": (-23.7764, -46.6889),
    "Guaianases": (-23.5439, -46.4125),
    "Iguatemi": (-23.5964, -46.4253),
    "Ipiranga": (-23.5914, -46.6064),
    "Itaim Bibi": (-23.5856, -46.6819),
    "Itaim Paulista": (-23.5017, -46.3983),
    "Itaquera": (-23.5414, -46.4733),
    "Jabaquara": (-23.6464, -46.6408),
    "Jaçanã": (-23.4678, -46.5789),
    "Jaguará": (-23.5122, -46.7486),
    "Jaguaré": (-23.5364, -46.7536),
    "Jaraguá": (-23.4556, -46.7358),
    "Jardim Ângela": (-23.6947, -46.7717),
    "Jardim Helena": (-23.4892, -46.4167),
    "Jardim Paulista": (-23.5689, -46.6689),
    "Jardim São Luís": (-23.6708, -46.7372),
    "José Bonifácio": (-23.5553, -46.4378),
    "Lapa": (-23.5275, -46.7036),
    "Liberdade": (-23.5583, -46.6353),
    "Limão": (-23.5072, -46.6789),
    "Mandaqui": (-23.4839, -46.6339),
    "Marsilac": (-23.9242, -46.6969),
    "Moema": (-23.5994, -46.6656),
    "Mooca": (-23.5558, -46.5978),
    "Morumbi": (-23.6000, -46.7200),
    "Parelheiros": (-23.8297, -46.7308),
    "Pari": (-23.5328, -46.6156),
    "Parque do Carmo": (-23.5667, -46.4625),
    "Pedreira": (-23.6939, -46.6431),
    "Penha": (-23.5289, -46.5419),
    "Perdizes": (-23.5361, -46.6736),
    "Perus": (-23.4067, -46.7539),
    "Pinheiros": (-23.5673, -46.7019),
    "Ponte Rasa": (-23.5161, -46.4947),
    "Raposo Tavares": (-23.5808, -46.7783),
    "República": (-23.5436, -46.6428),
    "Rio Pequeno": (-23.5681, -46.7556),
    "Sacomã": (-23.6019, -46.5961),
    "Santa Cecília": (-23.5356, -46.6517),
    "Santana": (-23.5025, -46.6247),
    "Santo Amaro": (-23.6549, -46.7102),
    "São Domingos": (-23.4956, -46.7433),
    "São Lucas": (-23.5881, -46.5397),
    "São Mateus": (-23.6075, -46.4756),
    "São Miguel": (-23.4958, -46.4419),
    "São Rafael": (-23.6272, -46.4539),
    "Sapopemba": (-23.6075, -46.5064),
    "Saúde": (-23.6147, -46.6383),
    "Sé": (-23.5505, -46.6339),
    "Tatuapé": (-23.5403, -46.5764),
    "Tremembé": (-23.4578, -46.6197),
    "Tucuruvi": (-23.4792, -46.6031),
    "Vila Andrade": (-23.6253, -46.7311),
    "Vila Curuçá": (-23.5131, -46.4161),
    "Vila Formosa": (-23.5656, -46.5442),
    "Vila Guilherme": (-23.5178, -46.6042),
    "Vila Jacuí": (-23.5019, -46.4556),
    "Vila Leopoldina": (-23.5308, -46.7317),
    "Vila Maria": (-23.5144, -46.5881),
    "Vila Mariana": (-23.5892, -46.6347),
    "Vila Matilde": (-23.5342, -46.5194),
    "Vila Medeiros": (-23.4889, -46.5889),
    "Vila Prudente": (-23.5819, -46.5800),
    "Vila Sônia": (-23.5978, -46.7367),
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
    """
    Valida se a imagem é segura e relacionada a rua/alagamento usando o Gemini.
    """
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return False, "Chave GEMINI_API_KEY não configurada nos Secrets do Streamlit."

    client = genai.Client(api_key=api_key)
    imagem = Image.open(io.BytesIO(foto_bytes))
    imagem.thumbnail((1024, 1024))

    prompt = (
        "Analise esta imagem enviada para um sistema público de alerta de alagamentos em São Paulo. "
        "Responda APENAS em JSON válido com duas chaves booleanas e uma string curta em português:\n"
        '{"segura": true/false, "relacionada_alagamento_ou_via": true/false, "motivo": "explicação curta"}\n'
        "Regras:\n"
        "- segura deve ser false se houver nudez, pornografia, conteúdo sexual, violência explícita ou ofensivo.\n"
        "- relacionada_alagamento_ou_via deve ser true APENAS se a foto mostrar rua, avenida, estação, calçada, chuva, poça, enchente ou trânsito afetado por água.\n"
        "- Se for selfie, meme, tela, animal ou foto interna sem relação com via/chuva/alagamento, relacionada_alagamento_ou_via deve ser false."
    )

    modelo_alvo = "gemini-3.8-flash"

    for tentativa in range(2):
        try:
            resposta = client.models.generate_content(
                model=modelo_alvo,
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
            erro_str = str(e)
            if "503" in erro_str or "UNAVAILABLE" in erro_str or "429" in erro_str:
                if tentativa == 0:
                    time.sleep(1.5)
                    continue
                return (
                    False,
                    f"O modelo {modelo_alvo} está com pico de demanda agora. Aguarde alguns segundos e tente de novo.",
                )
            return False, f"Erro ao chamar o modelo {modelo_alvo}: {erro_str}"  


@st.dialog("Alerta enviado com sucesso!")
def mostrar_popup_agradecimento(teve_foto_validada: bool):
    """Exibe popup de agradecimento após o envio do relato."""
    st.markdown("### Obrigado por ajudar outros trabalhadores!")
    st.write("Seu registro já foi adicionado ao painel para ajudar outras pessoas no trajeto em São Paulo.")
    if teve_foto_validada:
        st.success("📷 Sua foto foi validada pela IA e adicionada ao registro.")
    if st.button("Entendido", type="primary", use_container_width=True):
        st.rerun()


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

            if any(re.search(rf"\b{re.escape(termo)}\b", texto_norm) for termo in TERMOS_INTERIOR_EXCLUIR):
                continue

            tem_grande_sp = any(
                re.search(rf"\b{re.escape(mun)}\b", texto_norm) for mun in MUNICIPIOS_GRANDE_SP
            )
            if not tem_grande_sp and "sp" not in texto_norm.split():
                continue

            distrito_detectado = None
            for distrito in DISTRITOS_SP:
                distrito_norm = normalizar_texto(distrito)
                if re.search(rf"\b{re.escape(distrito_norm)}\b", texto_norm):
                    distrito_detectado = distrito
                    break

            if not distrito_detectado:
                distrito_detectado = "Sé"

            noticias.append(
                {
                    "titulo": titulo,
                    "link": link,
                    "fonte": fonte,
                    "distrito_detectado": distrito_detectado,
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
            "distrito": "Itaquera",
            "lat": -23.5414,
            "lon": -46.4733,
            "nivel": "Intransitável - Água alta",
            "horario": hora_atual,
            "descricao": "Av. José Pinheiro Borges, altura do nº 1200 — água acumulando perto da estação.",
            "foto": None,
            "secou_votos": 0,
        },
        {
            "id": 2,
            "usuario": "@ana_lapa",
            "distrito": "Lapa",
            "lat": -23.5275,
            "lon": -46.7036,
            "nivel": "Água na calçada",
            "horario": hora_atual,
            "descricao": "Rua Guaicurus, altura do nº 500 — calçada tomada pela água e trânsito parado.",
            "foto": None,
            "secou_votos": 0,
        },
    ]

if "abrir_popup_obrigado" not in st.session_state:
    st.session_state.abrir_popup_obrigado = False

if "ultimo_envio_teve_foto" not in st.session_state:
    st.session_state.ultimo_envio_teve_foto = False

if st.session_state.abrir_popup_obrigado:
    teve_foto_flag = st.session_state.ultimo_envio_teve_foto
    st.session_state.abrir_popup_obrigado = False
    st.session_state.ultimo_envio_teve_foto = False
    mostrar_popup_agradecimento(teve_foto_flag)

chuva_real_mm, temp_min, temp_max, clima_ok = buscar_chuva_real_sp()
noticias_sp = buscar_noticias_sp_e_grande_sp()

# Monta pinos de notícias reais (roxo)
pinos_noticias = []
for idx, n in enumerate(noticias_sp):
    distrito = n["distrito_detectado"]
    lat_b, lon_b = DISTRITOS_SP.get(distrito, DISTRITOS_SP["Sé"])
    desloc = ((idx % 5) - 2) * 0.0045
    pinos_noticias.append(
        {
            "tipo_label": "Notícia Real (SP/Grande SP)",
            "distrito": distrito,
            "lat": lat_b + desloc,
            "lon": lon_b - desloc,
            "resumo": f"{n['fonte']}: {n['titulo']}",
            "cor": [139, 92, 246, 230],
        }
    )

# Cabeçalho principal (Ajuste 2: descritivo mais assertivo baseado no PRD)
st.markdown(
    """
    <div class="header-box">
        <h1>🌧️ Alerta SP — Mobilidade Segura em Dias de Chuva</h1>
        <p>
            Desenvolvido para apoiar quem se locomove em dias úteis pela cidade de São Paulo e corre o risco de enfrentar
            bloqueios, atrasos e transtornos no trajeto <strong>casa ↔ trabalho</strong> por conta dos alagamentos urbanos.
            Acompanhe a previsão real de chuva, alertas da comunidade e pontos críticos antes de sair.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Barra lateral com os 96 distritos oficiais de SP
with st.sidebar:
    st.header("🧭 Seu Trajeto e Chuva")
    st.markdown(
        """
        <div class="escopo-box">
            🏙️ <strong>Escopo do mapa e distritos:</strong> Esta função de distritos e alertas de trajeto está disponível <strong>apenas para o município de São Paulo (capital)</strong>, e não para os demais municípios da Grande SP.
        </div>
        """,
        unsafe_allow_html=True,
    )

    lista_distritos = sorted(DISTRITOS_SP.keys())
    idx_moradia = lista_distritos.index("Itaquera") if "Itaquera" in lista_distritos else 0
    idx_trabalho = lista_distritos.index("Sé") if "Sé" in lista_distritos else 0

    distrito_moradia = st.selectbox("Distrito onde você mora (SP Capital)", options=lista_distritos, index=idx_moradia)
    distrito_trabalho = st.selectbox("Distrito onde você trabalha (SP Capital)", options=lista_distritos, index=idx_trabalho)

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
        # Ajuste 3: orienta o usuário a olhar o resultado na página principal
        st.markdown(
            """
            <div class="jornada-dica-box">
                👉 <strong>Veja o resultado na tela principal:</strong> o impacto dessa simulação no seu trajeto aparece atualizado no cartão <strong>"🚦 Nível de Risco no Trajeto"</strong> no topo do painel à direita.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        chuva_ativa_mm = chuva_real_mm

    if st.button("🔄 Atualizar dados reais agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Verifica pontos ativos nos distritos selecionados
distritos_trajeto = {distrito_moradia, distrito_trabalho}
pontos_usuario_trajeto = [
    item for item in st.session_state.ocorrencias_usuarios if item["distrito"] in distritos_trajeto
]
noticias_no_trajeto = [
    item for item in pinos_noticias if item["distrito"] in distritos_trajeto
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
    distritos_afetados = sorted(
        {p["distrito"] for p in pontos_usuario_trajeto} | {n["distrito"] for n in noticias_no_trajeto}
    )
    st.error(
        f"⚠️ **Atenção no seu trajeto ({distrito_moradia} ↔ {distrito_trabalho}):** "
        f"Há registro ou notícia envolvendo **{', '.join(distritos_afetados)}**. "
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
            <div class="card-sub">{distrito_moradia} ↔ {distrito_trabalho} • {risco_aviso}</div>
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

# 1. MAPA (Focado no município de SP)
st.markdown("### 🗺️ Mapa de Alagamentos e Notícias — Município de São Paulo")
st.caption("Filtro de distritos e alertas de trajeto válidos exclusivamente para a cidade de São Paulo (capital).")

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
            "distrito": item["distrito"],
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
            "distrito": pino["distrito"],
            "tipo_label": pino["tipo_label"],
            "resumo": pino["resumo"],
            "cor": pino["cor"],
        }
    )

df_mapa = pd.DataFrame(dados_mapa)
lat_foco, lon_foco = DISTRITOS_SP.get(distrito_moradia, (-23.5505, -46.6339))

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
    min_zoom=10.3,
    max_zoom=15.0,
    pitch=0,
)

tooltip = {
    "html": "<b>{tipo_label}</b><br/><b>Distrito (SP):</b> {distrito}<br/>{resumo}",
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

# 2. REPORT DE USUÁRIOS LOGO ABAIXO DO MAPA
st.divider()
st.markdown("### 🚨 Reportar Novo Alagamento (Município de São Paulo)")

st.markdown(
    """
    <div class="escopo-box">
        🏙️ <strong>Atenção:</strong> O registro por distrito neste formulário está disponível <strong>apenas para o município de São Paulo (capital)</strong> — não abrange os demais municípios da Grande SP.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="privacidade-box">
        🔒 <strong>Privacidade e Segurança:</strong> Usamos apenas o seu apelido público (<code>@username</code>) e a referência da via alagada.
        Não pedimos CPF nem o seu endereço pessoal. Fotos enviadas passam por <strong>verificação automática por IA</strong> para garantir que sejam registros reais de ruas ou alagamentos.
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
        distrito_escolhido = st.selectbox(
            "Distrito do alagamento (apenas SP Capital) *",
            options=lista_distritos,
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

    # Ajuste 6: orienta a indicar rua e número aproximado do ponto alagado
    descricao_curta = st.text_area(
        "Rua, altura do número e detalhes do ponto alagado (até 140 caracteres)",
        max_chars=140,
        placeholder="Ex.: Rua Alvarenga, altura do número 1000 — perto do ponto de ônibus, água subindo rápido.",
        help="Como os distritos de SP são grandes, indique a rua e um número de referência próximo ao alagamento.",
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

                lat_distrito, lon_distrito = DISTRITOS_SP[distrito_escolhido]
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
                    "distrito": distrito_escolhido,
                    "lat": lat_distrito + deslocamento,
                    "lon": lon_distrito - deslocamento,
                    "nivel": nivel_escolhido,
                    "horario": hora_registro,
                    "descricao": texto_descricao,
                    "foto": foto_bytes,
                    "secou_votos": 0,
                }

                st.session_state.ocorrencias_usuarios.append(nova_ocorrencia)
                st.session_state.ultimo_envio_teve_foto = foto_bytes is not None
                st.session_state.abrir_popup_obrigado = True
                st.rerun()

# 3. NOTÍCIAS REAIS APÓS O FORMULÁRIO DE REPORT
st.divider()
st.markdown("### 📰 Notícias Reais — São Paulo e Grande SP")
st.write("Manchetes recentes da imprensa local focadas na capital e região metropolitana (sem cidades do interior). Passe o mouse nos pontos roxos no mapa para ver os detalhes.")

if not noticias_sp:
    st.info("Nenhuma manchete recente encontrada agora para SP/Grande SP. Clique em 'Atualizar dados reais agora' na barra lateral.")
else:
    for n in noticias_sp:
        with st.container(border=True):
            st.markdown(f"**{n['titulo']}**")
            st.caption(f"Fonte: {n['fonte']} • 📍 Distrito de referência no mapa: **{n['distrito_detectado']}**")
            if n["link"]:
                st.markdown(f"[Abrir notícia]({n['link']})")

# 4. LISTA DE OCORRÊNCIAS DA COMUNIDADE E VALIDAÇÃO
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
                destaque_trajeto = " • 🧭 **No seu trajeto**" if item["distrito"] in distritos_trajeto else ""
                tem_foto_tag = "📷 Com foto verificada" if item.get("foto") is not None else "📝 Sem foto"
                st.markdown(f"**📍 {item['distrito']} (SP)** — *{item['nivel']}* • {tem_foto_tag}{destaque_trajeto}")
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
