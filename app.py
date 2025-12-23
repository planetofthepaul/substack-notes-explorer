from flask import Flask, request, render_template_string, Response
import urllib.request
import json
import time

app = Flask(__name__)

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
            margin-bottom: 30px;
            line-height: 1.5;
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
        .info { color: #666; margin-top: 15px; }
        #status { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Substack Notes Exporter</h1>
    <p>Export all your Substack Notes to a text file.</p>
    
    <form action="/export" method="post" id="form">
        <input type="text" name="subdomain" id="subdomain" 
               placeholder="Your subdomain (e.g. paulstaples)" required>
        <button type="submit" id="btn">Export Notes</button>
    </form>
    <div id="status"></div>

    <script>
        document.getElementById('form').onsubmit = function() {
            document.getElementById('btn').disabled = true;
            document.getElementById('btn').textContent = 'Fetching notes... (this may take a minute)';
            document.getElementById('status').innerHTML = '<p class="info">Please wait, fetching all notes...</p>';
        };
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/export', methods=['POST'])
def export():
    subdomain = request.form.get('subdomain', '').strip().lower()
    
    # Clean up subdomain input
    subdomain = subdomain.replace('https://', '').replace('http://', '')
    subdomain = subdomain.replace('.substack.com', '').replace('/', '')
    
    if not subdomain:
        return render_template_string(HTML + '<p class="error">Please enter a subdomain.</p>')
    
    all_notes = []
    cursor = None
    
    try:
        while True:
            url = f"https://{subdomain}.substack.com/api/v1/notes"
            if cursor:
                url += f"?cursor={cursor}"
            
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            response = urllib.request.urlopen(req, timeout=30)
            data = json.loads(response.read())
            
            items = data.get("items", [])
            if not items and not all_notes:
                return render_template_string(HTML + '<p class="error">No notes found. Check the subdomain and try again.</p>')
            
            for item in items:
                body = item.get("comment", {}).get("body", "")
                date = item.get("comment", {}).get("date", "")
                if body:
                    all_notes.append({"body": body, "date": date})
            
            cursor = data.get("nextCursor")
            if not cursor:
                break
            
            time.sleep(0.5)  # Rate limiting
    
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return render_template_string(HTML + f'<p class="error">Subdomain "{subdomain}" not found.</p>')
        return render_template_string(HTML + f'<p class="error">Error fetching notes: {e}</p>')
    except Exception as e:
        return render_template_string(HTML + f'<p class="error">Error: {e}</p>')
    
    # Build the text file
    output = f"Substack Notes Export for @{subdomain}\n"
    output += f"Total notes: {len(all_notes)}\n"
    output += "=" * 50 + "\n\n"
    
    for i, note in enumerate(all_notes, 1):
        output += f"--- Note {i} ---\n"
        if note["date"]:
            output += f"Date: {note['date']}\n"
        output += f"{note['body']}\n\n"
    
    # Return as downloadable file
    return Response(
        output,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={subdomain}_notes.txt'}
    )

if __name__ == '__main__':
    app.run(debug=True)
