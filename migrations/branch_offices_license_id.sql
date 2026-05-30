-- Vincula sucursales con la licencia (cliente SaaS).

ALTER TABLE branch_offices
    ADD COLUMN license_id INT NULL AFTER branch_office,
    ADD KEY idx_branch_offices_license_id (license_id);
