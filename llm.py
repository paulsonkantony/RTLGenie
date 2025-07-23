import logging
import tomllib
from langchain_openai import AzureChatOpenAI

logger = logging.getLogger("root")
logger.info("Imported TB Generator module")

def parse_toml_file(file_path):
    with open(file_path, "rb") as f:
        config = tomllib.load(f)
    return config
config = parse_toml_file("config.toml")

llm = AzureChatOpenAI(
    azure_deployment   = config["LLM"]["azure_deployment"],
    azure_endpoint     = config["LLM"]["azure_endpoint"],
    openai_api_key     = "dummy",  # required but not used
    openai_api_type    = config["LLM"]["openai_api_type"],
    openai_api_version = config["LLM"]["openai_api_version"],
    model              = config["LLM"]["model"],
    default_headers    = {"genaiplatform-farm-subscription-key": config["LLM"]["key"],}
)