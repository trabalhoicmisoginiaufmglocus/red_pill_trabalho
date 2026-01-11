import re

data = {
  "ideology": (
    "Red Pill",
    "Redpill",
    "VSM",
    "Valor Sexual de Mercado",
    "Masculinidade Forte",
    "Antiotário"
  ),
  "concepts": (
    "Macho Alfa",
    "Homem de valor",
    "Hipergamia",
    "Homem Beta",
    "Mulher 304",
    "Monkey branching",
    "80/20"
  ),
  "symbols": (
    "🗿", "🍷", "💊", "🫘", "💯", "💥"
  ),
  "slang": (
    "Chad",
    "Homem betinha",
    "Femimimi",
    "Polo masculino",
    "Polo Feminino"
  )
}

# TEMPLATES NÃO PODEM CONTER A MESMA VARIÁVEL MAIS DE UMA VEZ
templates = [
  "[ideology] [concepts] [symbols]",
  "[ideology] [slang]",
  "[concepts] [slang]"
]

def extract_variables(string):
  regex = r"\[(\w+)\]"
  variables = re.findall(regex, string)
  return variables

def generate_single_template(template, data):
  temp = [template]
  temp_2 = []

  n = len(extract_variables(template))

  for element in data:
    for string in temp:
      for value in data[element]:
        temp_2.append(string.replace(f"[{element}]", value))
    
    for item in temp_2:
      temp.append(item)
    for item in temp:
      if(len(extract_variables(item)) == n):
        temp.remove(item)
    n -= 1
    temp_2 = []

  res = []

  for item in temp:
    if len(extract_variables(item)) == 0 : 
      res.append(item)
  
  return res

# Pode sobrecarregar o limite de pesquisas da API
def generate_queries():
  # Inserção manual de pesquisas podem ser realizadas dentro da lista queries
  queries = [
        'O que é Red Pill?', 'O que significa VSM?',
        'O que é Valor Sexual de Mercado?', 'O que significa Hipergamia?',
        'Homem Alfa vs Homem Beta', 'Mulher 304, o que significa?',
        'O que é Monkey Branching?', 'A teoria 80/20 na Redpill',
        'Chad vs Beta: diferenças', 'O que significa "Femimimi"?',
        'Polo Masculino e Polo Feminino: qual a diferença?',
        'Símbolos Red Pill: significado de 🗿🍷💊', 'Como aumentar o VSM?',
        'A verdade sobre a hipergamia feminina', 'Por que o homem deve ser Alfa?',
        'Como aumentar meu valor sexual de mercado?', 'Qual a mulher ideal para um homem de valor?',
        'Como ser um homem de valor?', 'Quando as mulheres chegam na The Wall, o que fazer?', 
        'Como encontrar uma mulher ideial?', 'Incel vs Red Pill', 'Feminista vs Red Pill',
        'Por que o feminismo é ruim?', 'Como ser um bom Red Pill? 🗿',
        'Como encontrar a verdade da Red Pill?'
    ]

  # Para cada template
  for template in templates:
    
    # Cria o dicionario com os dados necessários para o template
    templateData = {} 
    for variable in extract_variables(template):
      templateData[variable] = data[variable]

    # Gera o conjunto de strings para aquele template
    list = generate_single_template(template, templateData)
    queries += list

  return queries
