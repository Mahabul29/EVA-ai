"""
EvaAI Chat - Flask Application
Homepage-only build. No AI backend wired up yet — add that back into
/api/chat once you're ready (see the placeholder route below).
"""
from flask import Flask, render_template, send_from_directory

app = Flask(__name__, static_folder='static', static_url_path='/static')


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')


@app.route("/service-worker.js")
def service_worker():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')


@app.route("/robots.txt")
def robots():
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')


@app.route("/api/health", methods=["GET"])
def health_check():
    return {"status": "healthy", "service": "EvaAI Chat"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
    
