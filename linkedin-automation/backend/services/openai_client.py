from openai import OpenAI
import json
from typing import Dict, List, Optional
import config

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def generate_linkedin_post(self, source_content: str, context: Optional[str] = None) -> Dict:
        """
        Generate LinkedIn post from source content
        """
        context_info = f"\n\nContext: {context}" if context else ""
        
        prompt = f"""
        Based on the following content, create an engaging LinkedIn post:
        
        {source_content}
        {context_info}
        
        Requirements:
        - Professional but engaging tone
        - Include relevant emojis (3-5 max)
        - Add 3-5 relevant hashtags at the end
        - Hook in the first line to grab attention
        - 200-300 words
        - LinkedIn best practices (authentic, value-driven)
        
        IMPORTANT: Return ONLY valid JSON (no markdown, no code blocks) in this exact format:
        {{
            "content": "the post content with hashtags",
            "hashtags": ["tag1", "tag2", "tag3"],
            "image_description": "description for AI image generation (professional, business-appropriate)"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
                # Removed response_format - parse JSON from text response instead
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Try to parse as JSON
            try:
                result = json.loads(content)
                return {
                    "success": True,
                    "post_content": result.get("content", ""),
                    "hashtags": result.get("hashtags", []),
                    "image_description": result.get("image_description", "")
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, use the content as-is and extract hashtags
                hashtags = []
                lines = content.split('\n')
                for line in lines:
                    if '#' in line:
                        import re
                        hashtags.extend(re.findall(r'#\w+', line))
                
                return {
                    "success": True,
                    "post_content": content,
                    "hashtags": hashtags[:5] if hashtags else ["ProfessionalDevelopment", "CareerAdvice", "Leadership"],
                    "image_description": "Professional LinkedIn post image, business setting, modern design"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_linkedin_comment(self, original_comment: str, post_context: Optional[str] = None) -> str:
        """
        Generate a thoughtful reply to a LinkedIn comment
        """
        prompt = f"""
        Generate a professional, personalized reply to this LinkedIn comment:
        
        Comment: "{original_comment}"
        
        {f"Post context: {post_context}" if post_context else ""}
        
        Guidelines:
        - Be specific and reference their point
        - Add value to the conversation
        - Professional but warm tone
        - 50-100 words
        - Show engagement and appreciation
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Thank you for your comment! {str(e)}"
    
    def generate_linkedin_message(self, recipient_context: str, trigger_context: str) -> str:
        """
        Generate personalized LinkedIn message
        trigger_context: 'post_like', 'comment', 'connection'
        """
        templates = {
            "post_like": f"""
            Generate a personalized LinkedIn message for someone who liked my post.
            
            Recipient context: {recipient_context}
            
            Guidelines:
            - Thank them for engaging
            - Reference the post topic
            - Invite further conversation
            - Professional but friendly
            - 100-150 words
            """,
            "comment": f"""
            Generate a personalized LinkedIn message for someone who commented on my post.
            
            Recipient context: {recipient_context}
            
            Guidelines:
            - Thank them for their thoughtful comment
            - Continue the conversation
            - Build connection
            - Professional but warm
            - 100-150 words
            """
        }
        
        template = templates.get(trigger_context, templates["post_like"])
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": template}],
                temperature=0.8
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Hi! Thanks for engaging with my post. I'd love to connect and continue the conversation!"

