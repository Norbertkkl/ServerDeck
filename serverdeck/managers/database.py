import re
import subprocess
from typing import Any, Dict, List, Tuple
from serverdeck.core.state import find_bin, _db_cache, STATE_LOCK

def mariadb_exec(sql: str) -> Tuple[bool, str]:
    bin_cmd = find_bin("mariadb") or find_bin("mysql")
    if not bin_cmd:
        return False, "Neither mariadb nor mysql client binary found"
    try:
        proc = subprocess.run(
            [bin_cmd, "-B", "-N", "-e", sql],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3.0
        )
        if proc.returncode == 0:
            return True, proc.stdout
        err = proc.stderr.strip().replace("\n", " ")
        return False, err
    except subprocess.TimeoutExpired:
        return False, "Database query timed out (3.0s)"
    except Exception as e:
        return False, str(e)

def get_mariadb_databases(force: bool = False) -> List[Dict[str, Any]]:
    global _db_cache
    with STATE_LOCK:
        if not force and _db_cache["dbs"]:
            return _db_cache["dbs"]

    sql = (
        "SELECT table_schema, COUNT(*), "
        "COALESCE(SUM(data_length + index_length), 0) "
        "FROM information_schema.tables "
        "GROUP BY table_schema;"
    )
    ok, out = mariadb_exec(sql)
    dbs = []
    if ok and out:
        for line in out.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                name = parts[0].strip()
                tbl_cnt = int(parts[1]) if parts[1].isdigit() else 0
                sz_bytes = int(parts[2]) if parts[2].isdigit() else 0
                sz_mb = round(sz_bytes / (1024 * 1024), 2)
                is_sys = name in ("information_schema", "performance_schema", "mysql", "sys")
                dbs.append({
                    "name": name,
                    "tables": tbl_cnt,
                    "size_mb": sz_mb,
                    "is_system": is_sys
                })
    with STATE_LOCK:
        _db_cache["dbs"] = dbs
    return dbs

def get_mariadb_users(force: bool = False) -> List[Dict[str, Any]]:
    global _db_cache
    with STATE_LOCK:
        if not force and _db_cache["users"]:
            return _db_cache["users"]

    sql = (
        "SELECT User, Host, "
        "IF(LENGTH(authentication_string)>0 OR LENGTH(Password)>0, 'YES', 'NO') "
        "FROM mysql.user;"
    )
    ok, out = mariadb_exec(sql)
    users = []
    if ok and out:
        for line in out.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                u = parts[0].strip()
                h = parts[1].strip()
                has_pass = parts[2].strip() if len(parts) >= 3 else "NO"
                is_sys = u in ("root", "mariadb.sys", "mysql.sys", "mysql.session", "mysql.infoschema")
                users.append({
                    "user": u,
                    "host": h,
                    "has_password": has_pass,
                    "is_system": is_sys
                })
    with STATE_LOCK:
        _db_cache["users"] = users
    return users

def sanitize_identifier(ident: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '', ident).strip()

def escape_sql_string(val: str) -> str:
    return val.replace('\\', '\\\\').replace("'", "''")

def create_database(dbname: str) -> Tuple[bool, str]:
    clean_name = sanitize_identifier(dbname)
    if not clean_name or len(clean_name) > 64:
        return False, "Invalid database name"
    sql = f"CREATE DATABASE `{clean_name}`; FLUSH PRIVILEGES;"
    ok, msg = mariadb_exec(sql)
    get_mariadb_databases(force=True)
    if ok:
        return True, f"Database `{clean_name}` created successfully"
    return False, f"Failed to create database `{clean_name}`: {msg}"

def drop_database(dbname: str) -> Tuple[bool, str]:
    clean_name = sanitize_identifier(dbname)
    if clean_name in ("information_schema", "performance_schema", "mysql", "sys"):
        return False, "Cannot delete protected system database!"
    sql = f"DROP DATABASE `{clean_name}`; FLUSH PRIVILEGES;"
    ok, msg = mariadb_exec(sql)
    get_mariadb_databases(force=True)
    if ok:
        return True, f"Database `{clean_name}` dropped successfully"
    return False, f"Failed to drop database `{clean_name}`: {msg}"

def create_db_user(username: str, host: str = "%", password: str = "") -> Tuple[bool, str]:
    clean_user = sanitize_identifier(username)
    clean_host = re.sub(r'[^a-zA-Z0-9_\-\.\%]', '', host).strip() or "%"
    if not clean_user or len(clean_user) > 32:
        return False, "Invalid username"
    escaped_pass = escape_sql_string(password)
    pass_clause = f" IDENTIFIED BY '{escaped_pass}'" if password else ""
    sql = f"CREATE USER '{clean_user}'@'{clean_host}'{pass_clause}; FLUSH PRIVILEGES;"
    ok, msg = mariadb_exec(sql)
    get_mariadb_users(force=True)
    if ok:
        return True, f"User '{clean_user}'@'{clean_host}' created successfully"
    return False, f"Failed to create user: {msg}"

def drop_db_user(username: str, host: str = "%") -> Tuple[bool, str]:
    clean_user = sanitize_identifier(username)
    clean_host = re.sub(r'[^a-zA-Z0-9_\-\.\%]', '', host).strip() or "%"
    if clean_user in ("root", "mariadb.sys", "mysql.sys") and clean_host in ("localhost", "127.0.0.1", "::1"):
        return False, "Cannot delete protected root/system user!"
    sql = f"DROP USER '{clean_user}'@'{clean_host}'; FLUSH PRIVILEGES;"
    ok, msg = mariadb_exec(sql)
    get_mariadb_users(force=True)
    if ok:
        return True, f"User '{clean_user}'@'{clean_host}' dropped successfully"
    return False, f"Failed to drop user: {msg}"

def grant_db_privileges(dbname: str, username: str, host: str = "%") -> Tuple[bool, str]:
    clean_db = sanitize_identifier(dbname)
    clean_user = sanitize_identifier(username)
    clean_host = re.sub(r'[^a-zA-Z0-9_\-\.\%]', '', host).strip() or "%"
    if not clean_db or not clean_user:
        return False, "Database name and username required"
    sql = f"GRANT ALL PRIVILEGES ON `{clean_db}`.* TO '{clean_user}'@'{clean_host}'; FLUSH PRIVILEGES;"
    ok, msg = mariadb_exec(sql)
    if ok:
        return True, f"Granted privileges on `{clean_db}`.* to '{clean_user}'@'{clean_host}'"
    return False, f"Failed to grant privileges: {msg}"

def reset_db_password(username: str, host: str = "%", new_password: str = "") -> Tuple[bool, str]:
    clean_user = sanitize_identifier(username)
    clean_host = re.sub(r'[^a-zA-Z0-9_\-\.\%]', '', host).strip() or "%"
    if not clean_user:
        return False, "Username required"
    escaped_pass = escape_sql_string(new_password)
    sql = f"ALTER USER '{clean_user}'@'{clean_host}' IDENTIFIED BY '{escaped_pass}'; FLUSH PRIVILEGES;"
    ok, msg = mariadb_exec(sql)
    if ok:
        return True, f"Password reset for '{clean_user}'@'{clean_host}'"
    return False, f"Failed to reset password: {msg}"
