import importlib.metadata


def get_package_version(package_name):
    try:
        version = importlib.metadata.version(package_name)
        return version
    except importlib.metadata.PackageNotFoundError:
        return None


def is_version_greater_than(version_str, compare_to="3.2"):
    def parse_version(version):
        return tuple(map(int, (version.split("."))))

    version_tuple = parse_version(version_str)
    compare_to_tuple = parse_version(compare_to)
    return version_tuple > compare_to_tuple


if __name__ == '__main__':
    version_str = get_package_version("django")
    is_version_greater_than(version_str, "3.21.1")


