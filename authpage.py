from flask import Flask, request
import logging
import os
import socket

app = Flask(__name__)

AUTH_CODE_FILE = "auth_code.txt"
AUTH_PORT_FILE = "auth_port.txt"

def get_free_port():
    """Finds and returns an available port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

@app.route('/callback')
def callback():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    code = request.args.get('code')
    if code:
        with open(AUTH_CODE_FILE, "w") as f:
            f.write(code)
    return f'''
        <html>
            <body>
                <center>
                <p>Authorization code: <input type="text" value="{code}" id="authCode"><button onclick="copyCode()">Copy</button></p>
                <p>Please copy and paste the code in the terminal if automatic retrieval fails.</p>
                <script>
                    function copyCode() {{
                        var copyText = document.getElementById("authCode");
                        copyText.select();
                        document.execCommand("copy");
                    }}
                </script>
            </center>
            </body>
        </html>
    '''
    
@app.route('/shutdown')
def shutdown():
    shutdownrequest = request.environ.get('werkzeug.server.shutdown')
    if shutdownrequest is None:
        # This might happen if the server is not Werkzeug, or not in debug mode.
        # For simplicity, we'll assume Werkzeug for now.
        raise RuntimeError("Not running with the Werkzeug Server or shutdown function not available.")
    shutdownrequest()
    return "Server shutting down..."


if __name__ == "__main__":
    port_str = os.environ.get("AUTH_PORT")
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            print(f"Warning: Invalid AUTH_PORT '{port_str}'. Using a free port instead.")
            port = get_free_port()
    else:
        port = get_free_port()

    with open(AUTH_PORT_FILE, "w") as f:
        f.write(str(port))
    
    print(f"Auth server starting on port {port}") # Optional: for direct run debugging
    app.run(port=port, debug=False) # debug=False is important for production and consistent shutdown