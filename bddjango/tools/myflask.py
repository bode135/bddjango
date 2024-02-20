# python3 /root/tools/myflask.py

from flask import Flask
from bdtime import tt
app = Flask(__name__)


@app.route('/')
def hello_world():
    msg = f"\n~~~ current_beijing_time: {tt.get_current_beijing_time_str(decimal_places=3)}\n"
    return msg


# region # --- cmd参数
import argparse


def parse_args():
    """
    # 参数解释

    # 其它类型参数:
    parser.add_argument("--seed", type=int, default=1,
                        help="seed of the experiment")
    parser.add_argument("--float", type=float, default=1.2345,
                        help="float")
    parser.add_argument('-ls', '-list', action='append')      # 输入列表
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', "--local", action="store_true", default=False, help="是否本地模式")
    parser.add_argument('-ip', "--ip", type=str, default='0.0.0.0', help="IP地址")
    parser.add_argument('-p', "--port", default=5000, type=int, help="端口")

    args = parser.parse_args()
    return args
# endregion


if __name__ == '__main__':
    args = parse_args()

    if args.local:
        host = 'localhost'
    else:
        host = '0.0.0.0'

    print(f'\n\n****** 启动时间: {tt.get_current_beijing_time_str(decimal_places=0)}\n\n')
    app.run(host=host, port=args.port)

