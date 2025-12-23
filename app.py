from flask import Flask, request, render_template_string, Response, jsonify
import urllib.request
import json
import time
import uuid
import threading

app = Flask(__name__)

# Store jobs in memory
jobs = {}

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Substack Notes Exporter</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 500px; 
            margin: 60px auto; 
            padding: 20px;
            background: #fafafa;
        }
        h1 { 
            font-size: 24px;
            margin-bottom: 10px;
        }
        p { 
            color: #666; 
            margin-bottom: 20px;
            line-height: 1.5;
        }
        .small {
            font-size: 14px;
            color: #888;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        button {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            background: #ff6719;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }
        button:hover { background: #e55a14; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .error { color: #c00; margin-top: 15px; }
        #progress { 
            color: #666;
            margin-top: 15px;
        }
        #download {
            display: none;
            margin-top: 20px;
            padding: 12px;
            background: #22c55e;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            text-align: center;
        }
        #download:hover { background: #16a34a; }
    </style>
</head>
<body>
    <h1>Substack Notes Exporter</h1>
    <p>Export all your Substack Notes to a text file.</p>
    <p class="small">First load may take 30 seconds if the server is waking up. Large accounts may take a minute or two.</p>
    
    <input type="text" id="subdomain" placeholder="Your subdomain (e.g. paulstaples)">
    <button id="btn" onclick="startExport()">Export Notes</button>
    <div id="progress"></div>
    <a id="download" href="#">Download Notes</a>

    <script>
        let jobId = null;
        
        async function startExport() {
            const subdomain = document.getElementById('subdomain').value.trim();
            if (!subdomain) {
                alert('Please enter a subdomain');
                return;
            }
            
            document.getElementById('btn').disabled = true;
            document.getElementById('btn').textContent = 'Starting...';
            document.getElementById('progress').textContent = '';
            document.getElementById('download').style.display = 'none';
            
            // Start the job
            const response = await fetch('/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subdomain: subdomain})
            });
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('progress').innerHTML = '<span class="error">' + data.error + '</span>';
                document.getElementById('btn').disabled = false;
                document.getElementById('btn').textContent = 'Export Notes';
                return;
            }
            
            jobId = data.job_id;
            document.getElementById('btn').textContent = 'Fetching...';
            checkProgress();
        }
        
        async function checkProgress() {
            const response = await fetch('/progress/' + jobId);
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('progress').innerHTML = '<span class="error">' + data.error + '</span>';
                document.getElementById('btn').disabled = false;
                document.getElementById('btn').textContent = 'Export Notes';
                return;
            }
            
            document.getElementById('progress').textContent = 'Fetched ' + data.count + ' notes...';
            
            if (data.done) {
                document.getElementById('progress').textContent = 'Done! Found ' + data.count + ' notes.';
                document.getElementById('download').href = '/download/' + jobId;
                document.getElementById('download').style.display = 'block';
                document.getElementById('download').textContent = 'Download ' + data.count + ' Notes';
                document.getElementById('btn').disabled = false;
                document.getElementById('btn').textContent = 'Export Notes';
            } else {
                setTimeout(checkProgress, 1000);
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json()
    subdomain = data.get('subdomain', '').strip().lower()
    
    # Clean up subdomain input
    subdomain = subdomain.replace('https://', '').replace('http://', '')
    subdomain = subdomain.replace('.substack.com', '').replace('/', '')
    
    if not subdomain:
        return jsonify({'error': 'Please enter a subdomain'})
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'subdomain': subdomain,
        'count': 0,
        'notes': [],
        'done': False,
        'error': None
    }
    
    # Start fetching in background thread
    thread = threading.Thread(target=fetch_notes, args=(job_id, subdomain))
    thread.start()
    
    return jsonify({'job_id': job_id})

def fetch_notes(job_id, subdomain):
    cursor = None
    
    try:
        while True:
            url = f"https://{subdomain}.substack.com/api/v1/notes"
            if cursor:
                url += f"?cursor={cursor}"
            
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            
            try:
                response = urllib.request.urlopen(req, timeout=30)
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limited - wait and retry
                    time.sleep(5)
                    continue
                if e.code == 404:
                    jobs[job_id]['error'] = f'Subdomain "{subdomain}" not found.'
                    jobs[job_id]['done'] = True
                    return
                raise
            
            data = json.loads(response.read())
            
            items = data.get("items", [])
            if not items and not jobs[job_id]['notes']:
                jobs[job_id]['error'] = 'No notes found. Check the subdomain and try again.'
                jobs[job_id]['done'] = True
                return
            
            for item in items:
                body = item.get("comment", {}).get("body", "")
                date = item.get("comment", {}).get("date", "")
                if body:
                    jobs[job_id]['notes'].append({"body": body, "date": date})
                    jobs[job_id]['count'] = len(jobs[job_id]['notes'])
            
            cursor = data.get("nextCursor")
            if not cursor:
                break
            
            time.sleep(0.5)  # Rate limiting
    
    except Exception as e:
        jobs[job_id]['error'] = str(e)
    
    jobs[job_id]['done'] = True

@app.route('/progress/<job_id>')
def progress(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'})
    
    job = jobs[job_id]
    return jsonify({
        'count': job['count'],
        'done': job['done'],
        'error': job['error']
    })

@app.route('/download/<job_id>')
def download(job_id):
    if job_id not in jobs:
        return "Job not found", 404
    
    job = jobs[job_id]
    subdomain = job['subdomain']
    notes = job['notes']
    
    # Build the text file
    output = f"Substack Notes Export for @{subdomain}\n"
    output += f"Total notes: {len(notes)}\n"
    output += "=" * 50 + "\n\n"
    
    for i, note in enumerate(notes, 1):
        output += f"--- Note {i} ---\n"
        if note["date"]:
            output += f"Date: {note['date']}\n"
        output += f"{note['body']}\n\n"
    
    return Response(
        output,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={subdomain}_notes.txt'}
    )

if __name__ == '__main__':
    app.run(debug=True)
