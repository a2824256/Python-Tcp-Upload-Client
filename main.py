# This Python file uses the following encoding: utf-8
import socket
import os
import json
import struct
import sys
import threading
import time

os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = './platforms'

from PySide2.QtWidgets import QApplication, QWidget, QFileDialog
from PySide2.QtCore import QFile, Signal
from PySide2.QtUiTools import QUiLoader
FILE_COUNTER = 0
STORE_PATH = os.path.join(os.getcwd(), 'upload')
print(STORE_PATH)
buffer = 1024
DELETE_SOURCE = False

class Main(QWidget):
    signal_log = Signal(str)
    signal_transmit = Signal()
    def __init__(self):
        super(Main, self).__init__()
        self.path = ""
        self.ip = ""
        self.load_ui()

    def load_ui(self):
        loader = QUiLoader()
        path = "./form.ui"
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

    def unlock_start_button(self):
        self.ui.startButton.setEnabled(True)

    def widget_setting(self):
        self.ui.startButton.clicked.connect(self.start_upload_thread)
        self.ui.selectButton.clicked.connect(self.select_dir)
        self.signal_log.connect(self.update_logs)
        self.signal_transmit.connect(self.unlock_start_button)

    def update_logs(self, string):
        self.ui.logBox.insertPlainText(string)

    def select_dir(self):
        self.selected_directory = QFileDialog.getExistingDirectory(self, "选择文件所在目录", "")
        self.ui.pathBox.setText(self.selected_directory)
        self.path = self.selected_directory

    def get_localtime(self):
        return str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    def start_upload_thread(self):
        global DELETE_SOURCE
        DELETE_SOURCE = self.ui.checkBox.isChecked()
        self.ip = self.ui.ipBox.toPlainText()
        self.ui.startButton.setEnabled(False)
        print(self.ip)
        thread = threading.Thread(target=self.upload_files)
        thread.start()

    def upload_files(self):
        print('upload')
        global FILE_COUNTER
        sk = socket.socket()
        sk.connect((self.ip, 60000))
        for root, dirs, files in os.walk(self.path):
            for file in files:
                FILE_COUNTER += 1
        localtime = self.get_localtime()
        content = localtime + ' ' + str(FILE_COUNTER) + '个文件开始上传\n'
        self.signal_log.emit(content)
        for root, dirs, files in os.walk(self.path):
            for file in files:
                res = root.find(self.path)
                if res != -1:
                    file_path = root.replace(self.path, '')
                    localtime = self.get_localtime()
                    content = localtime + ' ' + file + '开始上传\n'
                    self.signal_log.emit(content)
                    self.send_file(sk, file_path, file)
                    content = sk.recv(4)
                    content = content.decode('utf-8')
                    if '0' in content and DELETE_SOURCE is True:
                        os.remove(os.path.join(self.path.replace('/', '\\') + file_path, file))
        localtime = self.get_localtime()
        content = localtime + ' 上传结束\n'
        self.signal_log.emit(content)
        self.signal_transmit.emit()
        FILE_COUNTER = 0

    def get_integrity_checking(self):
        return 0


    def send_file(self, sk, file_path, filename):
        head = {'l': FILE_COUNTER,
                'filepath': file_path,
                'filename': filename,
                'filesize': None}
        file_path = os.path.join(self.path.replace('/', '\\') + file_path, filename)
        # 计算文件的大小
        filesize = os.path.getsize(file_path)
        head['filesize'] = filesize
        json_head = json.dumps(head)  # 利用json将字典转成字符串
        bytes_head = json_head.encode('utf-8')  # 字符串转bytes
        # 计算head长度
        head_len = len(bytes_head)  # 报头的长度
        # 利用struct将int类型的数据打包成4个字节的byte，所以服务器端接受这个长度的时候可以固定缓冲区大小为4
        pack_len = struct.pack('i', head_len)
        # 先将报头长度发出去
        sk.send(pack_len)
        # 再发送bytes类型的报头
        sk.send(bytes_head)
        with open(file_path, 'rb') as f:
            while filesize:
                if filesize >= buffer:
                    content = f.read(buffer)  # 每次读取buffer字节大小内容
                    filesize -= buffer
                    sk.send(content)  # 发送读取的内容
                else:
                    content = f.read(filesize)
                    sk.send(content)
                    filesize = 0
                    f.close()
                    break


if __name__ == "__main__":
    app = QApplication([])
    widget = Main()
    widget.widget_setting()
    widget.setWindowTitle("采集文件上传客户端")
    widget.show()
    sys.exit(app.exec_())
