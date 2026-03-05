import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TranslationEngine:
    @staticmethod
    async def translate_text(text: str, target_lang: str = "Arabic", source_lang: str = "Auto-detect") -> str:
        """
        Translate text using GPT-4o-mini for high quality human-like translation.
        """
        try:
            prompt = f"""
            Translate the following text from {source_lang} to {target_lang}.
            Maintain the original formatting, paragraphs, and structure.
            The translation should be natural and human-like.
            
            Text:
            {text}
            """
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional translator specializing in high-quality, natural translations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Translation Error: {e}")
            return f"Error translating text: {str(e)}"

    @staticmethod
    async def post_process_ai(text: str) -> str:
        """
        AI Post-processing to fix OCR errors and improve flow.
        """
        try:
            prompt = f"""
            The following text was extracted via OCR. Please fix any obvious spelling errors, 
            improve the flow, and ensure the formatting is clean. 
            Do not change the meaning of the text.
            
            Text:
            {text}
            """
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert editor specializing in fixing OCR errors and improving text clarity."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Post-processing Error: {e}")
            return text # Return original if AI fails
