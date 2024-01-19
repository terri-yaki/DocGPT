from flask import Flask, request
import logging

app = Flask(__name__)

@app.route('/callback')
def callback():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    code = request.args.get('code')
    return f'''
        <html>
            <body>
                <center>
                <p>Authorization code: <input type="text" value="{code}" id="authCode"><button onclick="copyCode()">Copy</button></p>
                <p>Please copy and paste the code in the terminal.</p>
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

if __name__ == "__main__":
    app.run(port=8000)