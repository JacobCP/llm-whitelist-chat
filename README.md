# Motivation
The LLM models behind chat interfaces such as ChatGPT and Bard are trained on public online content, and can be used to access information on any topic available publicly online. They are also finetuned with RLHF (Reinforcement Learning from Human Feedback) which, while limiting some undesirable content, also incorporates the organization's opinions and moral values into the model's output.

In some cases, a user may want to use an LLM chat interface without the potential for exposure to some of the content or opinions and moral values.

In cases where the Chat interface is needed for one specific purpose (i.e. coding, legal advice, etc.), it can be easier to limit the interface to only that purpose (whitelisting) rather than limiting it from the undesired content/options (blacklisting)

# Application
The application uses OpenAI's API for the LLM model, and streamlit for the UI.  

It currently utilizes OpenAI's "system message" to restrict the model to only provide content on one topic (currently coding).   

GPT-4 is used, as GPT-3.5 doesn't reliably follow the instructions of the system message.

To use the application, you'll need to either provide your own OpenAI API key, with access to GPT-4. (some users have been provided with a username/password that enables them to use the system's API key)
