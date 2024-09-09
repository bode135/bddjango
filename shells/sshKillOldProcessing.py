import os


def run(port=8000):
    """
    杀掉占用80端口的旧进程
    """
    os.system(f'bash shells/killport.sh {port}')


if __name__ == '__main__':
    run()
