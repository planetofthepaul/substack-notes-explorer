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
    <title>Substack Notes Exporter ✿</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Privacy-friendly analytics by Plausible -->
    <script async src="https://plausible.io/js/pa-jluo04lsBer5Kjum87QyY.js"></script>
    <script>
      window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};
      plausible.init()
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Quicksand:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        
        body { 
            font-family: 'Quicksand', 'Georgia', serif;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            background: linear-gradient(145deg, #fef9f3 0%, #fdf2e9 30%, #fce8e4 60%, #f9e4e8 100%);
            background-attachment: fixed;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        /* Floating flowers background */
        body::before {
            content: "✿ ❀ ✿ ❀ ✿ ❀ ✿ ❀ ✿ ❀ ✿ ❀";
            position: fixed;
            top: 20px;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 14px;
            color: #e8b4bc;
            opacity: 0.5;
            letter-spacing: 20px;
            pointer-events: none;
            z-index: 0;
        }
        
        body::after {
            content: "❁ ✾ ❁ ✾ ❁ ✾ ❁ ✾ ❁ ✾ ❁ ✾";
            position: fixed;
            bottom: 20px;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 14px;
            color: #d4a5a5;
            opacity: 0.4;
            letter-spacing: 20px;
            pointer-events: none;
            z-index: 0;
        }
        
        .container {
            width: 100%;
            max-width: 460px;
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 40px 35px;
            box-shadow: 
                0 4px 30px rgba(199, 144, 144, 0.15),
                0 1px 3px rgba(199, 144, 144, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(232, 180, 188, 0.3);
            position: relative;
            z-index: 1;
        }
        
        .flower-divider {
            text-align: center;
            color: #d4a5a5;
            font-size: 12px;
            letter-spacing: 8px;
            margin: 5px 0 25px 0;
            opacity: 0.7;
        }
        
        h1 { 
            font-family: 'Cormorant Garamond', Georgia, serif;
            font-size: 28px;
            font-weight: 500;
            color: #8b6b6b;
            margin: 0 0 5px 0;
            text-align: center;
            letter-spacing: 1px;
        }
        
        .subtitle {
            font-family: 'Cormorant Garamond', Georgia, serif;
            font-style: italic;
            color: #b8928f;
            text-align: center;
            margin-bottom: 8px;
            font-size: 17px;
        }
        
        p { 
            color: #9a8080; 
            margin-bottom: 18px;
            line-height: 1.7;
            text-align: center;
            font-size: 15px;
        }
        
        .small {
            font-size: 13px;
            color: #b8a0a0;
        }
        
        .small a {
            color: #c9928e;
            text-decoration: none;
            border-bottom: 1px dotted #c9928e;
            transition: all 0.3s ease;
        }
        
        .small a:hover {
            color: #a87070;
            border-bottom-color: #a87070;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 14px 18px;
            font-size: 16px;
            font-family: 'Quicksand', sans-serif;
            border: 2px solid #edd9d9;
            border-radius: 50px;
            margin-bottom: 18px;
            background: rgba(255, 255, 255, 0.7);
            color: #7a6060;
            transition: all 0.3s ease;
            text-align: center;
        }
        
        input[type="text"]::placeholder {
            color: #c4aaaa;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #d4a5a5;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 0 20px rgba(212, 165, 165, 0.2);
        }
        
        button {
            width: 100%;
            padding: 14px 20px;
            font-size: 16px;
            font-family: 'Quicksand', sans-serif;
            font-weight: 500;
            background: linear-gradient(135deg, #e8b4b8 0%, #d4a5a5 100%);
            color: white;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(212, 165, 165, 0.3);
            letter-spacing: 0.5px;
        }
        
        button:hover { 
            background: linear-gradient(135deg, #d4a5a5 0%, #c99595 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(212, 165, 165, 0.4);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button:disabled { 
            background: linear-gradient(135deg, #ddd 0%, #ccc 100%);
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .error { 
            color: #c48080; 
            background: rgba(196, 128, 128, 0.1);
            padding: 12px 16px;
            border-radius: 12px;
            border: 1px solid rgba(196, 128, 128, 0.2);
            margin-top: 15px;
            text-align: center;
        }
        
        #progress { 
            color: #9a8080;
            margin-top: 18px;
            text-align: center;
            font-style: italic;
        }
        
        #download {
            display: none;
            margin-top: 20px;
            padding: 14px 20px;
            background: linear-gradient(135deg, #a8c5a0 0%, #8fb88a 100%);
            color: white;
            text-decoration: none;
            border-radius: 50px;
            text-align: center;
            font-family: 'Quicksand', sans-serif;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(143, 184, 138, 0.3);
        }
        
        #download:hover { 
            background: linear-gradient(135deg, #8fb88a 0%, #7aa876 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(143, 184, 138, 0.4);
        }
        
        .leaf {
            display: inline-block;
            margin: 0 5px;
        }
        
        /* Mobile Responsive */
        @media (max-width: 520px) {
            body {
                padding: 15px;
                align-items: flex-start;
                padding-top: 40px;
            }
            
            .container {
                padding: 30px 25px;
                border-radius: 20px;
            }
            
            h1 {
                font-size: 24px;
            }
            
            .subtitle {
                font-size: 15px;
            }
            
            p {
                font-size: 14px;
                margin-bottom: 15px;
            }
            
            input[type="text"] {
                padding: 12px 16px;
                font-size: 16px; /* Prevents zoom on iOS */
            }
            
            button, #download {
                padding: 12px 18px;
                font-size: 15px;
            }
            
            body::before, body::after {
                font-size: 10px;
                letter-spacing: 12px;
            }
        }
        
        @media (max-width: 360px) {
            .container {
                padding: 25px 20px;
            }
            
            h1 {
                font-size: 22px;
            }
            
            .flower-divider {
                letter-spacing: 5px;
            }
        }
        
        /* Cute loading animation */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 1.5s ease-in-out infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Notes Exporter</h1>
        <p class="subtitle">for your Substack musings ✿</p>
        <div class="flower-divider">❀ ✿ ❀ ✿ ❀</div>
        
        <p>Gently gather all your notes into a lovely text file, ready to cherish forever.</p>
        
        <p class="small">crafted with care by <a href="https://paulstaples.substack.com" target="_blank">Paul Staples</a></p>
        <p class="small">The first bloom may take a moment if the garden is waking. Larger collections need a little more time to gather. ✿</p>
        
        <input type="text" id="subdomain" placeholder="your subdomain (e.g. paulstaples)">
        <button id="btn" onclick="startExport()"><span class="leaf">🌿</span> Gather My Notes <span class="leaf">🌿</span></button>
        <div id="progress"></div>
        <a id="download" href="#"><span class="leaf">🍃</span> Download Your Notes <span class="leaf">🍃</span></a>
    </div>

    <script>
        let jobId = null;
        
        async function startExport() {
            const subdomain = document.getElementById('subdomain').value.trim();
            if (!subdomain) {
                alert('Please enter a subdomain, dear 🌸');
                return;
            }
            
            document.getElementById('btn').disabled = true;
            document.getElementById('btn').innerHTML = '✿ Preparing... ✿';
            document.getElementById('btn').classList.add('loading');
            document.getElementById('progress').textContent = '';
            document.getElementById('download').style.display = 'none';
            
            // Start the job
            const response = await fetch('/notes/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subdomain: subdomain})
            });
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('progress').innerHTML = '<span class="error">Oh dear... ' + data.error + '</span>';
                document.getElementById('btn').disabled = false;
                document.getElementById('btn').innerHTML = '<span class="leaf">🌿</span> Gather My Notes <span class="leaf">🌿</span>';
                document.getElementById('btn').classList.remove('loading');
                return;
            }
            
            jobId = data.job_id;
            document.getElementById('btn').innerHTML = '❀ Gathering... ❀';
            checkProgress();
        }
        
        async function checkProgress() {
            const response = await fetch('/notes/progress/' + jobId);
            const data = await response.json();
            
            if (data.error) {
                document.getElementById('progress').innerHTML = '<span class="error">Oh dear... ' + data.error + '</span>';
                document.getElementById('btn').disabled = false;
                document.getElementById('btn').innerHTML = '<span class="leaf">🌿</span> Gather My Notes <span class="leaf">🌿</span>';
                document.getElementById('btn').classList.remove('loading');
                return;
            }
            
            document.getElementById('progress').textContent = '✿ Gathered ' + data.count + ' notes so far... ✿';
            
            if (data.done) {
                document.getElementById('progress').textContent = '🌸 Wonderful! Found ' + data.count + ' lovely notes. 🌸';
                document.getElementById('download').href = '/notes/download/' + jobId;
                document.getElementById('download').style.display = 'block';
                document.getElementById('download').innerHTML = '<span class="leaf">🍃</span> Download ' + data.count + ' Notes <span class="leaf">🍃</span>';
                document.getElementById('btn').disabled = false;
                document.getElementById('btn').innerHTML = '<span class="leaf">🌿</span> Gather My Notes <span class="leaf">🌿</span>';
                document.getElementById('btn').classList.remove('loading');
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
    output = f"✿ Substack Notes Export for @{subdomain} ✿\n"
    output += f"Total notes: {len(notes)}\n"
    output += "─" * 40 + "\n\n"
    
    for i, note in enumerate(notes, 1):
        output += f"── Note {i} ──\n"
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
