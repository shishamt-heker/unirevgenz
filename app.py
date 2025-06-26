from flask import Flask, render_template_string, request, redirect, url_for, jsonify
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient
from bson import ObjectId
from urllib.parse import quote_plus
from flask import Flask, send_from_directory
from waitress import serve

app = Flask(__name__)

# MongoDB connection
# Encode username and password
username = quote_plus("shishamt6")
password = quote_plus("Shishamt6@7894")
# Updated MongoDB connection string (using your original working connection)
client = MongoClient(f"mongodb+srv://{username}:{password}@cluster0.vxvov1y.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
# Connect to the database and collection
db = client['revision_app']
tasks_collection = db['tasks']

# Initialize MongoDB connection
try:
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    client = None

# Spaced repetition intervals (in days)
REVISION_INTERVALS = [1, 3, 7, 14, 20]

def get_tasks_collection():
    """Get the tasks collection"""
    if client is None:
        raise Exception("MongoDB connection not available")
    return tasks_collection

def load_tasks():
    """Load tasks from MongoDB"""
    try:
        collection = get_tasks_collection()
        tasks = list(collection.find({}))
        # Convert ObjectId to string for JSON serialization
        for task in tasks:
            task['_id'] = str(task['_id'])
        return tasks
    except Exception as e:
        print(f"Error loading tasks: {e}")
        return []

def save_task(task):
    """Save a single task to MongoDB"""
    try:
        collection = get_tasks_collection()
        if '_id' in task and task['_id']:
            # Update existing task
            task_id = ObjectId(task['_id']) if isinstance(task['_id'], str) else task['_id']
            task_copy = task.copy()
            del task_copy['_id']  # Remove _id from update data
            result = collection.update_one({'_id': task_id}, {'$set': task_copy})
            return result.modified_count > 0
        else:
            # Insert new task
            if '_id' in task:
                del task['_id']  # Remove _id if present for new tasks
            result = collection.insert_one(task)
            return result.inserted_id is not None
    except Exception as e:
        print(f"Error saving task: {e}")
        return False

def delete_task_from_db(task_id):
    """Delete a task from MongoDB"""
    try:
        collection = get_tasks_collection()
        object_id = ObjectId(task_id) if isinstance(task_id, str) else task_id
        result = collection.delete_one({'_id': object_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting task: {e}")
        return False

def get_next_review_date(current_cycle):
    """Calculate next review date based on current cycle"""
    if current_cycle < len(REVISION_INTERVALS):
        days_to_add = REVISION_INTERVALS[current_cycle]
    else:
        # After completing the cycle, repeat every 20 days
        days_to_add = 20
    
    return (datetime.now() + timedelta(days=days_to_add)).isoformat()

def get_available_tasks():
    """Get tasks that are due for review"""
    tasks = load_tasks()
    available_tasks = []
    current_time = datetime.now()
    
    for task in tasks:
        if task['status'] == 'pending':
            review_date = datetime.fromisoformat(task['next_review'])
            if current_time >= review_date:
                available_tasks.append(task)
    
    return available_tasks

def get_next_task_id():
    """Get the next available task ID"""
    try:
        collection = get_tasks_collection()
        # Find the task with the highest task_id
        last_task = collection.find().sort("task_id", -1).limit(1)
        last_task_list = list(last_task)
        if last_task_list:
            return last_task_list[0]['task_id'] + 1
        else:
            return 1
    except Exception as e:
        print(f"Error getting next task ID: {e}")
        return 1

@app.route('/')
def index():
    """Main page showing available tasks"""
    available_tasks = get_available_tasks()
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UnirevGen-Z</title>
        <link rel="icon" href="favicon.ico" type="image/x-icon">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f7fa;
                color: #333;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #555;
            }
            input[type="text"], textarea {
                width: 100%;
                padding: 12px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 16px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            input[type="text"]:focus, textarea:focus {
                outline: none;
                border-color: #667eea;
            }
            textarea {
                resize: vertical;
                min-height: 80px;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
            .btn-success {
                background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
            }
            .btn-success:hover {
                box-shadow: 0 4px 12px rgba(86, 171, 47, 0.4);
            }
            .btn-danger {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                margin-left: 10px;
            }
            .btn-danger:hover {
                box-shadow: 0 4px 12px rgba(255, 107, 107, 0.4);
            }
            .task-item {
                background: #f8f9fa;
                padding: 20px;
                border-left: 4px solid #667eea;
                margin-bottom: 15px;
                border-radius: 0 8px 8px 0;
                transition: transform 0.2s;
            }
            .task-item:hover {
                transform: translateX(5px);
            }
            .task-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .task-title {
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin: 0;
            }
            .task-cycle {
                background: #667eea;
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }
            .task-description {
                color: #666;
                margin-bottom: 15px;
                line-height: 1.5;
            }
            .task-dates {
                font-size: 14px;
                color: #888;
                margin-bottom: 15px;
            }
            .task-actions {
                display: flex;
                align-items: center;
            }
            .no-tasks {
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 40px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 2px dashed #ddd;
            }
            .stats {
                display: flex;
                justify-content: space-around;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .stat-item {
                text-align: center;
            }
            .stat-number {
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                font-size: 14px;
                color: #666;
                margin-top: 5px;
            }
            .intervals-info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #2196f3;
            }
            .intervals-info h4 {
                margin: 0 0 10px 0;
                color: #1976d2;
            }
            .intervals-info p {
                margin: 0;
                color: #666;
                font-size: 14px;
            }
            .mongodb-status {
                background: #d4edda;
                color: #155724;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #c3e6cb;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📚 Student Revision To-Do</h1>
            <p>Spaced Repetition Learning System</p>
        </div>

        <div class="mongodb-status">
            🌐 Connected to MongoDB Cloud Database
        </div>

        <div class="intervals-info">
            <h4>📅 How it works:</h4>
            <p>Tasks reappear for review after: <strong>1, 3, 7, 14, 20 days</strong>, then every <strong>20 days</strong> thereafter. This spaced repetition helps improve long-term retention!</p>
        </div>

        {% set all_tasks = get_all_tasks() %}
        {% set total_tasks = all_tasks|length %}
        {% set available_count = available_tasks|length %}
        {% set pending_count = all_tasks|selectattr('status', 'equalto', 'pending')|list|length %}

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{{ total_tasks }}</div>
                <div class="stat-label">Total Concepts</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ available_count }}</div>
                <div class="stat-label">Due for Review</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ pending_count - available_count }}</div>
                <div class="stat-label">Scheduled Later</div>
            </div>
        </div>

        <div class="container">
            <h2>➕ Add New Concept</h2>
            <form action="/add_task" method="post">
                <div class="form-group">
                    <label for="title">Concept Title:</label>
                    <input type="text" id="title" name="title" required placeholder="e.g., Python Lists and Dictionaries">
                </div>
                <div class="form-group">
                    <label for="description">Description (optional):</label>
                    <textarea id="description" name="description" placeholder="Key points to remember, examples, or notes..."></textarea>
                </div>
                <button type="submit" class="btn">Add Concept</button>
            </form>
        </div>

        <div class="container">
            <h2>📋 Concepts Due for Review ({{ available_count }})</h2>
            {% if available_tasks %}
                {% for task in available_tasks %}
                <div class="task-item">
                    <div class="task-header">
                        <h3 class="task-title">{{ task.title }}</h3>
                        <span class="task-cycle">Review #{{ task.current_cycle + 1 }}</span>
                    </div>
                    {% if task.description %}
                    <div class="task-description">{{ task.description }}</div>
                    {% endif %}
                    <div class="task-dates">
                        <strong>Created:</strong> {{ task.created_at[:10] }} | 
                        <strong>Last Reviewed:</strong> {{ task.last_completed[:10] if task.last_completed else 'Never' }}
                    </div>
                    <div class="task-actions">
                        <form action="/complete_task/{{ task._id }}" method="post" style="display: inline;">
                            <button type="submit" class="btn btn-success">✅ Mark as Reviewed</button>
                        </form>
                        <form action="/delete_task/{{ task._id }}" method="post" style="display: inline;" 
                              onsubmit="return confirm('Are you sure you want to delete this concept?')">
                            <button type="submit" class="btn btn-danger">🗑️ Delete</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-tasks">
                    🎉 No concepts due for review right now!<br>
                    Add new concepts above or check back later.
                </div>
            {% endif %}
        </div>

        <div class="container">
            <h2>📊 All Concepts Status</h2>
            <p><a href="/all_tasks" style="color: #667eea; text-decoration: none;">View all concepts and their schedules →</a></p>
        </div>
    </body>
    </html>
    """
    
    def get_all_tasks():
        return load_tasks()
    
    return render_template_string(html_template, 
                                available_tasks=available_tasks,
                                get_all_tasks=get_all_tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    """Add a new task"""
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if not title:
        return redirect(url_for('index'))
    
    # Generate unique task ID
    task_id = get_next_task_id()
    
    new_task = {
        'task_id': task_id,  # Custom numeric ID for compatibility
        'title': title,
        'description': description,
        'status': 'pending',
        'current_cycle': 0,
        'created_at': datetime.now().isoformat(),
        'last_completed': None,
        'next_review': datetime.now().isoformat()  # Available immediately
    }
    
    success = save_task(new_task)
    if not success:
        print("Failed to save task to MongoDB")
    
    return redirect(url_for('index'))

@app.route('/complete_task/<task_id>', methods=['POST'])
def complete_task(task_id):
    """Mark a task as completed and schedule next review"""
    tasks = load_tasks()
    
    for task in tasks:
        if task['_id'] == task_id:
            task['last_completed'] = datetime.now().isoformat()
            task['current_cycle'] += 1
            task['next_review'] = get_next_review_date(task['current_cycle'])
            save_task(task)
            break
    
    return redirect(url_for('index'))

@app.route('/all_tasks')
def all_tasks():
    """Show all tasks with their status"""
    tasks = load_tasks()
    current_time = datetime.now()
    
    # Categorize tasks
    available_tasks = []
    scheduled_tasks = []
    
    for task in tasks:
        if task['status'] == 'pending':
            review_date = datetime.fromisoformat(task['next_review'])
            if current_time >= review_date:
                available_tasks.append(task)
            else:
                task['days_until_review'] = (review_date - current_time).days
                scheduled_tasks.append(task)
    
    # Sort scheduled tasks by next review date
    scheduled_tasks.sort(key=lambda x: x['next_review'])
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UnirevGen-Z</title>
        <link rel="icon" href="favicon.ico" type="image/x-icon">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f7fa;
                color: #333;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }
            .back-link:hover {
                text-decoration: underline;
            }
            .task-item {
                background: #f8f9fa;
                padding: 20px;
                border-left: 4px solid #667eea;
                margin-bottom: 15px;
                border-radius: 0 8px 8px 0;
            }
            .available {
                border-left-color: #28a745;
            }
            .scheduled {
                border-left-color: #ffc107;
            }
            .task-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .task-title {
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin: 0;
            }
            .task-cycle {
                background: #667eea;
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }
            .available .task-cycle {
                background: #28a745;
            }
            .scheduled .task-cycle {
                background: #ffc107;
                color: #333;
            }
            .task-description {
                color: #666;
                margin-bottom: 15px;
                line-height: 1.5;
            }
            .task-dates {
                font-size: 14px;
                color: #888;
                margin-bottom: 15px;
            }
            .next-review {
                font-weight: 600;
                color: #667eea;
            }
            .available .next-review {
                color: #28a745;
            }
            .task-actions {
                display: flex;
                gap: 10px;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                text-decoration: none;
                display: inline-block;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
            }
            .btn-danger {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            }
            .btn-danger:hover {
                box-shadow: 0 4px 8px rgba(255, 107, 107, 0.4);
            }
            .no-tasks {
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 40px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 2px dashed #ddd;
            }
            .mongodb-status {
                background: #d4edda;
                color: #155724;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #c3e6cb;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📚 All Concepts Overview</h1>
        </div>

        <div class="mongodb-status">
            🌐 Data stored permanently in MongoDB Cloud
        </div>

        <div class="container">
            <a href="/" class="back-link">← Back to Dashboard</a>
            
            <h2>✅ Available for Review ({{ available_tasks|length }})</h2>
            {% if available_tasks %}
                {% for task in available_tasks %}
                <div class="task-item available">
                    <div class="task-header">
                        <h3 class="task-title">{{ task.title }}</h3>
                        <span class="task-cycle">Review #{{ task.current_cycle + 1 }}</span>
                    </div>
                    {% if task.description %}
                    <div class="task-description">{{ task.description }}</div>
                    {% endif %}
                    <div class="task-dates">
                        <strong>Created:</strong> {{ task.created_at[:10] }} | 
                        <strong>Last Reviewed:</strong> {{ task.last_completed[:10] if task.last_completed else 'Never' }} | 
                        <span class="next-review">Ready Now!</span>
                    </div>
                    <div class="task-actions">
                        <form action="/complete_task/{{ task._id }}" method="post" style="display: inline;">
                            <button type="submit" class="btn">✅ Mark as Reviewed</button>
                        </form>
                        <form action="/delete_task/{{ task._id }}" method="post" style="display: inline;" 
                              onsubmit="return confirm('Are you sure you want to delete this concept?')">
                            <button type="submit" class="btn btn-danger">🗑️ Delete</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-tasks">No concepts are due for review right now.</div>
            {% endif %}

            <h2>⏰ Scheduled for Later ({{ scheduled_tasks|length }})</h2>
            {% if scheduled_tasks %}
                {% for task in scheduled_tasks %}
                <div class="task-item scheduled">
                    <div class="task-header">
                        <h3 class="task-title">{{ task.title }}</h3>
                        <span class="task-cycle">Review #{{ task.current_cycle + 1 }}</span>
                    </div>
                    {% if task.description %}
                    <div class="task-description">{{ task.description }}</div>
                    {% endif %}
                    <div class="task-dates">
                        <strong>Created:</strong> {{ task.created_at[:10] }} | 
                        <strong>Last Reviewed:</strong> {{ task.last_completed[:10] if task.last_completed else 'Never' }} | 
                        <span class="next-review">Due in {{ task.days_until_review }} day{{ 's' if task.days_until_review != 1 else '' }}</span>
                    </div>
                    <div class="task-actions">
                        <form action="/delete_task/{{ task._id }}" method="post" style="display: inline;" 
                              onsubmit="return confirm('Are you sure you want to delete this concept?')">
                            <button type="submit" class="btn btn-danger">🗑️ Delete</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-tasks">No concepts are scheduled for later review.</div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_template, 
                                available_tasks=available_tasks,
                                scheduled_tasks=scheduled_tasks)

@app.route('/delete_task/<task_id>', methods=['POST'])
def delete_task(task_id):
    """Delete a task permanently from MongoDB"""
    success = delete_task_from_db(task_id)
    if not success:
        print(f"Failed to delete task {task_id} from MongoDB")
    
    # Check if request came from all_tasks page
    referer = request.headers.get('Referer', '')
    if 'all_tasks' in referer:
        return redirect(url_for('all_tasks'))
    else:
        return redirect(url_for('index'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        '.',               # Same directory as test.py
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


if __name__ == '__main__':
    serve(app, host="0.0.0.0", port=5000)
    # app.run(debug=True, host='0.0.0.0', port=5000)
