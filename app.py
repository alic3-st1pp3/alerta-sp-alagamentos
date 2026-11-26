import datetime
import email.utils
import io
import json
import math
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

        /* Correção definitiva de contraste nos botões primários e de envio */
        button[kind="primary"],
        button[data-testid="baseButton-primary"],
        [data-testid="stFormSubmitButton"] button,
        section[data-testid="stSidebar"] button[kind="primary"] {
            background-color: #1E3A8A !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 700 !important;
        }

        button[kind="primary"] p,
        button[kind="primary"] span,
        button[data-testid="baseButton-primary"] p,
        button[data-testid="baseButton-primary"] span,
        [data-testid="stFormSubmitButton"] button p,
        [data-testid="stFormSubmitButton"] button span,
        section[data-testid="stSidebar"] button[kind="primary"] p,
        section[data-testid="stSidebar"] button[kind="primary"] span {
            color: #FFFFFF !important;
        }

        button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            background-color: #1D4ED8 !important;
            color: #FFFFFF !important;
        }

        /* Botões secundários */
        button[kind="secondary"],
        button[data-testid="baseButton-secondary"] {
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1.5px solid #94A3B8 !important;
            font-weight: 600 !important;
        }

        button[kind="secondary"] p,
        button[kind="secondary"] span,
        button[data-testid="baseButton-secondary"] p,
        button[data-testid="baseButton-secondary"] span {
            color: #0F172A !important;
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
        .jornada-dica-box {
            background-color: #E0F2FE !important;
            border-left: 4px solid #0284C7;
            padding: 10px 12px;
            border-radius: 8px;
            color: #0F172A !important;
            font-size: 14px;
            margin-top: 8px;
        }
        .foco-mapa-box {
            background-color: #ECFDF5 !important;
            border: 1.5px solid #10B981;
            border-left: 5px solid #059669;
            padding: 12px 16px;
            border-radius: 10px;
            color: #064E3B !important;
            font-size: 15px;
            margin-bottom: 12px;
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

# Municípios da Região Metropolitana de São Paulo (Grande SP) com coordenadas centrais
MUNICIPIOS_GSP_COORDS = {
    "São Paulo": (-23.5505, -46.6339),
    "Arujá": (-23.3964, -46.3211),
    "Barueri": (-23.5114, -46.8761),
    "Biritiba Mirim": (-23.5731, -46.0389),
    "Caieiras": (-23.3644, -46.7408),
    "Cajamar": (-23.3561, -46.8769),
    "Carapicuíba": (-23.5236, -46.8408),
    "Cotia": (-23.6039, -46.9189),
    "Diadema": (-23.6861, -46.6228),
    "Embu das Artes": (-23.6489, -46.8522),
    "Embu-Guaçu": (-23.8322, -46.8114),
    "Ferraz de Vasconcelos": (-23.5411, -46.3689),
    "Francisco Morato": (-23.2817, -46.7425),
    "Franco da Rocha": (-23.3286, -46.7244),
    "Guararema": (-23.4150, -46.0350),
    "Guarulhos": (-23.4542, -46.5333),
    "Itapecerica da Serra": (-23.7172, -46.8492),
    "Itapevi": (-23.5489, -46.9342),
    "Itaquaquecetuba": (-23.4864, -46.3486),
    "Jandira": (-23.5278, -46.9025),
    "Juquitiba": (-23.9317, -47.0681),
    "Mairiporã": (-23.3189, -46.5867),
    "Mauá": (-23.6678, -46.4614),
    "Mogi das Cruzes": (-23.5228, -46.1883),
    "Osasco": (-23.5325, -46.7917),
    "Pirapora do Bom Jesus": (-23.3972, -47.0028),
    "Poá": (-23.5286, -46.3450),
    "Ribeirão Pires": (-23.7111, -46.4133),
    "Rio Grande da Serra": (-23.7442, -46.3981),
    "Salesópolis": (-23.5322, -45.8464),
    "Santa Isabel": (-23.3156, -46.2214),
    "Santana de Parnaíba": (-23.4439, -46.9178),
    "Santo André": (-23.6639, -46.5383),
    "São Bernardo do Campo": (-23.6939, -46.5650),
    "São Caetano do Sul": (-23.6231, -46.5511),
    "São Lourenço da Serra": (-23.8533, -46.9433),
    "Suzano": (-23.5425, -46.3108),
    "Taboão da Serra": (-23.6019, -46.7528),
    "Vargem Grande Paulista": (-23.6028, -47.0264),
}

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


def criar_icone_pin_svg(cor_hex: str) -> dict:
    """Gera um ícone SVG em formato de PIN (gota com ponta inferior) para o PyDeck IconLayer."""
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
        <path d="M32 4C18.7 4 8 14.7 8 28c0 16.5 24 32 24 32s24-15.5 24-32C56 14.7 45.3 4 32 4z"
              fill="{cor_hex}" stroke="#FFFFFF" stroke-width="3.5"/>
        <circle cx="32" cy="26" r="9.5" fill="#FFFFFF"/>
    </svg>
    """.strip()
    url_svg = "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg)
    return {
        "url": url_svg,
        "width": 64,
        "height": 64,
        "anchorY": 60,
        "anchorX": 32,
    }


ICONES_PIN = {
    "com_foto": criar_icone_pin_svg("#DC2626"),   # Vermelho
    "sem_foto": criar_icone_pin_svg("#F97316"),   # Laranja
    "noticia": criar_icone_pin_svg("#7C3AED"),    # Roxo
    "trajeto": criar_icone_pin_svg("#059669"),    # Verde (referência casa/trabalho)
}


def normalizar_texto(texto: str) -> str:
    mapa_acentos = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return texto.translate(mapa_acentos).lower()


def formatar_data_noticia(entry: dict) -> str:
    """Extrai e formata a data/hora de publicação de uma notícia do feed RSS para horário de SP."""
    fuso_sp = datetime.timezone(datetime.timedelta(hours=-3))
    try:
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed and len(parsed) >= 6:
            dt_utc = datetime.datetime(*parsed[:6], tzinfo=datetime.timezone.utc)
            dt_sp = dt_utc.astimezone(fuso_sp)
            return dt_sp.strftime("%d/%m/%Y às %H:%M")

        texto_data = entry.get("published") or entry.get("updated") or ""
        if texto_data:
            dt_parsed = email.utils.parsedate_to_datetime(texto_data)
            if dt_parsed.tzinfo is None:
                dt_parsed = dt_parsed.replace(tzinfo=datetime.timezone.utc)
            dt_sp = dt_parsed.astimezone(fuso_sp)
            return dt_sp.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        pass

    return "Data não informada"


@st.cache_data(ttl=86400)
def geocodificar_endereco_gsp(endereco: str, municipio: str):
    """
    Converte um endereço real na Grande São Paulo em coordenadas (lat, lon)
    usando o Nominatim (OpenStreetMap). Retorna (lat, lon, endereco_encontrado, exato).
    """
    lat_padrao, lon_padrao = MUNICIPIOS_GSP_COORDS.get(municipio, (-23.5505, -46.6339))
    endereco_limpo = (endereco or "").strip()

    if not endereco_limpo:
        return lat_padrao, lon_padrao, municipio, False

    consultas = [
        f"{endereco_limpo}, {municipio}, São Paulo, Brasil",
        f"{endereco_limpo}, Região Metropolitana de São Paulo, Brasil",
    ]

    headers = {"User-Agent": "AlertaSP-MobilidadeUrbana/1.0"}

    for q in consultas:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": q,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "br",
                    "viewbox": "-47.20,-23.15,-45.75,-24.05",
                    "bounded": 1,
                },
                headers=headers,
                timeout=5,
            )
            resp.raise_for_status()
            resultados = resp.json()
            if resultados:
                lat = float(resultados[0]["lat"])
                lon = float(resultados[0]["lon"])
                nome_exibido = resultados[0].get("display_name", f"{endereco_limpo} — {municipio}")
                return lat, lon, nome_exibido, True
        except Exception:
            continue

    return lat_padrao, lon_padrao, f"{endereco_limpo} ({municipio})", False


def calcular_enquadramento_pontos(ponto_a: tuple, ponto_b: tuple):
    """Calcula centro geográfico e zoom ideal para visualizar dois pontos no mapa."""
    lat_a, lon_a = ponto_a
    lat_b, lon_b = ponto_b

    lat_centro = (lat_a + lat_b) / 2
    lon_centro = (lon_a + lon_b) / 2

    distancia_graus = math.hypot(lat_a - lat_b, lon_a - lon_b)
    if distancia_graus < 0.005:
        zoom = 14.2
    elif distancia_graus < 0.025:
        zoom = 13.0
    elif distancia_graus < 0.08:
        zoom = 11.9
    elif distancia_graus < 0.18:
        zoom = 11.0
    else:
        zoom = 10.2

    return lat_centro, lon_centro, zoom


def validar_imagem_com_ia(foto_bytes: bytes):
    """Valida se a imagem é segura e relacionada a rua/alagamento usando o Gemini."""
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return False, "Chave GEMINI_API_KEY não configurada nos Secrets do Streamlit."

    client = genai.Client(api_key=api_key)
    imagem = Image.open(io.BytesIO(foto_bytes))
    imagem.thumbnail((1024, 1024))

    prompt = (
        "Analise esta imagem enviada para um sistema público de alerta de alagamentos na Grande São Paulo. "
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
def mostrar_popup_agradecimento(teve_foto_validada: bool, endereco_salvo: str):
    """Exibe popup de agradecimento após o envio do relato."""
    st.markdown("### Obrigado por ajudar outros trabalhadores!")
    st.write(f"Seu registro em **{endereco_salvo}** já foi marcado no mapa para orientar outros deslocamentos na Grande SP.")
    if teve_foto_validada:
        st.success("📷 Sua foto foi validada pela IA e adicionada ao registro.")
    if st.button("Entendido", type="primary", use_container_width=True):
        st.rerun()


@st.cache_data(ttl=1800)
def buscar_chuva_real_gsp():
    """Busca previsão real de precipitação (mm) e temperatura para a Grande São Paulo via Open-Meteo."""
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
    excluindo manchetes voltadas a cidades do interior paulista e incluindo data formatada.
    """
    query = urllib.parse.quote(
        '(alagamento OR enchente OR "chuva forte") ("São Paulo" OR "Grande SP" OR Guarulhos OR Osasco OR ABC)'
    )
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    noticias = []

    try:
        feed = feedparser.parse(url)
        entries = getattr(feed, "entries", []) or []
        for entry in entries[:20]:
            try:
                titulo = str(entry.get("title") or "Notícia sem título")
                link = str(entry.get("link") or "")
                fonte_obj = entry.get("source")
                if isinstance(fonte_obj, dict):
                    fonte = str(fonte_obj.get("title") or "Imprensa local")
                else:
                    fonte = str(getattr(fonte_obj, "title", None) or "Imprensa local")

                data_formatada = formatar_data_noticia(entry)
                texto_norm = normalizar_texto(f"{titulo} {fonte}")

                if any(re.search(rf"\b{re.escape(termo)}\b", texto_norm) for termo in TERMOS_INTERIOR_EXCLUIR):
                    continue

                municipio_detectado = None
                for mun in MUNICIPIOS_GSP_COORDS:
                    mun_norm = normalizar_texto(mun)
                    if re.search(rf"\b{re.escape(mun_norm)}\b", texto_norm):
                        municipio_detectado = mun
                        break

                if not municipio_detectado:
                    if "abc" in texto_norm.split():
                        municipio_detectado = "Santo André"
                    elif "sp" in texto_norm.split() or "grande sp" in texto_norm:
                        municipio_detectado = "São Paulo"
                    else:
                        continue

                noticias.append(
                    {
                        "titulo": titulo,
                        "link": link,
                        "fonte": fonte,
                        "data_publicacao": data_formatada,
                        "municipio_detectado": municipio_detectado,
                    }
                )
            except Exception:
                continue
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
            "municipio": "São Paulo",
            "endereco": "Av. José Pinheiro Borges, 1200 — Itaquera",
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
            "usuario": "@marcos_osasco",
            "municipio": "Osasco",
            "endereco": "Av. dos Autonomistas, 2500 — Centro",
            "lat": -23.5325,
            "lon": -46.7917,
            "nivel": "Água na calçada",
            "horario": hora_atual,
            "descricao": "Faixa da direita tomada pela água e trânsito parado.",
            "foto": None,
            "secou_votos": 0,
        },
    ]

if "abrir_popup_obrigado" not in st.session_state:
    st.session_state.abrir_popup_obrigado = False

if "ultimo_envio_teve_foto" not in st.session_state:
    st.session_state.ultimo_envio_teve_foto = False

if "ultimo_endereco_salvo" not in st.session_state:
    st.session_state.ultimo_endereco_salvo = ""

if "foco_trajeto_ativo" not in st.session_state:
    st.session_state.foco_trajeto_ativo = False

if "mapa_render_id" not in st.session_state:
    st.session_state.mapa_render_id = 0

if st.session_state.abrir_popup_obrigado:
    teve_foto_flag = st.session_state.ultimo_envio_teve_foto
    end_flag = st.session_state.ultimo_endereco_salvo
    st.session_state.abrir_popup_obrigado = False
    st.session_state.ultimo_envio_teve_foto = False
    st.session_state.ultimo_endereco_salvo = ""
    mostrar_popup_agradecimento(teve_foto_flag, end_flag)

chuva_real_mm, temp_min, temp_max, clima_ok = buscar_chuva_real_gsp()
noticias_sp = buscar_noticias_sp_e_grande_sp()

# Monta pinos de notícias reais (roxo)
pinos_noticias = []
for idx, n in enumerate(noticias_sp):
    mun = n["municipio_detectado"]
    lat_b, lon_b = MUNICIPIOS_GSP_COORDS.get(mun, (-23.5505, -46.6339))
    desloc = ((idx % 5) - 2) * 0.0045
    pinos_noticias.append(
        {
            "tipo_label": "Notícia Real (Grande SP)",
            "local_titulo": mun,
            "lat": lat_b + desloc,
            "lon": lon_b - desloc,
            "resumo": f"{n['fonte']} ({n['data_publicacao']}): {n['titulo']}",
            "icone": ICONES_PIN["noticia"],
            "tamanho": 44,
        }
    )

# Cabeçalho principal
st.markdown(
    """
    <div class="header-box">
        <h1>🌧️ Alerta SP — Mobilidade Segura em Dias de Chuva</h1>
        <p>
            Desenvolvido para apoiar quem se locomove em dias úteis pela <strong>Região Metropolitana de São Paulo</strong>
            e corre o risco de enfrentar bloqueios, atrasos e transtornos no trajeto <strong>casa ↔ trabalho</strong> por conta dos alagamentos.
            Mapeie endereços reais, acompanhe a chuva e confira os pontos críticos antes de sair.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Barra lateral com consulta de trajeto por endereço na Grande SP
with st.sidebar:
    st.header("🧭 Consultar Trajeto no Mapa")
    st.caption("Informe os endereços ou regiões do seu deslocamento na Grande São Paulo.")

    lista_municipios = sorted(MUNICIPIOS_GSP_COORDS.keys())
    idx_sp = lista_municipios.index("São Paulo") if "São Paulo" in lista_municipios else 0

    mun_origem = st.selectbox("Município de partida", options=lista_municipios, index=idx_sp)
    end_origem = st.text_input(
        "Endereço ou bairro de partida",
        placeholder="Ex.: Av. Paulista, 1000 ou Itaquera",
    )

    mun_destino = st.selectbox("Município de destino", options=lista_municipios, index=idx_sp)
    end_destino = st.text_input(
        "Endereço ou bairro de destino",
        placeholder="Ex.: Av. Faria Lima, 2000 ou Centro",
    )

    if st.button("📍 Ver no mapa", type="primary", use_container_width=True):
        st.session_state.foco_trajeto_ativo = True
        st.session_state.mapa_render_id += 1
        st.rerun()

    st.divider()
    st.subheader("🌦️ Clima Real (Grande SP)")
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
        st.markdown(
            """
            <div class="jornada-dica-box">
                👉 <strong>Veja o resultado na tela principal:</strong> o nível de risco atualizado aparece no cartão <strong>"🚦 Condição Geral pela Chuva"</strong> no topo do painel à direita.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        chuva_ativa_mm = chuva_real_mm

    if st.button("🔄 Atualizar dados reais agora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Coordenadas centrais dos municípios selecionados (evita chamada de rede a cada rerun)
lat_orig, lon_orig = MUNICIPIOS_GSP_COORDS.get(mun_origem, (-23.5505, -46.6339))
lat_dest, lon_dest = MUNICIPIOS_GSP_COORDS.get(mun_destino, (-23.5505, -46.6339))
desc_orig = f"{end_origem.strip()} — {mun_origem}" if end_origem.strip() else mun_origem
desc_dest = f"{end_destino.strip()} — {mun_destino}" if end_destino.strip() else mun_destino

if st.session_state.foco_trajeto_ativo:
    lat_orig, lon_orig, desc_orig, _ = geocodificar_endereco_gsp(end_origem, mun_origem)
    lat_dest, lon_dest, desc_dest, _ = geocodificar_endereco_gsp(end_destino, mun_destino)

if chuva_ativa_mm < 10:
    risco_texto = "Risco Baixo"
    risco_cor = "#059669"
    risco_aviso = "Chuva fraca; menor chance de bloqueios."
elif chuva_ativa_mm <= 30:
    risco_texto = "Risco Moderado"
    risco_cor = "#D97706"
    risco_aviso = "Atenção: chance de poças e lentidão."
else:
    risco_texto = "Risco Alto"
    risco_cor = "#DC2626"
    risco_aviso = "Alerta: chuva forte com alto risco de alagamento."

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
            <div class="card-titulo">🚦 Condição Geral pela Chuva</div>
            <p class="card-valor" style="color: {risco_cor};">{risco_texto}</p>
            <div class="card-sub">{risco_aviso}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="card-resumo">
            <div class="card-titulo">📍 Picos Mapeados (Grande SP)</div>
            <p class="card-valor" style="color: #DC2626;">{total_pinos}</p>
            <div class="card-sub">{len(st.session_state.ocorrencias_usuarios)} da comunidade • {len(pinos_noticias)} de notícias</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 1. MAPA COM PINs REAIS EM ENDEREÇOS DA GRANDE SP
st.markdown("### 🗺️ Mapa de Picos de Alagamento — Grande São Paulo")
st.caption("Visualize os pontos exatos reportados pela comunidade em endereços reais de toda a Região Metropolitana de São Paulo.")

if st.session_state.foco_trajeto_ativo:
    label_orig = end_origem.strip() if end_origem.strip() else mun_origem
    label_dest = end_destino.strip() if end_destino.strip() else mun_destino
    st.markdown(
        f"""
        <div class="foco-mapa-box">
            📍 <strong>Mapa centralizado na sua consulta:</strong> Enquadrando <strong>{label_orig} ({mun_origem})</strong> e <strong>{label_dest} ({mun_destino})</strong> — marcados com PINs verdes no mapa.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="legenda-box">
        <strong>Legenda dos PINs:</strong> &nbsp;&nbsp;
        📍🔴 <strong>Vermelho:</strong> Comunidade <strong>com foto</strong> &nbsp;&nbsp;|&nbsp;&nbsp;
        📍🟠 <strong>Laranja:</strong> Comunidade <strong>sem foto</strong> &nbsp;&nbsp;|&nbsp;&nbsp;
        📍🟣 <strong>Roxo:</strong> Notícia real (Grande SP) &nbsp;&nbsp;|&nbsp;&nbsp;
        📍🟢 <strong>Verde:</strong> Pontos consultados (Partida / Destino)
    </div>
    """,
    unsafe_allow_html=True,
)

dados_mapa = []

dados_mapa.append(
    {
        "lat": lat_orig + 0.0008,
        "lon": lon_orig + 0.0008,
        "local_titulo": f"{end_origem.strip() or mun_origem} ({mun_origem})",
        "tipo_label": "🏠 Ponto de Partida Consultado",
        "resumo": desc_orig,
        "icone": ICONES_PIN["trajeto"],
        "tamanho": 44,
    }
)

if (mun_destino != mun_origem) or (end_destino.strip() and end_destino.strip() != end_origem.strip()):
    dados_mapa.append(
        {
            "lat": lat_dest + 0.0008,
            "lon": lon_dest + 0.0008,
            "local_titulo": f"{end_destino.strip() or mun_destino} ({mun_destino})",
            "tipo_label": "💼 Ponto de Destino Consultado",
            "resumo": desc_dest,
            "icone": ICONES_PIN["trajeto"],
            "tamanho": 44,
        }
    )

for item in st.session_state.ocorrencias_usuarios:
    tem_foto = item.get("foto") is not None
    dados_mapa.append(
        {
            "lat": item["lat"],
            "lon": item["lon"],
            "local_titulo": f"{item['endereco']} ({item['municipio']})",
            "tipo_label": "Comunidade (com foto)" if tem_foto else "Comunidade (sem foto)",
            "resumo": f"{item['nivel']} — {item['descricao']} ({item['usuario']})",
            "icone": ICONES_PIN["com_foto"] if tem_foto else ICONES_PIN["sem_foto"],
            "tamanho": 48,
        }
    )

for pino in pinos_noticias:
    dados_mapa.append(
        {
            "lat": pino["lat"],
            "lon": pino["lon"],
            "local_titulo": pino["local_titulo"],
            "tipo_label": pino["tipo_label"],
            "resumo": pino["resumo"],
            "icone": pino["icone"],
            "tamanho": pino["tamanho"],
        }
    )

df_mapa = pd.DataFrame(dados_mapa)

lat_foco, lon_foco, zoom_foco = calcular_enquadramento_pontos(
    (lat_orig, lon_orig),
    (lat_dest, lon_dest),
)

layer_pins = pdk.Layer(
    "IconLayer",
    data=df_mapa,
    get_icon="icone",
    get_position="[lon, lat]",
    get_size="tamanho",
    size_scale=1,
    pickable=True,
    auto_highlight=True,
)

view_state = pdk.ViewState(
    latitude=lat_foco,
    longitude=lon_foco,
    zoom=zoom_foco,
    min_zoom=9.5,
    max_zoom=17.0,
    pitch=0,
)

tooltip = {
    "html": "<b>{tipo_label}</b><br/><b>Local:</b> {local_titulo}<br/>{resumo}",
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
        layers=[layer_pins],
        tooltip=tooltip,
    ),
    use_container_width=True,
    height=490,
    key=f"mapa_gsp_{st.session_state.mapa_render_id}_{mun_origem}_{end_origem}_{mun_destino}_{end_destino}",
)

# 2. REPORT DE USUÁRIOS LOGO ABAIXO DO MAPA (COM ENDEREÇO REAL EM QUALQUER MUNICÍPIO DA GRANDE SP)
st.divider()
st.markdown("### 🚨 Reportar Novo Pico de Alagamento (Grande São Paulo)")

st.markdown(
    """
    <div class="privacidade-box">
        🔒 <strong>Privacidade e Precisão:</strong> Usamos apenas o seu apelido público (<code>@username</code>) e o endereço da via alagada em qualquer município da Grande SP.
        Não pedimos CPF nem o seu endereço pessoal. Fotos enviadas passam por <strong>verificação automática por IA</strong>.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("form_reportar_alagamento", clear_on_submit=True):
    col_form1, col_form2 = st.columns(2)

    with col_form1:
        apelido_input = st.text_input(
            "Apelido público (@username) *",
            placeholder="Ex.: @maria_zl ou joao_abc",
        )
        municipio_escolhido = st.selectbox(
            "Município (Grande SP) *",
            options=lista_municipios,
            index=idx_sp,
        )
        endereco_input = st.text_input(
            "Endereço do alagamento (Rua e número aproximado) *",
            placeholder="Ex.: Rua Alvarenga, 1000 — Butantã",
            help="Informe o nome da rua/avenida e altura do número para posicionarmos o PIN exatamente no ponto alagado.",
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
            "Detalhes adicionais do local (até 140 caracteres)",
            max_chars=140,
            placeholder="Ex.: Perto do ponto de ônibus, água subindo rápido nas duas faixas.",
        )

    enviado = st.form_submit_button("Enviar Alerta", type="primary", use_container_width=True)

    if enviado:
        apelido_limpo = (apelido_input or "").strip()
        endereco_limpo = (endereco_input or "").strip()

        if not apelido_limpo:
            st.error("Por favor, preencha o seu apelido público (@username) antes de enviar o alerta.")
        elif not endereco_limpo:
            st.error("Por favor, informe o endereço aproximado (rua e número) do ponto de alagamento.")
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

                with st.spinner("📍 Localizando endereço no mapa da Grande SP..."):
                    lat_ponto, lon_ponto, _, endereco_exato = geocodificar_endereco_gsp(
                        endereco_limpo, municipio_escolhido
                    )

                if not endereco_exato:
                    deslocamento = (len(st.session_state.ocorrencias_usuarios) % 5) * 0.0022
                    lat_ponto += deslocamento
                    lon_ponto -= deslocamento

                novo_id = max([o["id"] for o in st.session_state.ocorrencias_usuarios], default=0) + 1
                hora_registro = datetime.datetime.now().strftime("%H:%M")

                texto_descricao = (
                    (descricao_curta or "").strip()
                    or "Ponto de alagamento informado pela comunidade."
                )

                nova_ocorrencia = {
                    "id": novo_id,
                    "usuario": apelido_limpo,
                    "municipio": municipio_escolhido,
                    "endereco": endereco_limpo,
                    "lat": lat_ponto,
                    "lon": lon_ponto,
                    "nivel": nivel_escolhido,
                    "horario": hora_registro,
                    "descricao": texto_descricao,
                    "foto": foto_bytes,
                    "secou_votos": 0,
                }

                st.session_state.ocorrencias_usuarios.append(nova_ocorrencia)
                st.session_state.ultimo_envio_teve_foto = foto_bytes is not None
                st.session_state.ultimo_endereco_salvo = f"{endereco_limpo} ({municipio_escolhido})"
                st.session_state.abrir_popup_obrigado = True
                st.rerun()

# 3. NOTÍCIAS REAIS APÓS O FORMULÁRIO DE REPORT (COM DATA DA NOTÍCIA)
st.divider()
st.markdown("### 📰 Notícias Reais — São Paulo e Grande SP")
st.write("Manchetes recentes da imprensa local focadas na capital e região metropolitana (sem cidades do interior). Passe o mouse nos PINs roxos no mapa para ver os detalhes.")

if not noticias_sp:
    st.info("Nenhuma manchete recente encontrada agora para SP/Grande SP. Clique em 'Atualizar dados reais agora' na barra lateral.")
else:
    for n in noticias_sp:
        with st.container(border=True):
            st.markdown(f"**{n['titulo']}**")
            st.caption(
                f"🗓️ Publicada em: **{n['data_publicacao']}** • "
                f"Fonte: {n['fonte']} • "
                f"📍 Município de referência: **{n['municipio_detectado']}**"
            )
            if n["link"]:
                st.markdown(f"[Abrir notícia]({n['link']})")

# 4. LISTA DE OCORRÊNCIAS DA COMUNIDADE E VALIDAÇÃO
st.divider()
st.markdown("### 📋 Picos Reportados pela Comunidade e Validação")
st.write("A água baixou por aí? Clique em **Já secou**. Com **3 confirmações**, o registro sai do mapa.")

if not st.session_state.ocorrencias_usuarios:
    st.info("Não há relatos de usuários ativos no momento.")
else:
    ocorrencia_para_remover = None

    for item in st.session_state.ocorrencias_usuarios:
        with st.container(border=True):
            c_info, c_foto, c_acao = st.columns([4, 2, 2])

            with c_info:
                tem_foto_tag = "📷 Com foto verificada" if item.get("foto") is not None else "📝 Sem foto"
                st.markdown(f"**📍 {item['endereco']} ({item['municipio']})** — *{item['nivel']}* • {tem_foto_tag}")
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
