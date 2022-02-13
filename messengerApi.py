from flask import (
    Flask,
    render_template
)
import connexion

app = connexion.App(__name__, specification_dir='./')
app.add_api('messengerSwagger.yml')


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')


if __name__ == '__main__':
    app.run(host="192.168.1.102", port=8080, debug=True)
