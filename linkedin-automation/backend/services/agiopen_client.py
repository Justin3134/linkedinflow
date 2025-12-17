import asyncio
import os
import shutil
import threading
from typing import Dict, Optional, List
from pathlib import Path
import config
import pyperclip
from oagi import TaskerAgent, AsyncDefaultAgent
from oagi import AsyncPyautoguiActionHandler, AsyncScreenshotMaker

# Global flag for stopping automation
_stop_flag = threading.Event()

class AGIOpenClient:
    def __init__(self):
        self.api_key = config.AGIOPEN_API_KEY
        self.current_task = None
        # Ensure OAGI environment is set
        if self.api_key:
            os.environ['OAGI_API_KEY'] = self.api_key
        if 'OAGI_BASE_URL' not in os.environ:
            os.environ['OAGI_BASE_URL'] = "https://api.agiopen.org"
    
    def stop_current_task(self):
        """Stop the current automation task immediately"""
        global _stop_flag
        _stop_flag.set()
        
        # Cancel the task forcefully
        if self.current_task and not self.current_task.done():
            try:
                self.current_task.cancel()
                # Force cancellation - don't wait
                print("🛑 Stop signal sent - cancelling task immediately")
            except Exception as e:
                print(f"⚠️ Error cancelling task: {e}")
        
        # Clear the current task reference
        self.current_task = None
        print("🛑 Automation stopped - control released to user")
    
    def _run_async(self, coro):
        """Helper to run async code in sync context"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create new one
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
    
    async def _create_post_async(self, content: str, image_path: Optional[str] = None) -> Dict:
        """Create LinkedIn post draft using OAGI SDK"""
        try:
            agent = TaskerAgent(model="lux-actor-1")
            
            # Truncate content if too long for instruction
            content_preview = content[:300] if len(content) > 300 else content
            
            todos = [
                "Go to https://linkedin.com/feed",
                "Click the 'Start a post' button or text box",
                f"Type the following content in the post editor: {content}",
                "Wait for the content to be fully typed"
            ]
            
            if image_path and os.path.exists(image_path):
                # Convert to absolute path
                abs_image_path = os.path.abspath(image_path)
                todos.extend([
                    "Click the 'Add a photo' or 'Media' button",
                    f"Upload the image file at: {abs_image_path}",
                    "Wait for the image to upload"
                ])
            
            agent.set_task(
                task="Create a LinkedIn post draft",
                todos=todos
            )
            
            await agent.execute(
                instruction="Create a LinkedIn post with the provided content and image if available",
                action_handler=AsyncPyautoguiActionHandler(),
                image_provider=AsyncScreenshotMaker(),
            )
            
            return {"success": True, "message": "Post draft created successfully"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def create_linkedin_post(self, content: str, image_path: Optional[str] = None) -> Dict:
        """Create LinkedIn post - synchronous wrapper"""
        return self._run_async(self._create_post_async(content, image_path))
    
    async def _create_and_publish_post_async(self, content: str, image_path: Optional[str] = None) -> Dict:
        """Create LinkedIn post draft with text and image - stops after uploading image (user posts manually)"""
        global _stop_flag
        _stop_flag.clear()  # Reset stop flag
        
        try:
            # Check stop flag before starting
            if _stop_flag.is_set():
                return {"success": False, "error": "Operation cancelled"}
            
            # Step 1: Copy content to clipboard for faster pasting
            # CRITICAL: Use the exact content passed to this function (from frontend)
            try:
                pyperclip.copy(content)
                print(f"✅ Content copied to clipboard ({len(content)} chars)")
                print(f"📋 Clipboard preview: {content[:200]}...")
            except Exception as e:
                print(f"⚠️ Could not copy to clipboard: {e}")
                # Continue anyway - OAGI can type it manually
            
            agent = TaskerAgent(model="lux-actor-1")
            
            # Create a dedicated folder for LinkedIn post images
            linkedin_images_folder = os.path.abspath(os.path.join("images", "linkedin_posts"))
            os.makedirs(linkedin_images_folder, exist_ok=True)
            
            # If image exists, ensure it's in the linkedin_posts folder
            final_image_path = None
            if image_path and os.path.exists(image_path):
                image_filename = os.path.basename(image_path)
                final_image_path = os.path.join(linkedin_images_folder, image_filename)
                if image_path != final_image_path:
                    shutil.copy2(image_path, final_image_path)
                final_image_path = os.path.abspath(final_image_path)
                print(f"✅ Image ready at: {final_image_path}")
            
            todos = [
                "Open a new browser tab",
                "Type 'linkedin.com/feed' in the address bar and press Enter",
                "Wait 5 seconds for LinkedIn to fully load",
                "Look for the text box that says 'Start a post' or the button with 'Start a post' text",
                "Click on 'Start a post' - this will open the post composer modal/editor",
                "Wait 5 seconds for the post editor modal to fully appear and be ready",
                "Look for the large text area inside the post editor modal - it should be a text input box",
                "Click directly inside this text area to focus it - make sure the cursor is blinking inside the text box",
                "Wait 2 seconds to ensure the text area is focused and ready for input",
                "Now paste the text using Cmd+V (Mac) or Ctrl+V (Windows) - the text is already in your clipboard",
                "Wait 3 seconds to verify the pasted text appears in the text area - you should see the text content displayed"
            ]
            
            # Add image upload if provided - but STOP after upload (don't click Post)
            if final_image_path and os.path.exists(final_image_path):
                todos.extend([
                    "Look for the 'Add media' button in the post editor - it might be an icon with a picture or say 'Add media' or 'Photo'",
                    "Click the 'Add media' button - this will open the file upload dialog",
                    "Wait 3 seconds for the file upload dialog to fully open",
                    f"In the file dialog, navigate to this exact folder: {linkedin_images_folder}",
                    f"Look for and select the image file named: {os.path.basename(final_image_path)}",
                    "Click the 'Open' button in the file dialog to upload the image",
                    "Wait 8 seconds for the image to upload completely and appear in the post preview area",
                    "Verify the image is now visible in the post editor preview - you should see the image displayed",
                    "STOP IMMEDIATELY - Do NOT click the Post button. The draft is complete and ready for manual review."
                ])
            else:
                todos.append("STOP IMMEDIATELY - Do NOT click the Post button. The draft is complete and ready for manual review.")
            
            agent.set_task(
                task="Create LinkedIn post: open tab, paste text, upload image, STOP",
                todos=todos
            )
            
            # Detailed instruction with clear steps
            image_filename_str = os.path.basename(final_image_path) if final_image_path else None
            
            instruction_text = f"""Create a LinkedIn post draft by following these EXACT steps in order:

STEP 1: Open LinkedIn
- Open a new browser tab
- Type 'linkedin.com/feed' in the address bar
- Press Enter
- Wait 5 seconds for the page to fully load

STEP 2: Open Post Composer
- Look for the text box that says 'Start a post' or find the button with 'Start a post' text
- Click on 'Start a post' - this will open the post composer modal/editor
- Wait 5 seconds for the post editor modal to fully appear and be ready

STEP 3: Paste Text Content
- Find the large text input area inside the post editor modal - it's the main text box where you type posts
- Click directly inside this text area to focus it - make sure the cursor is blinking inside the text box
- Wait 2 seconds to ensure the text area is focused and ready for input
- Press Cmd+V (Mac) or Ctrl+V (Windows) to paste the text from clipboard
- Wait 3 seconds and verify the pasted text appears in the text area - you should see the text content displayed

{f'''STEP 4: Upload Image
- Look for the 'Add media' button in the post editor - it might be an icon with a picture or say 'Add media' or 'Photo'
- Click the 'Add media' button - this will open the file upload dialog
- Wait 3 seconds for the file upload dialog to fully open
- In the file dialog, navigate to this exact folder path: {linkedin_images_folder}
- Look for and select the image file named: {image_filename_str}
- Click the 'Open' button in the file dialog to upload the image
- Wait 10 seconds for the image to upload completely and appear in the post preview area
- Verify the image is now visible in the post editor preview - you should see the image displayed below the text
- STOP IMMEDIATELY - Do NOT click the Post button. The draft is complete and ready for manual review.''' if final_image_path else 'STEP 4: STOP IMMEDIATELY - Do NOT click the Post button. The draft is complete and ready for manual review.'}

CRITICAL REMINDERS:
- The text content is already copied to your clipboard - just paste it (Cmd+V or Ctrl+V)
- After pasting text, wait to see it appear in the text area
{f'- After uploading image, wait to see it appear in the preview - then STOP' if final_image_path else ''}
- Do NOT click the Post button - stop immediately after text is pasted{f' and image is uploaded' if final_image_path else ''}
"""
            
            # Store task reference BEFORE creating it for proper cancellation
            self.current_task = asyncio.create_task(
                agent.execute(
                    instruction=instruction_text,
                    action_handler=AsyncPyautoguiActionHandler(),
                    image_provider=AsyncScreenshotMaker(),
                )
            )
            
            # Run with timeout and stop flag checking
            try:
                # Check stop flag periodically while waiting
                while not self.current_task.done() and not _stop_flag.is_set():
                    try:
                        # Wait for task with short timeout to check stop flag
                        done, pending = await asyncio.wait(
                            [self.current_task],
                            timeout=1.0,
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        if self.current_task.done():
                            break
                    except asyncio.TimeoutError:
                        # Continue loop to check stop flag
                        continue
                
                # Check if stopped
                if _stop_flag.is_set():
                    if not self.current_task.done():
                        self.current_task.cancel()
                        try:
                            # Don't wait - just cancel immediately
                            pass
                        except:
                            pass
                    self.current_task = None
                    return {"success": False, "error": "Operation stopped by user"}
                
                # Task completed normally
                if self.current_task.done():
                    try:
                        await self.current_task
                    except asyncio.CancelledError:
                        return {"success": False, "error": "Operation cancelled"}
                else:
                    # Timeout - cancel it
                    self.current_task.cancel()
                    return {"success": False, "error": "Operation timed out"}
                    
            except asyncio.CancelledError:
                self.current_task = None
                return {"success": False, "error": "Operation cancelled"}
            except Exception as e:
                self.current_task = None
                if _stop_flag.is_set():
                    return {"success": False, "error": "Operation stopped by user"}
                raise
            
            return {
                "success": True, 
                "post_url": "Draft ready",
                "post_id": "draft",
                "message": "Post draft created successfully! Review and post manually on LinkedIn."
            }
        except asyncio.CancelledError:
            return {"success": False, "error": "Operation cancelled"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def create_and_publish_linkedin_post(self, content: str, image_path: Optional[str] = None) -> Dict:
        """Create LinkedIn post draft (user posts manually) - synchronous wrapper"""
        return self._run_async(self._create_and_publish_post_async(content, image_path))
    
    async def _publish_post_async(self) -> Dict:
        """Publish the LinkedIn post"""
        try:
            agent = AsyncDefaultAgent(model="lux-actor-1")
            
            await agent.execute(
                instruction="Click the 'Post' button to publish the LinkedIn post that is currently in draft. The post text box should be visible with content.",
                action_handler=AsyncPyautoguiActionHandler(),
                image_provider=AsyncScreenshotMaker(),
            )
            
            # Wait a bit for post to be published
            await asyncio.sleep(3)
            
            return {
                "success": True, 
                "post_url": "Posted successfully",
                "post_id": "posted"
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def publish_post(self) -> Dict:
        """Publish post - synchronous wrapper"""
        return self._run_async(self._publish_post_async())
    
    def read_apple_notes(self, note_title: Optional[str] = None) -> Dict:
        """
        Read Apple Notes using AGI Open
        Note: This is complex - would need clipboard extraction
        """
        return {
            "success": False,
            "content": "",
            "error": "Apple Notes reading via OAGI requires additional clipboard handling. Please use 'Plain Text' option for now."
        }
    
    def read_google_docs(self, doc_url: Optional[str] = None, doc_name: Optional[str] = None) -> Dict:
        """
        Read Google Docs using AGI Open
        """
        if not doc_url:
            return {
                "success": False,
                "content": "",
                "error": "Please provide a Google Docs URL to read the document. Use 'Plain Text' option for manual input."
            }
        
        # Could implement this with OAGI if needed
        return {
            "success": False,
            "content": "",
            "error": "Google Docs reading via OAGI is not yet implemented. Please use 'Plain Text' option."
        }
    
    async def _reply_to_comments_async(self, post_url: str, replies: List[Dict]) -> Dict:
        """Automate replying to comments on a LinkedIn post"""
        global _stop_flag, _current_task_ref
        _stop_flag.clear()
        _current_task_ref = None
        
        try:
            agent = TaskerAgent(model="lux-actor-1")
            
            todos = [
                f"Navigate to {post_url} in the browser",
                "Wait 5 seconds for the post to load",
                "Scroll down to find the comments section",
                "Click on 'Comments' or expand the comments section"
            ]
            
            # For each comment reply
            for i, reply_data in enumerate(replies[:5]):  # Limit to 5 comments
                comment_text = reply_data.get('comment_text', '')[:50]
                reply_text = reply_data.get('reply_text', '')
                
                todos.extend([
                    f"Find the comment that contains: {comment_text}",
                    "Click the 'Reply' button under that comment",
                    "Wait 2 seconds for the reply box to appear",
                    f"Type the following reply: {reply_text}",
                    "Click 'Post reply' or 'Reply' button",
                    "Wait 3 seconds for the reply to be posted"
                ])
            
            agent.set_task(
                task="Reply to comments on a LinkedIn post",
                todos=todos
            )
            
            task = agent.execute(
                instruction=f"Navigate to the LinkedIn post and reply to comments with the provided replies. Stop after all replies are posted.",
                action_handler=AsyncPyautoguiActionHandler(),
                image_provider=AsyncScreenshotMaker(),
            )
            
            self.current_task = task
            _current_task_ref = task
            
            done, pending = await asyncio.wait(
                [task],
                timeout=300.0,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            if _stop_flag.is_set():
                if not task.done():
                    task.cancel()
                return {"success": False, "error": "Operation stopped by user"}
            
            if task.done():
                try:
                    await task
                except asyncio.CancelledError:
                    return {"success": False, "error": "Operation cancelled"}
            
            return {
                "success": True,
                "replies_sent": len(replies)
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        finally:
            self.current_task = None
            _current_task_ref = None
    
    def reply_to_comments_automated(self, post_url: str, replies: List[Dict]) -> Dict:
        """Reply to comments - synchronous wrapper"""
        return self._run_async(self._reply_to_comments_async(post_url, replies))
    
    def get_post_comments(self, post_url: str) -> Dict:
        """Get all comments on a specific post - placeholder"""
        return {
            "success": False,
            "comments": [],
            "error": "Comment extraction not yet implemented with OAGI SDK"
        }
    
    def reply_to_comment(self, post_url: str, comment_text: str, reply_text: str) -> Dict:
        """Reply to a specific comment - placeholder"""
        return {
            "success": False,
            "error": "Use reply_to_comments_automated for batch replies"
        }
    
    def message_user(self, profile_url: str, message: str) -> Dict:
        """Send a message to a LinkedIn user - placeholder"""
        return {
            "success": False,
            "error": "Messaging not yet implemented with OAGI SDK"
        }
    
    def get_post_likers(self, post_url: str) -> Dict:
        """Get list of people who liked a post - placeholder"""
        return {
            "success": False,
            "likers": [],
            "error": "Likers extraction not yet implemented with OAGI SDK"
        }
