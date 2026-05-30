-- Vincula tickets con la licencia (cliente SaaS).

ALTER TABLE tickets
    ADD COLUMN license_id INT NULL AFTER customer_id,
    ADD KEY idx_tickets_license_id (license_id);
