from flask import Flask

app = Flask(__name__, static_url_path="", static_folder="staticpahes")

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == ("__main__") :
    app.run(debug=True)