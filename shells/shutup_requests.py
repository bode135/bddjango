"""
# 让requests的报错闭嘴

pip install chardet==3.0.2
"""

import os
import shutil

dest_path = "/usr/local/lib/python3.6/dist-packages/requests/__init__.py"


def main():
    import re

    with open(dest_path, 'r') as f:
        text = f.read()

    pattern = r""" *(warnings.warn)\("urllib3 \(\{\}\)"""
    # pattern = r"^ *check_compatibility"
    reg = re.compile(pattern)
    match = reg.search(text)
    print('match: ', match)

    if not match:   return

    match.group(1)

    span_1 = match.span(1)
    text[span_1[0] - 1]

    print(text)
    text.count('\n')
    1


if __name__ == '__main__':
    main()
