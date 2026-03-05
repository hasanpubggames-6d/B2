import os
import base64
from openai import AsyncOpenAI
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class OCREngine:
    @staticmethod
    async def process_image(image_path: str, prompt: str = "Extract all text from this image accurately. Maintain the structure and paragraphs.") -> str:
        """
        Process an image using GPT-4 Vision to extract text.
        """
        try:
            # Optimize image before sending
            with Image.open(image_path) as img:
                # Resize if too large
                if img.width > 2000 or img.height > 2000:
                    img.thumbnail((2000, 2000))
                
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

            response = await client.chat.completions.create(
                model="gpt-4o-mini", # Using gpt-4o-mini for efficiency and cost
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OCR Error: {e}")
            return f"Error processing image: {str(e)}"

    @staticmethod
    async def process_pdf(pdf_path: str) -> str:
        """
        Placeholder for PDF processing. In a real scenario, we'd use pdf2image 
        and process each page through process_image.
        """
        # Implementation would require pdf2image and poppler
        return "PDF processing logic would go here, converting pages to images and using OCR."
