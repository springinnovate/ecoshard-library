"""Simple flask server to test connectivity."""
import flask

app = flask.Flask(__name__)


@app.route('/test')
def index():
    """Root page."""
    return 'hello'
