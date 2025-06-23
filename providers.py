# Provider configuration for different AI model providers
# Maps models to their providers, API key names, and base URLs

PROVIDERS = {
    "OpenAI": {
        "api_key_name": "OPENAI_API_KEY",
        "base_url": None,  # Use default OpenAI base URL
        "models": ["gpt-4.1", "gpt-4.1-mini", "gpt-o3", "gpt-o4-mini", "gpt-4o"],
    },
    "Perplexity": {
        "api_key_name": "PERPLEXITY_API_KEY",
        "base_url": "https://api.perplexity.ai",
        "models": ["sonar-pro", "sonar-reasoning"],
    },
}


def get_model_provider_options():
    """Return a list of model/provider combinations for the dropdown"""
    options = []
    for provider_name, provider_config in PROVIDERS.items():
        for model in provider_config["models"]:
            options.append(f"{model} ({provider_name})")
    return options


def parse_model_selection(selection):
    """Parse the model/provider selection and return model, provider info"""
    # Format: "model_name (Provider_Name)"
    if " (" in selection and selection.endswith(")"):
        model = selection.split(" (")[0]
        provider_name = selection.split(" (")[1][:-1]

        if provider_name in PROVIDERS:
            provider_config = PROVIDERS[provider_name]
            return {
                "model": model,
                "provider": provider_name,
                "api_key_name": provider_config["api_key_name"],
                "base_url": provider_config["base_url"],
            }

    raise ValueError(f"Invalid model selection format: {selection}")


def get_all_api_key_names():
    """Return a list of all API key names needed"""
    return [config["api_key_name"] for config in PROVIDERS.values()]
