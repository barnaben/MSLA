import shutil
from PIL import Image
from flask import Flask, jsonify, request, redirect, render_template
from time import sleep
from zipfile import ZipFile
import os
import threading

UPLOAD_FOLDER = 'files'
ALLOWED_EXTENSIONS = {"zip"}

status = {"printing": False,
          "pause": False,
          "stop": False,
          "object": "",
          "image": "",
          "percentage": 0
          }

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template("index.html")


@app.route('/getList', methods=['GET', 'POST'])
def getList():
    if request.method == 'GET':
        files = []
        for file in os.listdir("files"):
            if file.endswith(".zip"):
                files.append(file)

    return jsonify(files)


@app.route('/getStatus', methods=['GET'])
def getStatus():
    if request.method == 'GET':
        return jsonify(status)


@app.route('/postSelected', methods=['POST'])
def postSelected():
    if request.method == 'POST':
        print(request.form['selected'])
        status['printing'] = True
        status['object'] = request.form['selected']
        p = threading.Thread(target=printingProcess, args=(request.form['selected'],))
        p.start()
        return jsonify({'response': 'OK'})


@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if request.files:
            file = request.files["file"]

            if file and allowed_file(file.filename):
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                #Todo gcode
            return redirect('/')


@app.route('/postDelete', methods=['GET', 'POST'])
def postDelete():
    select = request.form.get('selected')
    os.remove(UPLOAD_FOLDER + "/" + select)
    return jsonify({'response': 'OK'})


@app.route('/postControl', methods=['GET', 'POST'])
def postControl():
    if request.method == 'POST':
        print(request.form)
        if request.form['control'] == 'pause':
            status['pause'] = not status['pause']
            if status['pause']:
                return jsonify({'response': 'paused'})
            else:
                return jsonify({'response': 'continued'})

        elif request.form['control'] == 'stop':
            status['stop'] = not status['stop']
            return jsonify({'response': 'stopped'})

    return jsonify({'response': 'error'})


@app.route('/postPower', methods=['GET', 'POST'])
def postPower():
    if request.method == 'POST':
        if request.form['power'] == 'shutdown':
            os.system("shutdown /s /t 1")
        elif request.form['power'] == 'reboot':
            os.system("shutdown /r /t 1")


def filldict(filename):
    dictParam = {}
    file = open(filename)
    line = file.readline()
    while line[0] == ';':
        pos = line.find(':')
        name = line[1:pos]
        value = line[pos + 1:-1]
        if value.isnumeric():
            dictParam[name] = float(value)
        else:
            dictParam[name] = value
        line = file.readline()
    return dictParam


def printingProcess(filename):
    # with tempfile.TemporaryDirectory() as print_files:

    path = 'static/' + filename[0:-3]
    file_name = 'files/'+filename
    with ZipFile(file_name, 'r') as zip:
        zip.extractall(path)

    parameters = filldict(path + "/run.gcode")

    for i in range(1, int(parameters['totalLayer'])):
        if status['pause']:
            # Todo pause movement
            while status['pause']:
                print('alszom')
                sleep(1)
            # Todo recover after pause
        elif status['stop']:
            # Todo same movement as pause
            print('megalitottak')
            status["object"] = ""
            status["printing"] = False
            status['stop'] = False
            status['image'] = ""
            clearJunk()
            break

        print('nyomtatok')
        status['image'] = path+"/"+str(i) + '.png'
        status['percentage'] = int((i / parameters["totalLayer"]) * 100)
        img = Image.open(path + '/' + str(i) + '.png')
        print(img.size)
        if i > parameters['bottomLayerCount']:
            img.show()
            sleep(int(parameters['normalExposureTime']))
        else:
            img.show()
            sleep(int(parameters['bottomLayerExposureTime']))

    clearJunk()

def clearJunk():
    folder = 'static'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


if __name__ == '__main__':
    clearJunk()
    app.secret_key = 'super secret key'
    app.run(host='0.0.0.0', debug=True)
