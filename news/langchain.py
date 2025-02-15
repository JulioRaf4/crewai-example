import os
from typing import List

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()

class TitleGenerator:
    def __init__(self):
        self.model = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.prompt = PromptTemplate.from_template("""
            Você é um editor especializado em criar títulos chamativos e informativos para notícias de tecnologia.
            
            Para cada notícia fornecida, crie um título em português que seja:
            1. Conciso (máximo 100 caracteres)
            2. Informativo
            3. Atraente para o leitor
            4. Fiel ao conteúdo
            
            Notícia:
            {text}
            
            Retorne apenas o título, sem aspas ou formatação adicional.
        """)

    def create_title(self, text: str) -> str:
        chain = self.prompt | self.model
        return chain.invoke({"text": text})

    def create_titles(self, news_list: List[str]) -> List[str]:
        """Gera títulos para uma lista de notícias"""
        titles = []
        for news in news_list:
            title = self.create_title(news)
            # Extrai apenas o conteúdo da resposta do modelo
            title = title.content.strip()
            titles.append(title)
        return titles 