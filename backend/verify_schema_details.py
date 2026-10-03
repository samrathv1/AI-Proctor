import json
import subprocess

sql = """
SELECT json_build_object(
    'tables', (
        SELECT json_agg(json_build_object('table', tablename, 'rls_enabled', rowsecurity))
        FROM pg_tables WHERE schemaname = 'public'
    ),
    'policies', (
        SELECT json_agg(json_build_object('table', tablename, 'policy', policyname, 'cmd', cmd, 'roles', roles))
        FROM pg_policies WHERE schemaname = 'public'
    ),
    'enums', (
        SELECT json_agg(json_build_object('enum', typname))
        FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid
        WHERE n.nspname = 'public' AND t.typtype = 'e'
    ),
    'indexes', (
        SELECT count(*) FROM pg_indexes WHERE schemaname = 'public'
    ),
    'foreign_keys', (
        SELECT count(*)
        FROM information_schema.table_constraints
        WHERE constraint_schema = 'public' AND constraint_type = 'FOREIGN KEY'
    ),
    'primary_keys', (
        SELECT count(*)
        FROM information_schema.table_constraints
        WHERE constraint_schema = 'public' AND constraint_type = 'PRIMARY KEY'
    )
);
"""

with open("supabase/verify.sql", "w", encoding="utf-8") as f:
    f.write(sql.strip())

cmd = ["npx", "supabase", "db", "query", "--linked", "--project-ref", "wxsodwupyieseegvniuq", "-f", "supabase/verify.sql"]
res = subprocess.run(cmd, capture_output=True, text=True, check=True)
print(res.stdout)
