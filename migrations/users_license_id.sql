-- Vincula usuarios con la licencia (cliente SaaS).

ALTER TABLE users
    ADD COLUMN license_id INT NULL AFTER rol_id,
    ADD KEY idx_users_license_id (license_id);
