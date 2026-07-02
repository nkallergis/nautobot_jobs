WITH schema_info AS (
    SELECT
        'postgresql' AS dbms,
        t.table_catalog,
        t.table_schema,
        t.table_name,
        c.column_name,
        c.ordinal_position,
        c.data_type,
        c.character_maximum_length,
        n.constraint_type,
        k2.table_schema AS referenced_table_schema,
        k2.table_name AS referenced_table_name,
        k2.column_name AS referenced_column_name
    FROM
        information_schema.tables t
    NATURAL LEFT JOIN information_schema.columns c
    LEFT JOIN (
        information_schema.key_column_usage k
        NATURAL JOIN information_schema.table_constraints n
        NATURAL LEFT JOIN information_schema.referential_constraints r
    ) ON c.table_catalog = k.table_catalog
       AND c.table_schema = k.table_schema
       AND c.table_name = k.table_name
       AND c.column_name = k.column_name
    LEFT JOIN information_schema.key_column_usage k2
      ON k.position_in_unique_constraint = k2.ordinal_position
     AND r.unique_constraint_catalog = k2.constraint_catalog
     AND r.unique_constraint_schema = k2.constraint_schema
     AND r.unique_constraint_name = k2.constraint_name
    WHERE
        t.TABLE_TYPE = 'BASE TABLE'
        AND t.table_schema NOT IN ('information_schema', 'pg_catalog')
),
customfield_info AS (
    SELECT
        'postgresql' AS dbms,
        'nautobot' AS table_catalog,
        'public' AS table_schema,
        CONCAT(dct.app_label, '_', dct.model) AS table_name,
        CONCAT('CF_', ecf.key) AS column_name,  -- Prefixing with 'CF_'
        ROW_NUMBER() OVER (PARTITION BY dct.app_label, dct.model ORDER BY ecf.key) +
        COALESCE((
            SELECT MAX(ordinal_position)
            FROM information_schema.columns
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ), 0) AS ordinal_position,
        ecf.type AS data_type,  -- Using original "customfield_type"
        CAST(NULL AS INTEGER) AS character_maximum_length,
        NULL AS constraint_type,
        NULL AS referenced_table_schema,
        NULL AS referenced_table_name,
        NULL AS referenced_column_name
    FROM
        extras_customfield ecf
    INNER JOIN extras_customfield_content_types ecct
        ON ecf.id = ecct.customfield_id
    INNER JOIN django_content_type dct
        ON ecct.contenttype_id = dct.id
),
customrelationship_info AS (
    SELECT
        'postgresql' AS dbms,
        'nautobot' AS table_catalog,
        'public' AS table_schema,
        CONCAT(src_ct.app_label, '_', src_ct.model) AS table_name,
        LOWER(CONCAT('CR_', dest_ct.model, '_id')) AS column_name,  -- Prepending "CR_"
        ROW_NUMBER() OVER (PARTITION BY src_ct.app_label, src_ct.model ORDER BY er.key) +
        COALESCE((
            SELECT MAX(ordinal_position)
            FROM information_schema.columns
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ), 0) AS ordinal_position,
        'uuid' AS data_type,  -- Relationships are UUID-based foreign keys
        CAST(NULL AS INTEGER) AS character_maximum_length,
        'FOREIGN KEY' AS constraint_type,
        'public' AS referenced_table_schema,
        CONCAT(dest_ct.app_label, '_', dest_ct.model) AS referenced_table_name,
        'id' AS referenced_column_name
    FROM
        extras_relationship er
    INNER JOIN django_content_type src_ct
        ON er.source_type_id = src_ct.id
    INNER JOIN django_content_type dest_ct
        ON er.destination_type_id = dest_ct.id
)
SELECT
    dbms,
    table_catalog,
    table_schema,
    table_name,
    column_name,
    ordinal_position,
    data_type,
    character_maximum_length,
    constraint_type,
    referenced_table_schema,
    referenced_table_name,
    referenced_column_name
FROM schema_info
UNION ALL
SELECT
    dbms,
    table_catalog,
    table_schema,
    table_name,
    column_name,
    ordinal_position::INTEGER,
    data_type,
    character_maximum_length,
    constraint_type,
    referenced_table_schema,
    referenced_table_name,
    referenced_column_name
FROM customfield_info
UNION ALL
SELECT
    dbms,
    table_catalog,
    table_schema,
    table_name,
    column_name,
    ordinal_position::INTEGER,
    data_type,
    character_maximum_length,
    constraint_type,
    referenced_table_schema,
    referenced_table_name,
    referenced_column_name
FROM customrelationship_info;
