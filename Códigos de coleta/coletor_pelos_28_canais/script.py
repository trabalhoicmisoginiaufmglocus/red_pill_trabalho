import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import time

# Conexão com a API informando o status
from scripts.scriptAPI import connectCheckAPI
from scripts.globalState import GlobalState
from scripts.secondsUntil import secondsUntil
from scripts.console import log

from config import config

import os
import csv
import time
import requests
import json
import random

# Configuração do timeout
import socket

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound

# timeout_in_sec = 15
timeout_in_sec = 60*3 # 3 minutes timeout limit
socket.setdefaulttimeout(timeout_in_sec)

def get_transcription(id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(id, languages=['pt'])  # Ajuste idiomas, se necessário
        transcription_text = " ".join([entry['text'] for entry in transcript])
        return transcription_text
    except NoTranscriptFound:
        transcript = YouTubeTranscriptApi.get_transcript(id, languages=['en'])  # Ajuste idiomas, se necessário
        transcription_text = " ".join([entry['text'] for entry in transcript])
        return transcription_text
    except Exception:
        return None
    
class YouTubeAPIManager:
    YOUTUBE_API_SERVICE_NAME = 'youtube'
    YOUTUBE_API_VERSION = 'v3'
    DEVELOPER_KEYS = config["youtube_keys"]

    static_YouTubeAPIManager = None

    def __init__(self):
        self.current_key_index = -1
        self.daily_quota = 10_000  # ou outro valor desejado por chave
        self.daily_cost = 0
        self.last_reset = datetime.now().date()
        self.youtube = self.get_new_youtube_client()

    @staticmethod
    def get_instance() -> "YouTubeAPIManager":
        if YouTubeAPIManager.static_YouTubeAPIManager is None:
            YouTubeAPIManager.static_YouTubeAPIManager = YouTubeAPIManager()
        return YouTubeAPIManager.static_YouTubeAPIManager

    def get_new_youtube_client(self):
        self.DEVELOPER_KEYS = config['youtube_keys']
        if self.current_key_index >= len(self.DEVELOPER_KEYS) - 1:
            timeout = 60 * 60 * 2  # 2 horas
            log("key", f"Todas as chaves excederam a quota. Aguardando {timeout} segundos.")
            GlobalState.get_instance().set_state("status", "sleeping")
            time.sleep(timeout)
            GlobalState.get_instance().set_state("status", "working")
            self.current_key_index = 0
            self.daily_cost = 0
            self.last_reset = datetime.now().date()
        else:
            self.current_key_index += 1

        developerKey = self.DEVELOPER_KEYS[self.current_key_index]
        GlobalState.get_instance().set_state("key_progress", f"{self.current_key_index + 1}/{len(self.DEVELOPER_KEYS)}")
        log("key", f"Usando developerKey: {developerKey}")
        return build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION, developerKey=developerKey)

    def reset_quota_if_new_day(self):
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_cost = 0
            self.last_reset = today
            log("key", "Novo dia detectado. Resetando cota da chave atual.")

    def estimate_cost(self, method_name):
        # Exemplo simplificado de custos:
        cost_table = {
            "search": 100,
            "videos": 1,
            "commentThreads": 1,
            "channels": 1,
            "subscriptions": 1,
        }
        for key in cost_table:
            if key in method_name:
                return cost_table[key]
        return 1  # default

    def make_api_request(self, method_func, method_name, **kwargs):
        self.reset_quota_if_new_day()
        request_cost = self.estimate_cost(method_name)

        print(request_cost, self.daily_quota)

        if self.daily_quota < 10000:
            print("A chave atual reduziu a cota diária. Trocando de chave...")

        if False: #self.daily_cost + request_cost > self.daily_quota:
            log("key", "Cota diária da chave excedida. Trocando de chave...")
            self.youtube = self.get_new_youtube_client()
            return self.make_api_request(method_func, method_name='',**kwargs)

        self.daily_cost += request_cost

        with open("requisições.csv", mode='a', newline='') as csv_file:
            fieldnames = kwargs.keys()
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0:
                writer.writeheader()
            writer.writerow(kwargs)

        while True:
            try:
                request = method_func(self.youtube, **kwargs)
                return request.execute()

            except HttpError as e:
                jsonR = e.content if hasattr(e, 'content') else None
                dados_json = json.loads(jsonR)
                razao = dados_json["error"]["errors"][0]["reason"]

                if razao == "quotaExceeded":
                    log("key", "Chave excedeu a quota. Trocando de chave...")
                    self.youtube = self.get_new_youtube_client()
                    return self.make_api_request(method_func, '', **kwargs)
                elif razao == "commentsDisabled":
                    log("video", "Video com comentários desabilitados")
                    raise HttpError(e.resp, e.content, uri=e.uri)
                elif e.resp.status == 403:
                    print("Acesso ao vídeo é restrito.")
                    return None
                else:
                    print("Erro ao enviar requisição - tentando novamente em", config["try_again_timeout"], "s")
                    time.sleep(config["try_again_timeout"])

            except Exception as e:
                print("Problema de conexão - tentando novamente em", config["try_again_timeout"], "s")
                time.sleep(config["try_again_timeout"])

def create_files_path():
    DEST_DIRECTORY_NAME = "files"

    
    if not os.path.exists("./" + DEST_DIRECTORY_NAME):
        os.makedirs("./" + DEST_DIRECTORY_NAME)

def generate_date_intervals(start_date, end_date, interval_type):
    interval_delta = {"weekly": timedelta(weeks=1), "monthly": timedelta(days=30)}
    current_start = end_date
    while current_start > start_date:
        current_end = min(current_start, end_date)
        current_start = max(current_end - interval_delta[interval_type], start_date)
        yield current_start, current_end

def is_short_video(video_id):
    shorts_url = f"https://www.youtube.com/shorts/{video_id}"
    response = requests.head(shorts_url, allow_redirects=False)
    return response.status_code == 200

def get_video_details(video_id):
    api_manager = YouTubeAPIManager.get_instance()
    # while not client.should_continue_based_in_daily_quota(1):
    #     continue
    method_func = lambda client, **kwargs: client.videos().list(**kwargs)
    print(">> Request video detais")
    video_response = api_manager.make_api_request(method_func, method_name="videos().list", id=video_id,
                                                   part='snippet,statistics,contentDetails,status,liveStreamingDetails,localizations,topicDetails,recordingDetails')

    if video_response == None:
        print("Acesso ao vídeo é restrito e requer autorização adicional.")
        return None

    if not video_response.get('items'):
        print("Acesso ao vídeo é restrito e requer autorização adicional.")
        return None

    video_details = video_response['items'][0]
    snippet = video_details['snippet']
    contentDetails = video_details['contentDetails']
    status = video_details['status']
    statistics = video_details['statistics']
    processingDetails = video_details.get('processingDetails', {})
    liveStreamingDetails = video_details.get('liveStreamingDetails', {})
    localizations = video_details.get('localizations', {})
    topicDetails = video_details.get('topicDetails', {})
    recordingDetails = video_details.get('recordingDetails', {})

    details = {
        "video_id": video_id,
        "title": snippet.get('title'),
        "description": snippet.get('description'),
        "channel_id": snippet.get('channelId'),
        "published_at": snippet.get('publishedAt'),
        "category_id": snippet.get('categoryId', ""),
        "tags": snippet.get('tags', []),
        "view_count": int(statistics.get('viewCount', 0)),
        "like_count": int(statistics.get('likeCount', 0)),
        "comment_count": int(statistics.get('commentCount', 0)),
        "duration": contentDetails.get('duration'),
        "definition": contentDetails.get('definition'),
        "caption": contentDetails.get('caption') == 'true',
        "licensed_content": contentDetails.get('licensedContent', False),
        "privacy_status": status.get('privacyStatus'),
        "license": status.get('license'),
        "embeddable": status.get('embeddable', False),
        "public_stats_viewable": status.get('publicStatsViewable', False),
        "is_made_for_kids": status.get('madeForKids', False),
        "thumbnail_url": snippet.get('thumbnails', {}).get('high', {}).get('url'),
        "default_audio_language": snippet.get('defaultAudioLanguage'),
        "default_language": snippet.get('defaultLanguage'),
        "actual_start_time": liveStreamingDetails.get('actualStartTime', ''),
        "scheduled_start_time": liveStreamingDetails.get('scheduledStartTime', ''),
        "actual_end_time": liveStreamingDetails.get('actualEndTime', ''),
        "scheduled_end_time": liveStreamingDetails.get('scheduledEndTime', ''),
        "concurrent_viewers": liveStreamingDetails.get('concurrentViewers', 0),
        "active_live_chat_id": liveStreamingDetails.get('activeLiveChatId', ''),
        "recording_date": recordingDetails.get('recordingDate', ''),
        "topicCategories": topicDetails.get('topicCategories', []),
        "processing_status": processingDetails.get('processingStatus', ''),
        "parts_total": processingDetails.get('processingProgress', {}).get('partsTotal', 0),
        "parts_processed": processingDetails.get('processingProgress', {}).get('partsProcessed', 0),
        "time_left_ms": processingDetails.get('processingProgress', {}).get('timeLeftMs', 0),
        "processing_failure_reason": processingDetails.get('processingFailureReason', '')}

    res = not any(details.values())
    if res == True:
        print("Valores do get video detais")

    return details


def get_comments(video_id, video_title, total_comment_count):
    api_manager = YouTubeAPIManager.get_instance()  # Obtendo a instância do objeto

    comments_data = []
    page_token = None
    collected_comments = 0
    while True:
        try:
            # while not should_continue_based_in_daily_quota(1):
            #     continue
            method_func = lambda client, **kwargs: api_manager.youtube.commentThreads().list(**kwargs)
            print(">> Request de comentarios")
            response = api_manager.make_api_request(method_func, method_name='commentThreads().list', part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                pageToken=page_token,
                textFormat="plainText")
            
            # print(response)
        except HttpError as e:
            jsonR = e.content if hasattr(e, 'content') else None
            dados_json = json.loads(jsonR)
            
            razao = dados_json["error"]["errors"][0]["reason"]
            if e.resp.status == 404:
                log("video", f"Vídeo com ID {video_id} não encontrado. Pulando...")
                return comments_data  # Retorna os dados de comentários coletados até agora
            elif razao == "commentsDisabled":
                log("video", f"Vídeo com ID {video_id} possui comentários bloqueados. Pulando...")
                return comments_data  # Retorna os dados de comentários coletados até agora
            else:
                print(e["detailes"])
                raise e  # Releva outros erros para serem tratados externamente
    

        for item in response.get("items", []):
            collected_comments +=1  # Inicializa o contador de comentários coletado
            comment_info = item["snippet"]["topLevelComment"]["snippet"]
            comment_id = item["snippet"]["topLevelComment"]["id"]
            comments_data.append({
                "video_id": video_id,
                "comment_id": comment_id,
                "author": comment_info.get("authorDisplayName"),
                "author_profile_image_url": comment_info.get("authorProfileImageUrl"),
                "author_channel_url": comment_info.get("authorChannelUrl"),
                "author_channel_id": comment_info.get("authorChannelId", {}).get("value"),
                "comment": comment_info.get("textDisplay"),
                "published_at": comment_info.get("publishedAt"),
                "updated_at": comment_info.get("updatedAt", None),  # Pode não estar presente em todas as respostas
                "like_count": comment_info.get("likeCount"),
                "viewer_rating": comment_info.get("viewerRating", ""), 
                "can_rate": comment_info.get("canRate", ""),
                "is_reply": False,
                "parent_id": None
            })
            # Verifique se o comentário tem respostas e as colete
            total_reply_count = item["snippet"]["totalReplyCount"]            
            if total_reply_count > 0:
                print(">> Coletando replies")
                replies = get_replies(video_id, comment_id)
                comments_data.extend(replies)
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    res = not any(comments_data) 
    if res == True:
        log("comments", "Valores do get comments vazios")             

    print(f"Coletados {collected_comments} de {total_comment_count} comentários para o vídeo {video_id}.")
    return comments_data

def get_replies(video_id, comment_id):
    replies_data = []
    page_token = None
    api_manager = YouTubeAPIManager.get_instance()  # Obtendo a instância do objeto
    #print(">> Request de replies")
    while True:
        # while not should_continue_based_in_daily_quota(1):
        #     continue
        method_func = lambda client, **kwargs: api_manager.youtube.comments().list(**kwargs)
        nextPageToken = None
        try:

            response = api_manager.make_api_request(method_func, method_name='comments().list', part="snippet",
                parentId=comment_id,
                maxResults=100,
                pageToken=page_token,
                textFormat="plainText")

            if(nextPageToken == response.get('nextPageToken')):
                nextPageToken = None
            else:
                nextPageToken = response.get('nextPageToken')

            
            print("Salvando ", len(response.get("items", [])), " replies únicos", video_id)

            for item in response.get("items", []):
                reply_info = item["snippet"]
                replies_data.append({
                    "video_id": video_id,
                    "comment_id": item["id"],
                    "author": reply_info.get("authorDisplayName"),
                    "author_profile_image_url": reply_info.get("authorProfileImageUrl"),
                    "author_channel_url": reply_info.get("authorChannelUrl"),
                    "author_channel_id": reply_info.get("authorChannelId", {}).get("value"),
                    "comment": reply_info.get("textDisplay"),
                    "published_at": reply_info.get("publishedAt"),
                    "updated_at": reply_info.get("updatedAt", ""), 
                    "like_count": reply_info.get("likeCount"),
                    "viewer_rating": reply_info.get("viewerRating", ""), 
                    "can_rate": reply_info.get("canRate", ""),
                    "is_reply": True,
                    "parent_id": comment_id        
                })

            # page_token = response.get('nextPageToken')
            print("reply page token: ", nextPageToken)
            if not page_token:
                break
        except HttpError as e:
            print("Erro ocorreu ao coletar replies")
            with open(f"consulta_{video_id}_{comment_id}.txt", "w") as file: 
                file.write(e) 
            break
    
    res = not any(replies_data) 
    return replies_data

def get_channel_details(channel_id):
    api_manager = YouTubeAPIManager.get_instance()  # Obtendo a instância do objeto

    # while not should_continue_based_in_daily_quota(1):
    #     continue
    method_func = lambda client, **kwargs: api_manager.youtube.channels().list(**kwargs)
    # print(">> Request de detalhes do canal")
    channel_response = api_manager.make_api_request(method_func, method_name='channels().list',
        part="snippet,statistics,contentDetails,brandingSettings",
        id=channel_id)

    if not channel_response.get('items'):
        return None  # Retorna None se não encontrar detalhes do canal

    channel_details = channel_response['items'][0]
    snippet = channel_details['snippet']
    statistics = channel_details['statistics']
    brandingSettings = channel_details.get('brandingSettings', {})

    # Coleta de informações básicas e adicionais do canal
    details = {
        "channel_id": channel_id,
        "title": snippet.get('title', ""),
        "description": snippet.get('description', ""),
        "published_at": snippet.get('publishedAt', ""),
        "country": snippet.get('country', ""),  
        "view_count": int(statistics.get('viewCount', 0)),
        "comment_count": int(statistics.get('commentCount', 0)),
        "subscriber_count": int(statistics.get('subscriberCount', 0)),
        "video_count": int(statistics.get('videoCount', 0)),
        "is_verified": brandingSettings.get('channel', {}).get('isVerified', False),
        "keywords": brandingSettings.get('channel', {}).get('keywords', ""),  # Palavras-chave do canal
        "profile_picture_url": snippet.get('thumbnails', {}).get('default', {}).get('Link', ""),  # URL da imagem de perfil
    }

    res = not any(details.values()) 
    if res == True:
        log("channels", "Valores do get channel details vazios") 
    
    return details

# Função para processar um único vídeo
def process_video(video_id, video_title, processed_videos):
    global channels_info
    print(">> processando vídeos")
    videos_file_exists = os.path.isfile('files/videos_info.csv')
    channels_file_exists = os.path.isfile('files/channels_info.csv')
    comments_file_exists = os.path.isfile('files/comments_info.csv')

    video_details = get_video_details(video_id)
    if video_details == None:
        print("Erro por causa de autorização")
        return
    video_details['transcription'] = get_transcription(video_id)
    total_comment_count = video_details['comment_count']  # Assumindo que 'comment_count' é o total de comentários disponíveis

    pd.DataFrame([video_details]).to_csv('files/videos_info.csv', mode='a', header=not videos_file_exists, index=False)
    
    channel_details = get_channel_details(video_details['channel_id'])
    pd.DataFrame([channel_details]).to_csv('files/channels_info.csv', mode='a', header=not channels_file_exists, index=False)
        
    if total_comment_count > 0 and total_comment_count < 10000000000000: #Sentinel 
        try:
            comments = get_comments(video_id, video_title, total_comment_count)
            comments_df = pd.DataFrame(comments)
            comments_df['channel_id'] = video_details['channel_id']
            comments_df.to_csv('files/comments_info.csv', mode='a', header=not comments_file_exists, index=False)
        except:
            pass


    processed_videos.add(video_id)
    with open('files/processed_videos.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([video_id])
              
def make_search_request(channelId, published_after, published_before, REGION_CODE, RELEVANCE_LANGUAGE, page_token=None):
    """
    Realiza uma requisição de busca de vídeos na API do YouTube.
    Suporta paginação através do parâmetro page_token.

    Args:
        channelId (str): O ID do canal para buscar vídeos.
        published_after (str): Data de início do período de publicação (ISO 8601).
        published_before (str): Data de fim do período de publicação (ISO 8601).
        REGION_CODE (str): Código da região para filtrar resultados.
        RELEVANCE_LANGUAGE (str): Idioma de relevância para a pesquisa.
        page_token (str, optional): Token para a próxima página de resultados. Defaults to None.

    Returns:
        dict: A resposta da API do YouTube em formato JSON, ou None em caso de falha.
    """
    api_manager = YouTubeAPIManager.get_instance()

    # while not should_continue_based_in_daily_quota(100):
    #     continue
    method_func = lambda client, **kwargs: api_manager.youtube.search().list(**kwargs)
    
    print(">> Nova querie")
    
    # Prepara os parâmetros da requisição
    request_params = {
        "part": "id,snippet",
        "maxResults": 50,
        "type": "video",
        "order": "relevance",
        "publishedAfter": published_after,
        "publishedBefore": published_before,
        "regionCode": REGION_CODE,
        "relevanceLanguage": RELEVANCE_LANGUAGE,
        "channelId": channelId
    }

    # Adiciona o pageToken se ele for fornecido
    if page_token:
        request_params["pageToken"] = page_token

    search_response = api_manager.make_api_request(method_func, method_name="search", **request_params)

    if search_response is None:
        print(f"Erro: make_search_request recebeu None para o canal {channelId}. A requisição à API pode ter falhado.")
        return None
    
    number_of_videos = len(search_response.get('items', []))
    print(f"A requisição da query retornou {number_of_videos} vídeos.")

    return search_response

def main():
   # Configurar com aspas duplas os termos chaves -> testar primeiro....
    # channels = config["channels"]

    create_files_path() # Cria diretório files para armazenar saidas 

    df_autal_date = pd.read_csv('files/atual_date.csv', header=None)

    GlobalState.get_instance().set_state("status", "working")

    # Captura a data atual de busca do dataframe atual_date (year, month, day)
    atual_date = {
        "year": df_autal_date.iloc[0, 0],
        "month": df_autal_date.iloc[0, 1],
        "day": df_autal_date.iloc[0, 2],
    }

    start_date = datetime(config['start_date'][0], config['start_date'][1], config['start_date'][2]) #Data inicial da coleta 
    end_date = datetime(atual_date["year"], atual_date["month"], atual_date["day"]) #Data final 
    interval_type = "monthly" #Intervalo da busca, se é mensal(monthtly), ou semanal (weekly)
    REGION_CODE = config['region_code']
    RELEVANCE_LANGUAGE = config['relevance_language']
    TOP_COMMENTED = False #Pegar os vídeos mais comentados? Não vale a pena porque está retornando vídeo do tema...
    number_of_videos_to_process = 0
    REQUIRE_TITLE_KEYWORDS = False # Forçar o processamento dos vídeos e comentários com determinadas keywords nos títulos...
    
    processed_videos = set()

    # Tenta carregar vídeos já processados
    try:
        with open('files/processed_videos.csv', 'r') as file:
            processed_videos = {row[0] for row in csv.reader(file)}
    except FileNotFoundError:
        pass  # Continua com o conjunto vazio se o arquivo não existir

    api_manager = YouTubeAPIManager.get_instance()  # Obtendo a instância do objeto
    
    connectCheckAPI() # Conecta com a API de status -> Caso não configurou, ignore

    for start_interval, end_interval in generate_date_intervals(start_date, end_date, interval_type):
        log("interval", f"[{start_interval} - {end_interval}]")
        
        # Atualiza o atual_date.csv para cada iteração do gerador de intervalos
        with open("files/atual_date.csv", "w", newline="") as csvfile:
            fieldnames = ["year", "month", "day"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writerow({
                "year": end_interval.year,
                "month": end_interval.month,
                "day": end_interval.day
            })

        channels = ["UC3nQ4xUl6rodOWuQbBULyow",
                    "UCGPyMhoHjh3EyKUHuiNq0jA",
                    "UCeL1a4rpEA8UG9IQIewPccg",
                    "UCX0VSzJ2z5l0C9wnwh5SoRw",
                    "UCdVVI9mJUzGWShsD80poZMg",
                    "UCSpUAJw93VIHVn8k-JP8NTQ",
                    "UCExFA9MsrRmWnXUlhiwu4qA",
                    "UCI8GhdRx2zMoAlg-NvwRLog",
                    "UC1uQ9bGrXnbm27oSoRY1hOQ",
                    "UCDrGZXd8k06ifz0-gccIn0w",
                    "UCfx6e_bcnSL0aMDVx0xSlPw",
                    "UCwkhscWOa5gDDQ0R1f_rY_A",
                    "UC2mYg5TZ092oVhh66-9AYUA",
                    "UCeO2AubeXjuOfRcyZs_rIIA",
                    "UCpz_R2L_jolO-RG0V_KvyPQ",
                    "UCQDsVQO2-Lju8iDu3k_k-bw",
                    "UCCqPJ9sE7QQ1QUxTB4YiflA",
                    "UCZLKzB_7kUljL-A4TojxMmQ",
                    "UCpeW2LVGeNLnSXCp64b3TEQ",
                    "UCwC0gjZzYXopNGdXveEUS4A",
                    "UCYWqR3u-h0hiSARo0KyYl7g",
                    "UCRmNflJuD1TxLbRlDV08_7g",
                    "UC5jojOrPlt_4MwesFoI9p6A",
                    "UCUBeVY6Kn7ulBmUGynJqISw",
                    "UCoigiav3LDJJkt2SiXKxUaQ",
                    "UCO9FRrBUwGdYopkMbGGKbpg",
                    "UCAYoI16-UkXemcnhC-kTvDQ",
                    "UCNiU1wZxK6YN-KuJP7QMpBQ"]

        min_sleep_time = 60
        max_sleep_time = 180

        for channel_id in channels: # FOR POR CHANNEL_ID
            GlobalState.get_instance().set_state("atual_query", channel_id)
            GlobalState.get_instance().set_state("channel_id_progress", f"{channels.index(channel_id) + 1}/{len(channels)}")

            published_after = start_interval.isoformat() + "Z"
            published_before = end_interval.isoformat() + "Z"
            
            all_videos_from_channel = [] # Lista para acumular todos os vídeos do canal
            next_page_token = None # Começa sem token para a primeira requisição

            # Loop para paginar os resultados da pesquisa
            while True:
                search_response = make_search_request(
                    channel_id,
                    published_after,
                    published_before,
                    REGION_CODE,
                    RELEVANCE_LANGUAGE,
                    # Adiciona o pageToken se ele existir (para requisições subsequentes)
                    page_token=next_page_token 
                )

                if search_response is None:
                    print(f"A coleta do vídeo para o canal {channel_id} falhou na paginação. Indo para o próximo canal.")
                    break # Sai do loop de paginação e vai para o próximo canal_id
                
                current_page_videos = search_response.get("items", [])
                all_videos_from_channel.extend(current_page_videos) # Adiciona os vídeos da página atual

                # Obtém o token para a próxima página
                next_page_token = search_response.get("nextPageToken")

                # Se não há mais token, significa que chegamos ao final dos resultados
                if not next_page_token:
                    break

                # sleep_duration = random.uniform(min_sleep_time, max_sleep_time)
                # print(f"Esperando {sleep_duration:.2f} segundos antes da próxima requisição...")
                # time.sleep(sleep_duration)

            total_videos_collected = len(all_videos_from_channel)
            if total_videos_collected == 0:
                log("search", f"Nenhum vídeo encontrado para a consulta: {channel_id} entre {start_interval} e {end_interval}")
                continue

            # Agora, você itera sobre a lista completa de vídeos coletados
            for index, item in enumerate(all_videos_from_channel, start=1):
                VIDEO_TITLE = item['snippet']['title'].lower()
                key_words = config['key_words']

                try:
                    video_id = item['id']['videoId']
                    print(f"Processando vídeo {index} de {total_videos_collected}: ID = {video_id}")
                    if video_id not in processed_videos:
                        video_details = get_video_details(video_id)

                        if video_details is None:
                            print("A coleta dos detalhes do vídeo falhou. Indo para o próximo vídeo.")
                            continue

                        comment_count = video_details.get('comment_count', 0)
                        print("Title:", video_details.get('title', 'N/A'), "# comments", comment_count)
                        
                        process_video(video_id, "", processed_videos)
                except Exception as e:
                    print(f"Ocorreu um erro ao processar o vídeo {video_id}: {e}")
                    pass

            log("search", f"Coleta concluída para a consulta: {channel_id} entre {start_interval} e {end_interval}. Total de vídeos: {total_videos_collected}")


if __name__ == "__main__":
    main()
