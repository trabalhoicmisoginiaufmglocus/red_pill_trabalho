# Código não testado --> adicionei apenas as palavras chave que havíamos envontrado (não adicionei os emojis).
# Adicionar APIs
# Testar primeiro com intervalo curto --> perceber tempo de demora


config = {
  # Configuração da região da coleta -> Formato: ISO 3166-1 alpha-2
  'region_code': 'BR',         

  # Configuração da linguagem da coleta -> Formato: ISO 639-1   
  'relevance_language': 'pt',     

  # A coleta ocorre da data final para a data inicial -> [ano, mês, dia]
  'start_date': [2024, 1, 1], 
  'end_date': [2025, 6, 30],

  # API que receberá uma requisição PATCH com payload de um JSON contendo informações acerca da coleta
  # Mantenha uma string vazia '' Caso não tenha configurado
  'api_endpoint': '',
  # Intervalo, em segundos, entre cada envio de dados para a API
  'api_cooldown': 60,                                                   

  # Intervalo, em segundos, entre cada tentativa de requisição para a API apos falha
  'try_again_timeout': 60,                                              


  # KEYs da API v3 do YouTube
  'youtube_keys' : [
    'AIzaSyC6RXuA9Xilf6DVbyz6VL1rQgijGY-1u3I',
    'AIzaSyBFY8UGvfJSkiQ3ub-g38SEtsKORFZ47hc',
    'AIzaSyD49vEckVpDgNPdGii5hwGPv8_aoN8ffUg',
    'AIzaSyCAIm4SYVZt6Q2RSNggEiopIysudvN8EF4',
    'AIzaSyBrHy8f9rcUx8JAUbCXPvapfYLEtI3TPqk',
    'AIzaSyD2LZnwEExmB9NM9WMslBcrlr7FXax2VVg'
  ],


  'channels_id' : [
    'UCeL1a4rpEA8UG9IQIewPccg','UCNiU1wZxK6YN-KuJP7QMpBQ','UCAYoI16-UkXemcnhC-kTvDQ','UCExFA9MsrRmWnXUlhiwu4qA',
    'UCX0VSzJ2z5l0C9wnwh5SoRw','UC3nQ4xUl6rodOWuQbBULyow','UCSpUAJw93VIHVn8k-JP8NTQ','UCGPyMhoHjh3EyKUHuiNq0jA',
    'UC2mYg5TZ092oVhh66-9AYUA','UCfx6e_bcnSL0aMDVx0xSlPw','UCeO2AubeXjuOfRcyZs_rIIA','UCDrGZXd8k06ifz0-gccIn0w',
    'UCZLKzB_7kUljL-A4TojxMmQ','UCYWqR3u-h0hiSARo0KyYl7g','UCpz_R2L_jolO-RG0V_KvyPQ','UCCqPJ9sE7QQ1QUxTB4YiflA',
    'UCI8GhdRx2zMoAlg-NvwRLog','UCoigiav3LDJJkt2SiXKxUaQ','UC1uQ9bGrXnbm27oSoRY1hOQ','UCwC0gjZzYXopNGdXveEUS4A',
    'UC5jojOrPlt_4MwesFoI9p6A','UCQDsVQO2-Lju8iDu3k_k-bw',
    'UCOmgZM9a03QjICfkCaxcjYA',
    'UCO9FRrBUwGdYopkMbGGKbpg',
    'UCRmNflJuD1TxLbRlDV08_7g',
    'UCUBeVY6Kn7ulBmUGynJqISw',
    'UCpeW2LVGeNLnSXCp64b3TEQ',
    'UCdVVI9mJUzGWShsD80poZMg',
    'UCwkhscWOa5gDDQ0R1f_rY_A'
  ]

}
