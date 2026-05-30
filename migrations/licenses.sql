-- Licencias por cliente (vigencia del servicio).

CREATE TABLE IF NOT EXISTS licenses (
    id INT NOT NULL AUTO_INCREMENT,
    license_client_name VARCHAR(255) NOT NULL DEFAULT '',
    since_date DATE NULL,
    end_date DATE NULL,
    added_date DATETIME NULL,
    updated_date DATETIME NULL,
    deleted_date DATETIME NULL,
    PRIMARY KEY (id),
    KEY idx_licenses_deleted_date (deleted_date),
    KEY idx_licenses_client_name (license_client_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
