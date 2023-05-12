import os
import shutil


def remove_path(path, keep_external_folder=False):
    if not os.path.exists(path):
        return

    if os.path.isfile(path):
        os.remove(path)
    else:
        assert path not in ['/'], '非法目标路径!'
        shutil.rmtree(path)
        if keep_external_folder:
            os.makedirs(path, exist_ok=True)
