import yaml
import os
import time
from typing import ClassVar
from dotenv import load_dotenv
from crewai import Crew, Agent, Task
from crewai.tools import BaseTool
import logging
from pprint import pformat
from serpapi import GoogleSearch

# Configuração do logger do Django
logger = logging.getLogger(__name__)

load_dotenv()

class GoogleSearchWrapper(BaseTool):
    name: str = "Web Search"
    description: str = "Pesquisa na web usando Google Search"
    api_key: ClassVar[str] = "722a75fd8a59e05a335b8c40c22bb85f0bfc5b5d68c8df05ba364e64f663525f"
    max_retries: ClassVar[int] = 3
    delay_between_retries: ClassVar[int] = 2

    def _run(self, query: str) -> str:
        for attempt in range(self.max_retries):
            try:
                search = GoogleSearch({
                    "q": query,
                    "api_key": self.api_key,
                    "num": 5  
                })
                results = search.get_dict()
                
                if "error" in results:
                    raise Exception(f"Erro na API do Google: {results['error']}")
                
                formatted_results = []
                for result in results.get("organic_results", []):
                    title = result.get("title", "Sem título")
                    link = result.get("link", "")
                    snippet = result.get("snippet", "Sem descrição")
                    formatted_results.append(f"Título: {title}\nLink: {link}\nDescrição: {snippet}\n")
                
                return "\n".join(formatted_results)
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.delay_between_retries * (attempt + 1)
                    logger.warning(f"Erro na pesquisa. Aguardando {wait_time} segundos antes de tentar novamente...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"Erro após {self.max_retries} tentativas: {str(e)}")
                raise


class NewsCrew:
    def __init__(self):
        self.tasks_map = {}
        try:
            logger.info("Iniciando NewsCrew")
            self.load_config()
            self.setup_tools()
            self.setup_agents()
            self.setup_tasks()
            logger.info("NewsCrew inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro na inicialização do NewsCrew: {str(e)}", exc_info=True)
            raise

    def load_config(self):
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            agents_path = os.path.join(base_path, 'config', 'agents.yml')
            tasks_path = os.path.join(base_path, 'config', 'tasks.yml')
            
            logger.info(f"Carregando configurações de: {agents_path} e {tasks_path}")
            
            with open(agents_path, 'r', encoding='utf-8') as f:
                self.agents_config = yaml.safe_load(f)
                logger.debug(f"Configuração dos agentes carregada: \n{pformat(self.agents_config)}")
            
            with open(tasks_path, 'r', encoding='utf-8') as f:
                self.tasks_config = yaml.safe_load(f)
                logger.debug(f"Configuração das tarefas carregada: \n{pformat(self.tasks_config)}")
        except Exception as e:
            logger.error(f"Erro ao carregar arquivos de configuração: {str(e)}", exc_info=True)
            raise

    def setup_tools(self):
        try:
            search = GoogleSearchWrapper()
            self.tools = {
                'web_search': search
            }
            logger.info("Ferramentas configuradas com sucesso")
            logger.debug(f"Ferramentas disponíveis: {list(self.tools.keys())}")
        except Exception as e:
            logger.error(f"Erro na configuração das ferramentas: {str(e)}", exc_info=True)
            raise

    def setup_agents(self):
        self.agents = {}
        try:
            for agent_id, config in self.agents_config.items():
                logger.info(f"Configurando agente: {agent_id}")
                logger.debug(f"Configuração do agente {agent_id}: \n{pformat(config)}")
                
                self.agents[agent_id] = Agent(
                    name=config['name'],
                    role=config['role'],
                    goal=config['goal'],
                    backstory=config['backstory'],
                    verbose=True,
                    allow_delegation=False,
                    tools=[self.tools['web_search']]
                )
            logger.info(f"Total de {len(self.agents)} agentes configurados")
            logger.debug(f"Agentes configurados: {list(self.agents.keys())}")
        except Exception as e:
            logger.error(f"Erro na configuração dos agentes: {str(e)}", exc_info=True)
            raise

    def setup_tasks(self):
        self.tasks = []
        self.tasks_map = {} 
        try:
            logger.debug(f"Iniciando configuração das tarefas. Tipo de tasks_config: {type(self.tasks_config)}")
            logger.debug(f"Conteúdo de tasks_config: \n{pformat(self.tasks_config)}")
            
            # Primeiro cria todas as tarefas
            for task_config in self.tasks_config['tasks']:                
                agent = self.agents.get(task_config['agent'])
                    
                task_tools = []
                for tool in task_config.get('tools', []):
                    if tool in self.tools:
                        task_tools.append(self.tools[tool])
                    else:
                        logger.warning(f"Ferramenta '{tool}' não encontrada. Ferramentas disponíveis: {list(self.tools.keys())}")
                
                task = Task(
                    description=task_config['description'],
                    agent=agent,
                    expected_output=task_config['expected_output'],
                    tools=task_tools,
                    context=[]  # Contexto inicial vazio
                )
                
                self.tasks_map[task_config['id']] = task  
                self.tasks.append(task)
            
            for task_config, task in zip(self.tasks_config['tasks'], self.tasks):
                context_ids = task_config.get('context', [])
                if isinstance(context_ids, str):
                    context_ids = [context_ids]
                    
                task.context = [
                    self.tasks_map[ctx_id] 
                    for ctx_id in context_ids 
                    if ctx_id in self.tasks_map
                ]
            
            logger.info(f"Total de {len(self.tasks)} tarefas configuradas")
        except Exception as e:
            logger.error(f"Erro na configuração das tarefas: {str(e)}", exc_info=True)
            raise

    def run(self):
        try:
            logger.info("Iniciando execução da crew")
            crew = Crew(
                agents=list(self.agents.values()),
                tasks=self.tasks,
                verbose=False
            )
            result = crew.kickoff()
            return result
        
        except Exception as e:
            logger.error(f"Erro durante a execução da crew: {str(e)}", exc_info=True)
            raise e
