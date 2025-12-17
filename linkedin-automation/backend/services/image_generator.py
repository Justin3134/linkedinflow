from openai import OpenAI
import requests
import base64
from PIL import Image
import io
import os
import config

class ImageGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAIIMAGE_API_KEY)
    
    def generate_post_image(self, prompt: str, save_path: str = "generated_image.png") -> Dict:
        """
        Generate image for LinkedIn post using OpenAI DALL-E
        """
        enhanced_prompt = f"Professional LinkedIn post image: {prompt}. Business professional style, clean design, high quality, corporate appropriate, modern aesthetic"
        
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Download and save image
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            
            image = Image.open(io.BytesIO(img_response.content))
            
            # Create images directory if it doesn't exist
            os.makedirs("images", exist_ok=True)
            full_path = os.path.join("images", save_path)
            image.save(full_path)
            
            return {
                "success": True,
                "image_path": full_path,
                "image_url": image_url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "image_path": None
            }

