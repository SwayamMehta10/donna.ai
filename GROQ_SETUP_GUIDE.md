# 🚀 Using Groq with AI Voice Agent - Setup Guide

This guide will help you configure your AI Voice Agent to use Groq instead of Ollama for LLM services. Groq provides fast, cloud-hosted language models without the need for local installation.

## 📋 Why Choose Groq?

- **High-speed inference** - Much faster responses than local Ollama
- **No local installation** - No need to download large model files
- **Free tier available** - Generous free allowance for testing
- **Access to advanced models** - Llama-3-8B, Mixtral, and more

## 🛠️ Setup Steps

### 1. **Create a Groq Account**

1. Visit [Groq Console](https://console.groq.com)
2. Sign up for a free account
3. Navigate to "API Keys" section
4. Generate a new API key
5. Copy your API key for later use

### 2. **Update Environment Configuration**

Edit your `.env` file in the project root:

```env
# Change the LLM provider from Ollama to Groq
LLM_PROVIDER=groq

# Set your Groq API key
LLM_API_KEY=gsk_your_api_key_here

# Choose a model (default is llama3-8b-8192)
LLM_MODEL=llama3-8b-8192

# Remove or comment out Ollama-specific settings
# LLM_API_URL=http://localhost:11434
```

### 3. **Supported Models**

Groq supports several models. As of September 2025, the most current models for this application are:

| Model Name | Description | Best For |
|------------|-------------|----------|
| `llama-3.1-8b-instant` | Llama 3.1 8B (recommended) | General purpose, fast responses |
| `gemma2-9b-it` | Gemma 2 9B | Alternative with good performance |
| `meta-llama/llama-4-scout-17b-16e-instruct` | Llama 4 Scout | Advanced reasoning |
| `meta-llama/llama-guard-4-12b` | Llama Guard | Content moderation |

> Note: Model availability may change over time. Run the `view_groq_models.py` script to see the current list of available models.

### 4. **Testing Your Configuration**

Run the following test script to verify your Groq integration works:

```bash
# Activate your virtual environment
.\myenv\Scripts\activate

# Create a test file
echo "import asyncio
from src.services.model import LLMService

async def test_groq():
    llm = LLMService()
    llm.provider = 'groq'
    llm.api_key = 'YOUR_API_KEY_HERE'  # Replace with your actual key
    llm.model = 'llama3-8b-8192'
    
    result = await llm._call_groq('Hello, please respond with a short greeting')
    print(f'Groq response: {result}')
    
asyncio.run(test_groq())" > test_groq.py

# Run the test
python test_groq.py
```

### 5. **Update Configuration File**

If you prefer to set this permanently in the code:

1. Copy `src/config/settings_example.py` to `src/config/settings.py` if not already done
2. Edit the LLM settings in `settings.py`:

```python
# LLM settings (using Groq)
'llm_provider': 'groq',  
'llm_model': 'llama3-8b-8192',  # Groq model
'llm_api_key': 'your_groq_api_key', 
```

## ⚙️ Performance Optimization

### Response Speed

Groq is optimized for fast responses. For even better performance:

1. Set a lower temperature (0.1-0.3) for more deterministic outputs
2. Use the smaller models (llama3-8b) for faster responses
3. Keep prompts concise and focused

### Error Handling

The code already includes error handling for Groq API calls, but if you encounter issues:

1. Check your internet connection
2. Verify your API key is correct
3. Ensure you're using a supported model name

## 🔄 Switching Between Providers

You can easily switch between Groq and Ollama:

### For Groq (Cloud):
```env
LLM_PROVIDER=groq
LLM_MODEL=llama3-8b-8192
LLM_API_KEY=your_api_key
```

### For Ollama (Local):
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_API_URL=http://localhost:11434
```

## 🔍 Troubleshooting

### Common Issues:

#### Connection Errors
```
Groq API call failed: ConnectionError
```
- Check your internet connection
- Verify firewall settings

#### Authentication Errors
```
Groq API error: 401 - Unauthorized
```
- Ensure your API key is correct
- Regenerate API key if necessary

#### Rate Limit Errors
```
Groq API error: 429 - Too Many Requests
```
- Reduce request frequency
- Consider upgrading plan if hitting free tier limits

## 📊 Monitoring Usage

1. Visit the [Groq Console](https://console.groq.com)
2. Navigate to "Usage" section
3. Monitor your API calls and token usage
4. Set up alerts if needed

---

With this guide, you should be able to successfully configure and use Groq as the LLM provider for your AI Voice Agent. Enjoy the improved performance and cloud-based convenience!