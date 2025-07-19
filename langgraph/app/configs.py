import logging
import os

from dotenv import dotenv_values, load_dotenv
from langchain_openai import AzureChatOpenAI

# Load variables from .env file into a dictionary
if os.path.exists(".env"):
    load_dotenv()
    config_env = dotenv_values(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

azure_gpt4o_mini = AzureChatOpenAI(
    api_key=config_env.get("AZURE_OPENAI_4O_MINI_API_KEY"),
    api_version=config_env.get("AZURE_OPENAI_4O_MINI_API_VERSION"),
    azure_deployment=config_env.get("AZURE_OPENAI_4O_MINI_DEPLOYMENT"),
    azure_endpoint=config_env.get("AZURE_OPENAI_4O_MINI_ENDPOINT"),
    model_name="gpt-4o-mini",
    temperature=0,
    n=1,
)

