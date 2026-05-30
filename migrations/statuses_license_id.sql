-- Vincula estatus con la licencia (cliente SaaS).

ALTER TABLE statuses
    ADD COLUMN license_id INT NULL AFTER status,
    ADD KEY idx_statuses_license_id (license_id);
