import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys


def judge_db_is_migrating():
    if 'makemigrations' in sys.argv or 'migrate' in sys.argv:
        return True
    else:
        return False


def get_cursor_by_pg_conf(pg_conf, db_name=None):
    assert 'postgresql' in pg_conf.get('ENGINE'), '本方案仅支持postgresql数据库!'

    db_name = db_name or pg_conf.get('NAME')  # 想新建的数据库名

    user = pg_conf.get('USER')
    pwd = pg_conf.get('PASSWORD')
    port = pg_conf.get('PORT')
    host = pg_conf.get('HOST')

    conn = psycopg2.connect(database=db_name, port=port, host=host, user=user, password=pwd)

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cursor = conn.cursor()
    return cursor


def create_db_if_not_exist(pg_conf, debug=False):
    """
    如果不存在指定数据库, 则创建.
    若创建了则返回True, 否则False
    """
    db_name = pg_conf.get('NAME')

    cursor = get_cursor_by_pg_conf(pg_conf, db_name="postgres")

    # 检查数据库是否存在
    # sql = f'SELECT u.datname FROM pg_catalog.pg_database u where u.datname="{db_name}";'
    # db_name = "a2203_zhiHuiTuShuGuanPingTai_20220618"
    sql = f"SELECT u.datname FROM pg_catalog.pg_database u where u.datname='{db_name}';"
    cursor.execute(sql)

    row = cursor.fetchall()
    if row:
        msg = f'已存在数据库[{db_name}]!'
        if debug:
            print(msg)
        ret = False
    else:
        # 创建数据库
        sql = 'CREATE DATABASE "{}";'.format(db_name)     # pg不支持 CREATE DATABASE XXX IF NOT EXISTS;
        try:
            cursor.execute(sql)
            msg = f'数据库[{db_name}]创建成功.'
            print(msg)
            ret = True
        except Exception as e:
            # print(e)
            if 'already exists' in str(e):
                msg = f'已存在数据库[{db_name}]!'
            else:
                msg = f'--- create_db_if_not_exist Error: {e}'
            if debug:
                print(msg)
            ret = False

    cursor.close()
    return ret


def is_exist_table_in_db(pg_conf, table_name, debug=False):
    """
    判断db中是否已经迁移好了表table_name
    """
    cursor = get_cursor_by_pg_conf(pg_conf)

    # 判断表是否存在
    sql = f'SELECT count(*) FROM "{table_name}";'

    try:
        exist_flag = True
        cursor.execute(sql)
    except Exception as e:
        exist_flag = False
        if debug:
            print('*** is_exist_table_in_db error: ', e)

    if debug:
        print('--- is_exist_table_in_db:', exist_flag)

    cursor.close()
    return exist_flag


def use_zhparser_in_db(pg_conf):
    """
    启动指定pg库的中文分词解释器
    """
    cursor = get_cursor_by_pg_conf(pg_conf)

    try:
        sql ="CREATE EXTENSION zhparser;"
        cursor.execute(sql)
    except Exception as e:
        if 'already exists' in str(e):
            print('数据库已启用`zhparser`!')
            return False
        print('*** zhparser_1: ', e)

    try:
        sql = "CREATE TEXT SEARCH CONFIGURATION chinese_zh (PARSER = zhparser);"
        cursor.execute(sql)
    except Exception as e:
        print('*** zhparser_2: ', e)

    try:
        sql = "ALTER TEXT SEARCH CONFIGURATION chinese_zh ADD MAPPING FOR n,v,a,i,e,l WITH simple;"
        cursor.execute(sql)
    except Exception as e:
        print('*** zhparser_3: ', e)

    print('--- 成功启动zhparser解释器.')
    cursor.close()
    return True


def main():
    from ControlHub.settings.development import DATABASES
    pg_conf = DATABASES.get('default')

    create_db_if_not_exist(pg_conf, debug=True)

    use_zhparser_in_db(pg_conf)

    is_exist_table_in_db(pg_conf, table_name='user_customuser', debug=True)


if __name__ == '__main__':
    main()


