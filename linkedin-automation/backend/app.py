from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import config
from services.agiopen_client import AGIOpenClient
from services.openai_client import OpenAIClient
from services.image_generator import ImageGenerator
from database import Session, PostHistory, CommentHistory, MessageHistory
import os
import uuid

app = Flask(__name__)

# Configure CORS - More permissive for development
# Allows all origins in development (for production, restrict to specific origins)
def is_allowed_origin(origin):
    """Check if origin is allowed (allows localhost, 127.0.0.1, and local network IPs)"""
    if not origin:
        return False
    
    # Allow localhost and 127.0.0.1
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        return True
    
    # Allow local network IPs (common private IP ranges)
    if origin.startswith("http://192.168.") or origin.startswith("http://172.") or origin.startswith("http://10."):
        return True
    
    # Check explicit list
    return origin in config.ALLOWED_ORIGINS

# For development: allow all origins
CORS(app, 
     origins="*",  # Allow all origins in development
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    # Allow all origins for development
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

# Initialize services
agi_client = AGIOpenClient()
openai_client = OpenAIClient()
image_gen = ImageGenerator()

# Store workflow states (in production, use Redis)
workflow_states = {}
active_tasks = {}  # Track active OAGI tasks for cancellation

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    return jsonify({"status": "healthy", "cors": "enabled"})

@app.route('/api/stop-automation', methods=['POST', 'OPTIONS'])
def stop_automation():
    """
    Stop the current automation process immediately
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Always stop the current OAGI task, regardless of workflow_id
        agi_client.stop_current_task()
        
        data = request.json or {}
        workflow_id = data.get('workflow_id')
        
        # Clean up workflow state if provided
        if workflow_id and workflow_id in workflow_states:
            workflow_states[workflow_id]["status"] = "cancelled"
            if workflow_id in active_tasks:
                del active_tasks[workflow_id]
        
        # Also cancel all active tasks
        for task_id in list(active_tasks.keys()):
            if task_id in active_tasks:
                del active_tasks[task_id]
        
        return jsonify({
            "success": True,
            "message": "Automation stopped successfully. OAGI agent will release control of your screen."
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/read-source', methods=['POST', 'OPTIONS'])
def read_source():
    """
    Read content from selected source (Apple Notes, Google Docs, or plain text)
    """
    if request.method == 'OPTIONS':
        # Handle preflight request
        return jsonify({}), 200
    
    try:
        data = request.json or {}
        source_type = data.get('source_type')  # 'macbook-notes', 'google-docs', 'plain-text'
        source_data = data.get('source_data') or {}  # For Google Docs: URL or name, for Notes: note title, for plain: text
        
        if not source_type:
            return jsonify({"success": False, "error": "source_type is required"}), 400
        
        if source_type == 'photo-capture':
            # Photo capture is handled via upload-photo endpoint
            return jsonify({
                "success": False,
                "error": "Photo capture should use the upload-photo endpoint first"
            }), 400
        
        elif source_type == 'macbook-notes':
            result = agi_client.read_apple_notes(note_title=source_data.get('note_title'))
        
        elif source_type == 'google-docs':
            result = agi_client.read_google_docs(
                doc_url=source_data.get('doc_url'),
                doc_name=source_data.get('doc_name')
            )
        
        elif source_type == 'plain-text':
            result = {
                "success": True,
                "content": source_data.get('text', '')
            }
        
        else:
            return jsonify({"success": False, "error": "Invalid source type"}), 400
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({"success": False, "error": error_msg}), 500

@app.route('/api/upload-photo', methods=['POST', 'OPTIONS'])
def upload_photo():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    """
    Upload photo from photo capture feature
    """
    try:
        if 'photo' not in request.files:
            return jsonify({"success": False, "error": "No photo file provided"}), 400
        
        photo_file = request.files['photo']
        notes = request.form.get('notes', '')
        
        if photo_file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        # Save photo to uploads folder
        uploads_folder = os.path.join("images", "uploads")
        os.makedirs(uploads_folder, exist_ok=True)
        
        # Get file extension
        file_ext = os.path.splitext(photo_file.filename)[1] or '.jpg'
        photo_filename = f"photo_{uuid.uuid4().hex[:8]}{file_ext}"
        photo_path = os.path.join(uploads_folder, photo_filename)
        photo_file.save(photo_path)
        
        # Return full URL path
        photo_url = f"http://localhost:5001/api/images/uploads/{photo_filename}"
        
        return jsonify({
            "success": True,
            "photo_url": photo_url,
            "photo_path": os.path.abspath(photo_path),
            "notes": notes
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/images/uploads/<filename>', methods=['GET'])
def serve_uploaded_image(filename):
    """Serve uploaded images"""
    uploads_folder = os.path.join("images", "uploads")
    return send_from_directory(uploads_folder, filename)

@app.route('/api/generate-content', methods=['POST', 'OPTIONS'])
def generate_content():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    """
    Generate LinkedIn content (post/comment/message) from source content
    """
    data = request.json
    source_content = data.get('source_content')
    action_type = data.get('action_type')  # 'post', 'comment', 'messages'
    context = data.get('context', '')
    photo_url = data.get('photo_url')  # For photo capture
    source_type = data.get('source_type', 'plain-text')
    
    try:
        if action_type == 'post':
            # If we have a photo, use it instead of generating a new image
            if photo_url and source_type == 'photo-capture':
                # Use the uploaded photo as the post image
                # Generate post content based on photo + notes
                enhanced_context = f"User uploaded a photo and wrote these notes: {source_content}. Create a LinkedIn post that describes the photo and incorporates the notes."
                result = openai_client.generate_linkedin_post(enhanced_context, context)
                
                if result.get("success"):
                    # Extract filename from photo_url and find the actual file
                    # photo_url format: http://localhost:5001/api/images/uploads/photo_xxx.jpg
                    filename = photo_url.split('/')[-1]
                    uploads_folder = os.path.join("images", "uploads")
                    photo_path_abs = os.path.abspath(os.path.join(uploads_folder, filename))
                    
                    if os.path.exists(photo_path_abs):
                        # Copy to linkedin_posts folder for automation
                        linkedin_posts_folder = os.path.join("images", "linkedin_posts")
                        os.makedirs(linkedin_posts_folder, exist_ok=True)
                        linkedin_photo_path = os.path.join(linkedin_posts_folder, filename)
                        import shutil
                        shutil.copy2(photo_path_abs, linkedin_photo_path)
                        
                        result["image_path"] = os.path.abspath(linkedin_photo_path)
                        result["image_url"] = photo_url
                    else:
                        # Fallback: generate image from description
                        image_desc = result.get("image_description", "")
                        image_result = image_gen.generate_post_image(image_desc, f"post_{uuid.uuid4().hex[:8]}.png")
                        if image_result.get("success"):
                            result["image_path"] = image_result["image_path"]
                            result["image_url"] = image_result["image_url"]
                    
                    return jsonify(result)
                else:
                    return jsonify(result), 500
            else:
                # Normal flow: generate content and image
                result = openai_client.generate_linkedin_post(source_content, context)
                
                if result.get("success"):
                    # Generate image
                    image_desc = result.get("image_description", "")
                    image_result = image_gen.generate_post_image(image_desc, f"post_{uuid.uuid4().hex[:8]}.png")
                    
                    if image_result.get("success"):
                        result["image_path"] = image_result["image_path"]
                        result["image_url"] = image_result["image_url"]
                    
                    return jsonify(result)
                else:
                    return jsonify(result), 500
        
        elif action_type == 'comment':
            # For comments, we'd need the original comment
            comment_text = data.get('comment_text', '')
            reply = openai_client.generate_linkedin_comment(comment_text, context)
            return jsonify({"success": True, "reply": reply})
        
        elif action_type == 'messages':
            recipient_context = data.get('recipient_context', '')
            trigger_context = data.get('trigger_context', 'post_like')
            message = openai_client.generate_linkedin_message(recipient_context, trigger_context)
            return jsonify({"success": True, "message": message})
        
        return jsonify({"success": False, "error": "Invalid action type"}), 400
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/create-post-draft', methods=['POST'])
def create_post_draft():
    """
    Create LinkedIn post draft (not published yet) - DEPRECATED, use create-and-publish-post
    """
    data = request.json
    post_content = data.get('post_content')
    image_path = data.get('image_path')
    
    try:
        result = agi_client.create_linkedin_post(post_content, image_path)
        
        workflow_id = str(uuid.uuid4())
        workflow_states[workflow_id] = {
            "post_content": post_content,
            "image_path": image_path,
            "status": "draft"
        }
        
        return jsonify({
            "success": result.get("success", False),
            "workflow_id": workflow_id,
            "preview_screenshot": result.get("screenshot")
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/create-and-publish-post', methods=['POST'])
def create_and_publish_post():
    """
    Create and publish LinkedIn post in one go - fully automated
    """
    data = request.json
    post_content = data.get('post_content')  # The exact content from frontend
    image_url_or_path = data.get('image_path')  # Could be URL or local path
    
    try:
        # Step 1: Handle image - could be URL or local file path
        image_path = None
        if image_url_or_path:
            # Check if it's a URL (starts with http) or a local path
            if image_url_or_path.startswith('http://') or image_url_or_path.startswith('https://'):
                # It's a URL - download it
                import requests
                os.makedirs("images", exist_ok=True)
                image_filename = f"post_image_{uuid.uuid4().hex[:8]}.png"
                
                # Ensure linkedin_posts subfolder exists
                linkedin_posts_folder = os.path.join("images", "linkedin_posts")
                os.makedirs(linkedin_posts_folder, exist_ok=True)
                
                # Download the image
                print(f"📥 Downloading image from: {image_url_or_path}")
                img_response = requests.get(image_url_or_path, timeout=30)
                img_response.raise_for_status()
                
                # Save to linkedin_posts folder
                linkedin_image_path = os.path.join(linkedin_posts_folder, image_filename)
                with open(linkedin_image_path, 'wb') as f:
                    f.write(img_response.content)
                
                image_path = os.path.abspath(linkedin_image_path)
                print(f"✅ Image downloaded to: {image_path}")
            else:
                # It's a local path - check if it exists
                if os.path.exists(image_url_or_path):
                    # Ensure it's in the linkedin_posts folder
                    linkedin_posts_folder = os.path.join("images", "linkedin_posts")
                    os.makedirs(linkedin_posts_folder, exist_ok=True)
                    
                    # Copy to linkedin_posts folder if not already there
                    filename = os.path.basename(image_url_or_path)
                    linkedin_image_path = os.path.join(linkedin_posts_folder, filename)
                    
                    if image_url_or_path != linkedin_image_path:
                        import shutil
                        shutil.copy2(image_url_or_path, linkedin_image_path)
                    
                    image_path = os.path.abspath(linkedin_image_path)
                    print(f"✅ Image ready at: {image_path}")
                else:
                    print(f"⚠️ Image path does not exist: {image_url_or_path}")
        
        # Step 2: Ensure we have content
        if not post_content:
            return jsonify({"success": False, "error": "Post content is required"}), 400
        
        print(f"📝 Post content length: {len(post_content)} characters")
        print(f"📝 Post content preview: {post_content[:100]}...")
        
        # Step 3: Create and publish post using OAGI
        print(f"🚀 Starting LinkedIn automation...")
        result = agi_client.create_and_publish_linkedin_post(post_content, image_path)
        
        if result.get("success"):
            # Save to database as draft
            session = Session()
            post_record = PostHistory(
                post_id=result.get("post_id", f"draft_{uuid.uuid4().hex[:8]}"),
                content=post_content,
                image_url=image_url or "",
                linkedin_url=result.get("post_url", "Draft ready"),
                source_type="automated",
                engagement_count=0
            )
            session.add(post_record)
            session.commit()
            post_id = post_record.id
            session.close()
            
            return jsonify({
                "success": True,
                "post_url": result.get("post_url", "Draft ready"),
                "post_id": result.get("post_id", "draft"),
                "message": result.get("message", "Post draft created successfully! Review and post manually on LinkedIn."),
                "record_id": post_id
            })
        else:
            return jsonify({
                "success": False, 
                "error": result.get("error", "Failed to publish post")
            }), 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/publish-post', methods=['POST'])
def publish_post():
    """
    Publish the draft post on LinkedIn
    """
    data = request.json
    workflow_id = data.get('workflow_id')
    
    if workflow_id not in workflow_states:
        return jsonify({"success": False, "error": "Workflow not found"}), 404
    
    try:
        # Publish the post
        result = agi_client.publish_post()
        
        if result.get("success"):
            # Save to database
            session = Session()
            workflow = workflow_states[workflow_id]
            
            post_record = PostHistory(
                post_id=result.get("post_id", ""),
                content=workflow["post_content"],
                image_url=workflow.get("image_path", ""),
                linkedin_url=result.get("post_url", ""),
                source_type="unknown"
            )
            session.add(post_record)
            session.commit()
            session.close()
            
            workflow_states[workflow_id]["status"] = "published"
            workflow_states[workflow_id]["post_url"] = result.get("post_url")
            
            return jsonify({
                "success": True,
                "post_url": result.get("post_url"),
                "post_id": result.get("post_id")
            })
        else:
            return jsonify({"success": False, "error": "Failed to publish"}), 500
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-post-comments', methods=['POST'])
def get_post_comments():
    """
    Get all comments on a specific post
    """
    data = request.json
    post_url = data.get('post_url')
    
    try:
        result = agi_client.get_post_comments(post_url)
        
        if result.get("success"):
            # Generate replies for each comment
            comments = result.get("comments", [])
            replies = []
            
            for comment in comments:
                reply_text = openai_client.generate_linkedin_comment(
                    comment.get("text", ""),
                    post_url
                )
                replies.append({
                    "original_comment": comment,
                    "reply": reply_text
                })
            
            return jsonify({
                "success": True,
                "comments": comments,
                "suggested_replies": replies
            })
        
        return jsonify(result), 500
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/reply-to-comments', methods=['POST'])
def reply_to_comments():
    """
    Reply to comments on a post
    """
    data = request.json
    post_url = data.get('post_url')
    comments_to_reply = data.get('comments', [])  # List of {comment_text, reply_text}
    
    try:
        session = Session()
        results = []
        
        for item in comments_to_reply:
            result = agi_client.reply_to_comment(
                post_url,
                item['comment_text'],
                item['reply_text']
            )
            
            if result.get("success"):
                # Save to database
                comment_record = CommentHistory(
                    post_id=post_url.split("/")[-1],
                    commenter_name=item.get('commenter_name', 'Unknown'),
                    comment_text=item['comment_text'],
                    reply_sent=item['reply_text']
                )
                session.add(comment_record)
            
            results.append(result)
        
        session.commit()
        session.close()
        
        return jsonify({
            "success": True,
            "replies_sent": len([r for r in results if r.get("success")]),
            "results": results
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/message-likers', methods=['POST'])
def message_likers():
    """
    Get post likers and send them messages
    """
    data = request.json
    post_url = data.get('post_url')
    
    try:
        # Get likers
        likers_result = agi_client.get_post_likers(post_url)
        
        if not likers_result.get("success"):
            return jsonify(likers_result), 500
        
        likers = likers_result.get("likers", [])[:10]  # Limit to 10
        
        session = Session()
        results = []
        
        for liker in likers:
            # Generate personalized message
            message = openai_client.generate_linkedin_message(
                f"User: {liker.get('name', 'Unknown')}",
                "post_like"
            )
            
            # Send message
            result = agi_client.message_user(
                liker.get("profile_url", ""),
                message
            )
            
            if result.get("success"):
                # Save to database
                message_record = MessageHistory(
                    recipient_profile=liker.get("profile_url", ""),
                    message_text=message,
                    context="post_like"
                )
                session.add(message_record)
            
            results.append({
                "liker": liker,
                "message_sent": result.get("success", False)
            })
        
        session.commit()
        session.close()
        
        return jsonify({
            "success": True,
            "messages_sent": len([r for r in results if r["message_sent"]]),
            "results": results
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """
    Get user's activity history
    """
    try:
        session = Session()
        
        posts = session.query(PostHistory).order_by(
            PostHistory.created_at.desc()
        ).limit(20).all()
        
        comments = session.query(CommentHistory).order_by(
            CommentHistory.created_at.desc()
        ).limit(50).all()
        
        messages = session.query(MessageHistory).order_by(
            MessageHistory.sent_at.desc()
        ).limit(30).all()
        
        session.close()
        
        return jsonify({
            "posts": [{
                "id": p.post_id,
                "content": p.content[:100] + "..." if len(p.content) > 100 else p.content,
                "url": p.linkedin_url,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "engagement_count": p.engagement_count
            } for p in posts],
            "comments": [{
                "post_id": c.post_id,
                "commenter": c.commenter_name,
                "reply": c.reply_sent[:100] + "..." if len(c.reply_sent) > 100 else c.reply_sent,
                "created_at": c.created_at.isoformat() if c.created_at else None
            } for c in comments],
            "messages": [{
                "recipient": m.recipient_profile,
                "context": m.context,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None
            } for m in messages]
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Create images directory if it doesn't exist
    os.makedirs("images", exist_ok=True)
    app.run(port=config.FLASK_PORT, debug=True)

