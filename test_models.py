import os; from dotenv import load_dotenv; load_dotenv('.env'); import google.generativeai as genai; from langchain_google_genai import ChatGoogleGenerativeAI; api_key = os.getenv('GOOGLE_API_KEY'); 
models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.5-flash', 'gemini-3.1-pro-preview', 'gemini-flash-lite-latest']
for m in models:
    try:
        print(f'Testing {m}...')
        response = ChatGoogleGenerativeAI(model=m, google_api_key=api_key).invoke('hi')
        print(f'SUCCESS: {m}')
    except Exception as e:
        print(f'ERROR {m}: {e}')
