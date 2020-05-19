CREATE TABLE job_table (
    -- a unique hash of the job based on the raster id
    job_id TEXT NOT NULL PRIMARY KEY,
    uri TEXT NOT NULL,
    job_status TEXT NOT NULL,
    active INT NOT NULL, -- 0 if complete, error no not
    last_accessed_utc TEXT NOT NULL
    );

CREATE INDEX last_accessed_index ON job_table(last_accessed_utc);
CREATE INDEX job_id_index ON job_table(job_id);

-- we may search by partial `id` so set NOCASE so we can use the index
CREATE TABLE catalog_table (
    asset_id TEXT NOT NULL COLLATE NOCASE,
    catalog TEXT NOT NULL COLLATE NOCASE,
    xmin REAL NOT NULL,
    xmax REAL NOT NULL,
    ymin REAL NOT NULL,
    ymax REAL NOT NULL,
    utc_datetime TEXT NOT NULL COLLATE NOCASE,
    mediatype TEXT NOT NULL COLLATE NOCASE,
    description TEXT NOT NULL COLLATE NOCASE,
    uri TEXT NOT NULL,
    local_path TEXT NOT NULL,
    raster_min REAL NOT NULL,
    raster_max REAL NOT NULL,
    raster_mean REAL NOT NULL,
    raster_stdev REAL NOT NULL,
    default_style TEXT NOT NULL,
    PRIMARY KEY (asset_id, catalog)
    );
CREATE INDEX asset_id_index ON catalog_table(asset_id);
CREATE INDEX catalog_index ON catalog_table(catalog);
CREATE INDEX xmin_index ON catalog_table(xmin);
CREATE INDEX xmax_index ON catalog_table(xmax);
CREATE INDEX ymin_index ON catalog_table(ymin);
CREATE INDEX ymax_index ON catalog_table(ymax);
CREATE INDEX utctime_index ON catalog_table(utc_datetime);
CREATE INDEX mediatype_index ON catalog_table(mediatype);

CREATE TABLE attribute_table (
    asset_id TEXT NOT NULL COLLATE NOCASE,
    catalog TEXT NOT NULL COLLATE NOCASE,
    key TEXT NOT NULL COLLATE NOCASE,
    value TEXT NOT NULL COLLATE NOCASE,
    PRIMARY KEY (asset_id, catalog, key)
);

CREATE INDEX asset_catalog_attribute_index ON
attribute_table(asset_id, catalog);

CREATE TABLE api_keys (
    api_key TEXT NOT NULL PRIMARY KEY,
    /* permissions is string of READ:catalog WRITE:catalog CREATE
       where READ/WRITE:catalog allow access to read and write the
       catalog and CREATE allows creation of a new catalog.
    */
    permissions TEXT NOT NULL
    );

CREATE TABLE global_variables (
    key TEXT NOT NULL PRIMARY KEY,
    value BLOB);
