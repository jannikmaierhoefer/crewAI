import logging
import os
import urllib.parse

from typing import Any, Dict, Optional, cast

from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.api.types import validate_embedding_function

logger = logging.getLogger(__name__)


class EmbeddingConfigurator:
    @staticmethod
    def _validate_url(url: str) -> str:
        """Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            str: The validated URL
            
        Raises:
            ValueError: If URL is invalid
        """
        try:
            result = urllib.parse.urlparse(url)
            if all([result.scheme, result.netloc]):
                return url
            raise ValueError(f"Invalid URL format: {url}")
        except Exception as e:
            raise ValueError(f"Invalid URL: {str(e)}")

    def __init__(self):
        self.embedding_functions = {
            "openai": self._configure_openai,
            "azure": self._configure_azure,
            "ollama": self._configure_ollama,
            "vertexai": self._configure_vertexai,
            "google": self._configure_google,
            "cohere": self._configure_cohere,
            "voyageai": self._configure_voyageai,
            "bedrock": self._configure_bedrock,
            "huggingface": self._configure_huggingface,
            "watson": self._configure_watson,
            "custom": self._configure_custom,
        }

    def configure_embedder(
        self,
        embedder_config: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingFunction:
        """Configures and returns an embedding function based on the provided config."""
        if embedder_config is None:
            return self._create_default_embedding_function()

        provider = embedder_config.get("provider")
        config = embedder_config.get("config", {})
        model_name = config.get("model") if provider != "custom" else None

        if provider not in self.embedding_functions:
            raise Exception(
                f"Unsupported embedding provider: {provider}, supported providers: {list(self.embedding_functions.keys())}"
            )

        embedding_function = self.embedding_functions[provider]
        return (
            embedding_function(config)
            if provider == "custom"
            else embedding_function(config, model_name)
        )

    @staticmethod
    def _create_default_embedding_function():
        from chromadb.utils.embedding_functions.openai_embedding_function import (
            OpenAIEmbeddingFunction,
        )

        return OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"), model_name="text-embedding-3-small"
        )

    @staticmethod
    def _configure_openai(config, model_name):
        from chromadb.utils.embedding_functions.openai_embedding_function import (
            OpenAIEmbeddingFunction,
        )

        return OpenAIEmbeddingFunction(
            api_key=config.get("api_key") or os.getenv("OPENAI_API_KEY"),
            model_name=model_name,
            api_base=config.get("api_base", None),
            api_type=config.get("api_type", None),
            api_version=config.get("api_version", None),
            default_headers=config.get("default_headers", None),
            dimensions=config.get("dimensions", None),
            deployment_id=config.get("deployment_id", None),
            organization_id=config.get("organization_id", None),
        )

    @staticmethod
    def _configure_azure(config, model_name):
        from chromadb.utils.embedding_functions.openai_embedding_function import (
            OpenAIEmbeddingFunction,
        )

        return OpenAIEmbeddingFunction(
            api_key=config.get("api_key"),
            api_base=config.get("api_base"),
            api_type=config.get("api_type", "azure"),
            api_version=config.get("api_version"),
            model_name=model_name,
            default_headers=config.get("default_headers"),
            dimensions=config.get("dimensions"),
            deployment_id=config.get("deployment_id"),
            organization_id=config.get("organization_id"),
        )

    @staticmethod
    def _configure_ollama(config: Dict[str, Any], model_name: Optional[str]) -> EmbeddingFunction:
        """Configure Ollama embedder with flexible URL configuration.
        
        Args:
            config: Configuration dictionary that supports multiple URL keys in priority order:
                1. url: Legacy key (highest priority)
                2. api_url: Alternative key following HuggingFace pattern
                3. base_url: Alternative key
                4. api_base: Alternative key following Azure pattern
                Default: http://localhost:11434/api/embeddings
            model_name: Name of the Ollama model to use
            
        Returns:
            OllamaEmbeddingFunction: Configured embedder instance
            
        Raises:
            ValueError: If URL is invalid or model name is missing
        """
        from chromadb.utils.embedding_functions.ollama_embedding_function import (
            OllamaEmbeddingFunction,
        )

        if not model_name:
            raise ValueError("Model name is required for Ollama embedder configuration")

        url = (
            config.get("url")
            or config.get("api_url")
            or config.get("base_url")
            or config.get("api_base")
            or "http://localhost:11434/api/embeddings"
        )
        
        validated_url = EmbeddingConfigurator._validate_url(url)
        logger.info(f"Configuring Ollama embedder with URL: {validated_url}")

        return OllamaEmbeddingFunction(
            url=validated_url,
            model_name=model_name,
        )

    @staticmethod
    def _configure_vertexai(config, model_name):
        from chromadb.utils.embedding_functions.google_embedding_function import (
            GoogleVertexEmbeddingFunction,
        )

        return GoogleVertexEmbeddingFunction(
            model_name=model_name,
            api_key=config.get("api_key"),
            project_id=config.get("project_id"),
            region=config.get("region"),
        )

    @staticmethod
    def _configure_google(config, model_name):
        from chromadb.utils.embedding_functions.google_embedding_function import (
            GoogleGenerativeAiEmbeddingFunction,
        )

        return GoogleGenerativeAiEmbeddingFunction(
            model_name=model_name,
            api_key=config.get("api_key"),
            task_type=config.get("task_type"),
        )

    @staticmethod
    def _configure_cohere(config, model_name):
        from chromadb.utils.embedding_functions.cohere_embedding_function import (
            CohereEmbeddingFunction,
        )

        return CohereEmbeddingFunction(
            model_name=model_name,
            api_key=config.get("api_key"),
        )

    @staticmethod
    def _configure_voyageai(config, model_name):
        from chromadb.utils.embedding_functions.voyageai_embedding_function import (
            VoyageAIEmbeddingFunction,
        )

        return VoyageAIEmbeddingFunction(
            model_name=model_name,
            api_key=config.get("api_key"),
        )

    @staticmethod
    def _configure_bedrock(config, model_name):
        from chromadb.utils.embedding_functions.amazon_bedrock_embedding_function import (
            AmazonBedrockEmbeddingFunction,
        )

        # Allow custom model_name override with backwards compatibility
        kwargs = {"session": config.get("session")}
        if model_name is not None:
            kwargs["model_name"] = model_name
        return AmazonBedrockEmbeddingFunction(**kwargs)

    @staticmethod
    def _configure_huggingface(config, model_name):
        from chromadb.utils.embedding_functions.huggingface_embedding_function import (
            HuggingFaceEmbeddingServer,
        )

        return HuggingFaceEmbeddingServer(
            url=config.get("api_url"),
        )

    @staticmethod
    def _configure_watson(config, model_name):
        try:
            import ibm_watsonx_ai.foundation_models as watson_models
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
        except ImportError as e:
            raise ImportError(
                "IBM Watson dependencies are not installed. Please install them to use Watson embedding."
            ) from e

        class WatsonEmbeddingFunction(EmbeddingFunction):
            def __call__(self, input: Documents) -> Embeddings:
                if isinstance(input, str):
                    input = [input]

                embed_params = {
                    EmbedParams.TRUNCATE_INPUT_TOKENS: 3,
                    EmbedParams.RETURN_OPTIONS: {"input_text": True},
                }

                embedding = watson_models.Embeddings(
                    model_id=config.get("model"),
                    params=embed_params,
                    credentials=Credentials(
                        api_key=config.get("api_key"), url=config.get("api_url")
                    ),
                    project_id=config.get("project_id"),
                )

                try:
                    embeddings = embedding.embed_documents(input)
                    return cast(Embeddings, embeddings)
                except Exception as e:
                    print("Error during Watson embedding:", e)
                    raise e

        return WatsonEmbeddingFunction()

    @staticmethod
    def _configure_custom(config):
        custom_embedder = config.get("embedder")
        if isinstance(custom_embedder, EmbeddingFunction):
            try:
                validate_embedding_function(custom_embedder)
                return custom_embedder
            except Exception as e:
                raise ValueError(f"Invalid custom embedding function: {str(e)}")
        elif callable(custom_embedder):
            try:
                instance = custom_embedder()
                if isinstance(instance, EmbeddingFunction):
                    validate_embedding_function(instance)
                    return instance
                raise ValueError(
                    "Custom embedder does not create an EmbeddingFunction instance"
                )
            except Exception as e:
                raise ValueError(f"Error instantiating custom embedder: {str(e)}")
        else:
            raise ValueError(
                "Custom embedder must be an instance of `EmbeddingFunction` or a callable that creates one"
            )
