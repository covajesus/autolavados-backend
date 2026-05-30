-- Vincula rifas con la licencia (cliente SaaS).

ALTER TABLE raffles
    ADD COLUMN license_id INT NULL AFTER raffle,
    ADD KEY idx_raffles_license_id (license_id);
